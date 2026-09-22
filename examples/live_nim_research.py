"""Live NVIDIA NIM research run.

Reads the API key from the NVIDIA_API_KEY environment variable ONLY —
the key is never stored, never logged and never written to any file.

Usage:
    export NVIDIA_API_KEY="nvapi-..."
    python examples/live_nim_research.py [--model MODEL] [--quick]

Options:
    --model   pick a specific NIM model id (default: auto-select from
              /v1/models, preferring a small instruct model)
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
    "meta/llama-3.1-70b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
    "meta/llama-3.3-70b-instruct",
]


def pick_model(available: list) -> str:
    for pref in PREFERRED:
        if pref in available:
            return pref
    instruct = [m for m in available if "instruct" in m.lower()]
    if instruct:
        return instruct[0]
    return available[0] if available else "meta/llama-3.1-8b-instruct"


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

    model = args.model or pick_model(models)
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
