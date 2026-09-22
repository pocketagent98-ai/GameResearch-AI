"""Shared fixtures for offline tests — no network, no API keys."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from gameres.models import StaticModel
from gameres.pipeline import GameResearchPipeline
from gameres.search import CannedSearch, SearchHit


SHEET = (
    "- Developer: Imangi Studios [VERIFIED]\n"
    "- Released 2011 on iOS [VERIFIED]\n"
    "- Endless runner with swipe controls [VERIFIED]\n"
    "- The loop works because of immediate feedback and near misses [INFERENCE]\n"
    "- Monetization details may have changed since launch [UNVERIFIED]\n"
)

COMPARISON = (
    "Common patterns: swipe/tilt controls, coin economies, mission lists "
    "[VERIFIED].\n"
    "Underused ideas: player-shaped environments, meaningful exploration "
    "[INFERENCE].\n"
)

CONCEPTS = (
    "Concept 1 - Name: Currents of Nhyra. Pitch: a runner where the world "
    "is a living river that remembers the player. Core mechanic: the river "
    "re-routes itself based on how you played previous runs. Risks: "
    "procedural memory costs. Technical difficulty: medium. Why different: "
    "no current runner adapts the world to the player [INFERENCE].\n"
    "Concept 2 - Name: Skyward Bloom. Pitch: vertical runner where you "
    "plant the path you run on. Core mechanic: seeds collected mid-run "
    "grow the next segment.\n"
    "Concept 3 - Name: Echo Chase. Pitch: you race your own ghost from "
    "previous runs; the ghost is an obstacle and a guide.\n"
    "Concept 4 - Name: Gravity Garden. Pitch: rotate the world instead of "
    "the character.\n"
    "Concept 5 - Name: Lantern Keepers. Pitch: co-op endless runner where "
    "two players share one light source.\n"
    "Recommendation: Currents of Nhyra - strongest originality-to-"
    "feasibility trade-off; the adaptive-world mechanic is feasible in "
    "Godot and no researched game uses it [INFERENCE].\n"
)

BIBLE = (
    "GAME BIBLE: Currents of Nhyra\n"
    "Genre: adaptive endless runner. Platform: mobile, Godot 4.x.\n"
    "Core loop: RUN -> SHAPE -> COLLECT -> RISK -> REWARD -> FAIL -> "
    "GROW -> RETRY.\n"
    "World: a sentient river-network; biomes change with player history.\n"
    "Design decision: no timers, only flow speed, to keep runs fair and "
    "readable.\n"
)


def build_pipeline() -> GameResearchPipeline:
    model = StaticModel(
        script={
            "phase 1 - game discovery": SHEET,
            "phase 3 - temple run": SHEET,
            "phase 4 - comparative": COMPARISON,
            "phase 5 - find the design gap": CONCEPTS,
            "phase 6 - create the final original game": BIBLE,
        },
        default="ok",
    )
    search = CannedSearch({
        "temple run": [SearchHit("Temple Run wiki", "https://example.com/tr", "Imangi Studios")],
    })
    return GameResearchPipeline(model=model, search=search)


@pytest.fixture
def pipeline():
    return build_pipeline()
