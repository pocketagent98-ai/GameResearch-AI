"""Model-layer tests: local gate, key safety, static determinism."""

import pytest

from gameres.models import LocalGate, LocalModelSpec, NIMClient, StaticModel, StubLocalRuntime


# -- LocalGate: cloud-first loading ----------------------------------------

def test_cloud_healthy_routes_cloud_and_never_loads_local():
    runtime = StubLocalRuntime()
    gate = LocalGate(cloud_health=lambda: True, runtime=runtime)
    for _ in range(3):
        assert gate.route() == "cloud"
    assert runtime.load_calls == 0  # local model MUST NOT be loaded


def test_cloud_down_lazy_loads_local_once():
    runtime = StubLocalRuntime()
    gate = LocalGate(cloud_health=lambda: False, runtime=runtime)
    assert gate.route() == "local"
    assert gate.route() == "local"
    assert runtime.load_calls == 1
    assert runtime.loaded_spec.name == "Qwen3-0.6B"


def test_cloud_recovery_unloads_local_when_safe():
    runtime = StubLocalRuntime()
    state = {"healthy": False}
    gate = LocalGate(cloud_health=lambda: state["healthy"], runtime=runtime)
    assert gate.route() == "local"
    assert runtime.is_loaded()
    state["healthy"] = True
    assert gate.route() == "cloud"
    assert not runtime.is_loaded()
    assert runtime.unload_calls == 1


def test_unload_deferred_while_busy():
    runtime = StubLocalRuntime()
    state = {"healthy": False}
    gate = LocalGate(cloud_health=lambda: state["healthy"], runtime=runtime)
    gate.route()
    runtime.busy = True
    state["healthy"] = True
    gate.route() == "cloud"
    assert runtime.is_loaded()  # deferred: mid-generation
    runtime.busy = False
    assert gate.route() == "cloud"
    assert not runtime.is_loaded()


def test_report_cloud_failure_switches_to_local():
    runtime = StubLocalRuntime()
    gate = LocalGate(cloud_health=lambda: True, runtime=runtime)
    assert gate.route() == "cloud"
    gate.report_cloud_failure()
    assert gate.route() == "local"


def test_generate_local_refuses_after_recovery():
    runtime = StubLocalRuntime()
    state = {"healthy": False}
    gate = LocalGate(cloud_health=lambda: state["healthy"], runtime=runtime)
    gate.route()
    state["healthy"] = True
    with pytest.raises(RuntimeError):
        gate.generate_local("hi")


def test_local_model_spec_default():
    spec = LocalModelSpec()
    assert spec.gguf_path.endswith(".gguf")
    assert spec.context_tokens >= 2048


# -- NIMClient safety (no network in these tests) ---------------------------

def test_nimclient_repr_never_leaks_key():
    client = NIMClient(api_key="nvapi-SUPERSECRETKEY123")
    assert "nvapi-SUPERSECRETKEY123" not in repr(client)
    assert "nvapi-SUPERSECRETKEY123" not in str(client)


def test_nimclient_error_messages_never_leak_key():
    import urllib.error
    import json
    from unittest.mock import patch, MagicMock

    client = NIMClient(api_key="nvapi-SUPERSECRETKEY123", max_retries=0)
    err = urllib.error.HTTPError(
        "url", 401, "Unauthorized", None,  # type: ignore[arg-type]
        MagicMock(read=lambda: b'{"error": "bad key"}'),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(Exception) as exc_info:
            client.chat("hello")
    assert "nvapi-SUPERSECRETKEY123" not in str(exc_info.value)
    assert "401" in str(exc_info.value)


def test_static_model_deterministic():
    model = StaticModel(script={"temple run": "sheet"}, default="d")
    assert model.chat("Tell me about Temple Run") == "sheet"
    assert model.chat("anything else") == "d"
    assert model.health() is True
