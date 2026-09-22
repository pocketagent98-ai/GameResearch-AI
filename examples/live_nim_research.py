"""Live NVIDIA NIM research run.

Reads the API key from the NVIDIA_API_KEY environment variable ONLY —
the key is never stored, never logged and never written to any file.

Usage:
    export NVIDIA_API_KEY="nvapi-..."
    python examples/live_nim_research.py [--model MODEL] [--quick]

Options:
    --model   pick a specific NIM model id (default: auto-select from
              /v1/models, preferring a small instruct model, verified
              with a tiny probe call)
    --quick   3 reference games instead of 12 (fewer tokens)

The run prints a markdown research report to stdout.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gameres.models import NIMClient
from gameres.pipeline import GameResearchPipeline
from gameres.search import DuckDuckGoSearch

PREFERRED = [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-70b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
    "google/gemma-2-9b-it",
    "microsoft/phi-3-small-8k-instruct",
]


def pick_model(available: list, tried: set) -> str:
    """Pick the first PREFERRED model present and not yet tried; then any
    remaining instruct model; then anything."""
    for pref in PREFERRED:
        if pref in available and pref not in tried:
            return pref
    for m in available:
        if "instruct" in m.lower() and m not in tried:
            return m
    for m in available:
        if m not in tried:
            return m
    raise SystemExit("no callable model found on this key")


def verified_model(client: NIMClient, available: list) -> str:
    """A model can be LISTED on a key but not callable (404 on invoke).
    Probe each candidate with a tiny chat call and use the first that
    actually responds."""
    tried: set = set()
    last_error = None
    for _ in range(len(available)):
        model = pick_model(available, tried)
        tried.add(model)
        probe = NIMClient(api_key=client._key, model=model, max_retries=0)
        try:
            reply = probe.chat("Reply with the single word: OK", max_tokens=8)
            if reply.strip():
                print(f"Model probe OK: {model}", file=sys.stderr)
                return model
        except Exception as exc:
            last_error = exc
            print(f"Model not callable, trying next: {model}", file=sys.stderr)
    raise SystemExit(f"no callable model found; last error: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--no-search", action="store_true",
                        help="skip the live DuckDuckGo source check")
    args = parser.parse_args()

    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        print("ERROR: set the NVIDIA_API_KEY environment variable first.", file=sys.stderr)
        return 2

    client = NIMClient(api_key=api_key)

    print("== NVIDIA NIM connection test: GET /v1/models ==", file=sys.stderr)
    try:
        models = client.list_models()
    except Exception as exc:
        print(f"CONNECTION FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"OK — {len(models)} models visible on this key.", file=sys.stderr)

    model = args.model or verified_model(client, models)
    print(f"Using model: {model}", file=sys.stderr)
    client = NIMClient(api_key=api_key, model=model)

    search = None if args.no_search else DuckDuckGoSearch()
    pipeline = GameResearchPipeline(model=client, search=search,
                                    verify_search=not args.no_search)

    report = pipeline.run(
        "Research successful endless-runner games and design an original "
        "game that is not a clone",
        quick=args.quick,
    )

    print(report.to_markdown())
    print(f"\n<!-- model calls: {report.model_calls}, "
          f"input tokens: {client.input_tokens}, "
          f"output tokens: {client.output_tokens}, "
          f"elapsed: {report.elapsed_seconds:.1f}s -->")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
