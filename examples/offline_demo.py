"""Offline demo — the full pipeline with a deterministic scripted model.

No network, no API keys. Shows the phases, the honesty gate and the
final markdown report shape.

Usage:
    python examples/offline_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from gameres.pipeline import GameResearchPipeline
from gameres.search import CannedSearch, SearchHit

from conftest import build_pipeline  # scripted model + canned search


def main() -> None:
    pipeline: GameResearchPipeline = build_pipeline()
    report = pipeline.run(
        "Design an original endless runner that is not a clone",
        games=["Temple Run", "Subway Surfers", "Alto's Odyssey"],
        quick=False,
    )
    print(report.to_markdown())
    print(f"\n[model calls: {report.model_calls}, elapsed: {report.elapsed_seconds:.2f}s]")


if __name__ == "__main__":
    main()
