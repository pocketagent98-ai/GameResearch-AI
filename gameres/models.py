"""Model access: one abstraction for cloud and local.

Cloud path:
    pipeline -> NIMClient (NVIDIA NIM, OpenAI-compatible) -> provider

Local path (offline / low connectivity):
    pipeline -> LocalGate -> llama.cpp binding -> Qwen3 GGUF

Loading gate (mandatory):
    cloud API healthy  -> use cloud; local model MUST NOT be loaded
    no usable API      -> lazily load the local model
    cloud recovers     -> resume cloud, unload local when safe

The API key is passed per call, never stored on the client, never logged,
and never included in exception messages or repr().
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
RETRYABLE = {408, 409, 429, 500, 502, 503, 504}


class ModelError(RuntimeError):
    def __init__(self, message: str, *, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status


class ModelClient(Protocol):
    name: str

    def chat(self, prompt: str, *, system: str = "", max_tokens: int = 2048) -> str: ...

    def health(self) -> bool: ...


class NIMClient:
    """NVIDIA NIM (OpenAI-compatible /chat/completions). Key comes from the
    caller each time; it never appears in logs or errors."""

    def __init__(self, api_key: str, *, model: str = "meta/llama-3.1-8b-instruct",
                 base_url: str = NIM_BASE_URL, timeout: float = 120.0,
                 max_retries: int = 3) -> None:
        self.name = "nvidia-nim"
        self._key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def _post(self, payload: Dict) -> Dict:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                # never include the key or auth header in the message
                body = ""
                try:
                    body = exc.read().decode("utf-8", "replace")[:200]
                except Exception:
                    pass
                last_error = ModelError(
                    f"NIM HTTP {exc.code} for model {self.model}: {body}", status=exc.code
                )
                if exc.code not in RETRYABLE:
                    raise last_error
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = ModelError(f"NIM network error: {exc}", status=None)
            time.sleep(min(2 ** attempt, 8))
        raise last_error or ModelError("NIM request failed")

    def list_models(self) -> List[str]:
        req = urllib.request.Request(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {self._key}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            blob = json.loads(resp.read().decode("utf-8"))
        return sorted(m["id"] for m in blob.get("data", []) if m.get("id"))

    def chat(self, prompt: str, *, system: str = "", max_tokens: int = 2048) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        blob = self._post({
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "stream": False,
        })
        self.calls += 1
        usage = blob.get("usage") or {}
        self.input_tokens += int(usage.get("prompt_tokens", 0))
        self.output_tokens += int(usage.get("completion_tokens", 0))
        choice = (blob.get("choices") or [{}])[0]
        return ((choice.get("message") or {}).get("content")) or ""

    def health(self) -> bool:
        try:
            return len(self.list_models()) > 0
        except Exception:
            return False

    def __repr__(self) -> str:  # key must never leak
        return f"NIMClient(model={self.model!r}, key=***masked***)"


class StaticModel:
    """Deterministic scripted model for offline runs and tests.

    ``script`` maps a lowercase substring of the prompt to a canned reply;
    ``default`` answers everything else.
    """

    def __init__(self, script: Optional[Dict[str, str]] = None, default: str = "ok") -> None:
        self.name = "static"
        self.script = {k.lower(): v for k, v in (script or {}).items()}
        self.default = default
        self.calls = 0

    def chat(self, prompt: str, *, system: str = "", max_tokens: int = 2048) -> str:
        self.calls += 1
        low = prompt.lower()
        for needle, reply in self.script.items():
            if needle in low:
                return reply
        return self.default

    def health(self) -> bool:
        return True


# --------------------------------------------------------------------------
# Local model gate (llama.cpp binding point)
# --------------------------------------------------------------------------

@dataclass
class LocalModelSpec:
    name: str = "Qwen3-0.6B"
    gguf_path: str = "models/qwen3-0.6b-q4_0.gguf"
    context_tokens: int = 2048


class StubLocalRuntime:
    """In-memory stand-in for the llama.cpp native runtime. A native app
    binds the same three methods to llama.cpp's API."""

    def __init__(self) -> None:
        self.loaded_spec: Optional[LocalModelSpec] = None
        self.load_calls = 0
        self.unload_calls = 0
        self.busy = False

    def load(self, spec: LocalModelSpec) -> None:
        self.load_calls += 1
        self.loaded_spec = spec

    def unload(self) -> None:
        self.unload_calls += 1
        self.loaded_spec = None

    def is_loaded(self) -> bool:
        return self.loaded_spec is not None

    def generate(self, prompt: str, *, max_tokens: int = 512) -> str:
        if not self.is_loaded():
            raise RuntimeError("local model not loaded")
        return "[local model reply]"


class LocalGate:
    """Cloud-first loading gate. ``cloud_health`` is a callable returning
    True when the authorized cloud API is usable. The local runtime loads
    lazily ONLY when the cloud is down, and unloads when the cloud recovers
    and generation is not in flight."""

    def __init__(self, cloud_health: Callable[[], bool], runtime: StubLocalRuntime,
                 spec: Optional[LocalModelSpec] = None) -> None:
        self._cloud_health = cloud_health
        self.runtime = runtime
        self.spec = spec or LocalModelSpec()
        self._cloud_down = False
        self.events: List[str] = []

    def _log(self, event: str) -> None:
        self.events.append(event)

    def report_cloud_failure(self) -> None:
        self._cloud_down = True
        self._log("cloud.failed")

    def route(self) -> str:
        healthy = not self._cloud_down and bool(self._cloud_health())
        if healthy:
            if self.runtime.is_loaded() and not self.runtime.busy:
                self.runtime.unload()
                self._log("local.unloaded")
            self._log("route.cloud")
            return "cloud"
        if not self.runtime.is_loaded():
            self.runtime.load(self.spec)  # lazy load, exactly once
            self._log("local.loaded")
        self._log("route.local")
        return "local"

    def generate_local(self, prompt: str, *, max_tokens: int = 512) -> str:
        if not self.runtime.is_loaded():
            raise RuntimeError("local model not loaded; call route() first")
        if not self._cloud_down and self._cloud_health():
            raise RuntimeError("cloud recovered; route() again")
        return self.runtime.generate(prompt, max_tokens=max_tokens)
