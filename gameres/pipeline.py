"""The game-research pipeline (master prompt phases 1-6 + honesty rules).

Each phase builds a prompt that encodes the corresponding section of the
master prompt and calls the model client. Facts the model states must be
tagged [VERIFIED] / [INFERENCE] / [UNVERIFIED]; ``annotate_unverified``
post-processes outputs so a silent fact can never reach the final report.

Phase 2 (actually playing the games) cannot be automated honestly — this
pipeline marks gameplay-derived observations as [UNVERIFIED] and relies on
documented sources instead, exactly as the master prompt allows when direct
gameplay is not possible.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .models import ModelClient
from .search import CannedSearch, DuckDuckGoSearch, SearchHit, SearchProvider
from .tags import annotate_unverified, tag_stats

REFERENCE_GAMES: List[str] = [
    "Temple Run",
    "Temple Run 2",
    "Subway Surfers",
    "Sonic Dash",
    "Minion Rush",
    "Jetpack Joyride",
    "Alto's Odyssey",
    "Talking Tom Gold Run",
    "Lara Croft: Relic Run",
    "Rayman Adventures",
    "Into the Dead 2",
    # slot 12: one additional highly relevant game discovered during research
    "Crossy Road",
]

SYSTEM_PROMPT = (
    "You are an autonomous AAA-level Game Research Director, Game Designer, "
    "UX/UI Designer, Gameplay Analyst, Level Designer, Systems Designer, "
    "Technical Game Architect and Product Strategist. You never copy "
    "copyrighted assets, characters, maps, names, storylines or code from "
    "reference games. You extract general design principles and design "
    "ORIGINAL intellectual property. You never present an inference as a "
    "fact: every factual statement you output must be tagged [VERIFIED], "
    "[INFERENCE] or [UNVERIFIED]. You never create a reskin or a clone."
)

_FACT_SHEET_FIELDS = (
    "Official name; Developer; Publisher; Release history; Platforms; Genre; "
    "Core gameplay loop; Target audience; Camera perspective; Movement system; "
    "Controls; Player abilities; Obstacles; Enemies; Collectibles; Power-ups; "
    "Missions/objectives; Progression; Upgrades; Currency systems; Characters; "
    "World/level structure; Difficulty progression; Bosses; Events; Challenges; "
    "Rewards; Social features; Monetization structure; Audio design; Visual "
    "style; Animation style; UI/UX structure; Loading experience; Tutorial and "
    "onboarding; Game-over and retry flow; Performance characteristics; "
    "Device requirements; Offline/online requirements"
)

_DISCOVERY_TEMPLATE = (
    "PHASE 1 - GAME DISCOVERY. Produce a compact fact sheet for the game "
    '"{game}" (endless runner / action-adventure mobile category). Cover: '
    + _FACT_SHEET_FIELDS
    + ".\nTag every factual statement. Prefer verified public information; "
    "when you are reasoning rather than reporting, tag [INFERENCE]; when you "
    "cannot confirm something, tag [UNVERIFIED]. Keep it under 500 words."
)

_TEMPLE_RUN_TEMPLATE = (
    "PHASE 3 - TEMPLE RUN DEEP ANALYSIS. Analyze Temple Run / Temple Run 2 "
    "in detail: MOVEMENT (running, turning, jumping, sliding, side movement, "
    "lane changes, momentum, timing windows, input responsiveness); CAMERA "
    "(distance, height, FOV, movement, shake, transitions, visual feedback); "
    "LEVEL DESIGN (path generation, turns, gaps, obstacles, environmental "
    "hazards, difficulty scaling, pattern generation, procedural elements, "
    "safe zones, risk/reward sections); GAMEPLAY LOOP (explain why the "
    "RUN -> AVOID -> COLLECT -> RISK -> REWARD -> FAIL -> UPGRADE -> RETRY "
    "loop works psychologically: immediate feedback, risk/reward, near "
    "misses, increasing speed, achievement, progress, curiosity, mastery, "
    "replayability). Fair and transparent design only - no deceptive or "
    "harmful mechanics. Tag facts. Under 600 words."
)

_COMPARISON_TEMPLATE = (
    "PHASE 4 - COMPARATIVE ANALYSIS. You have fact sheets for these games:\n"
    "{sheets}\n"
    "Compare them across: core loop, controls, movement, camera, level "
    "design, procedural generation, progression, difficulty, UI, UX, art "
    "direction, audio, rewards, economy, replayability, accessibility, "
    "performance, innovation. Then identify: (A) common patterns among "
    "successful games, (B) repeated features, (C) per-game "
    "differentiators, (D) friction-causing features, (E) features that "
    "could be improved, (F) underused ideas, (G) opportunities for an "
    "original game. Do NOT pick a 'best' game - explain what can be "
    "learned from each. Tag facts. Under 700 words."
)

_GAP_TEMPLATE = (
    "PHASE 5 - FIND THE DESIGN GAP. Based on this comparative analysis:\n"
    "{comparison}\n"
    "Find a genuine design opportunity - NOT 'Temple Run with different "
    "graphics'. Consider: what is missing from current endless runners; "
    "underused mechanics; what would make players curious; deeper mastery; "
    "a world that feels alive; meaningful exploration; meaningful player "
    "decisions; environments that react to the player; more interesting "
    "procedural generation; accessibility for new players; long-term "
    "discovery for advanced players.\n"
    "Create exactly 5 ORIGINAL game concepts. For each: Name; One-line "
    "pitch; Core mechanic; Unique selling point; World; Player role; "
    "Gameplay loop; Progression; Major risks; Technical difficulty; Why it "
    "is different. Then recommend the concept with the strongest "
    "combination of originality, gameplay depth, technical feasibility and "
    "long-term potential. Do NOT use arbitrary numerical scores - explain "
    "the trade-offs instead. Tag facts. Under 900 words."
)

_BIBLE_TEMPLATE = (
    "PHASE 6 - CREATE THE FINAL ORIGINAL GAME. Design the complete Game "
    "Bible for this selected concept:\n{concept}\n"
    "Sections: original game name; genre; high-concept pitch; player "
    "fantasy; target platform and device range; camera; art direction; "
    "world; story premise; characters; player character; core gameplay "
    "loop; secondary loops; movement system; exploration system; obstacle "
    "system; enemy/NPC systems; power-up, item and inventory systems; "
    "progression, skills and upgrades; missions, events, achievements and "
    "rewards; difficulty system; procedural generation and world "
    "structure; biomes, weather, day/night, environmental events, secret "
    "areas; boss/elite encounters; UI/UX (HUD, menus, settings, tutorial, "
    "onboarding, game-over, restart); audio; VFX and animation; haptics; "
    "accessibility; performance; save system; offline/online architecture; "
    "game economy; optional monetization; live events; future content; "
    "Godot 4.x technical architecture (scene structure, node hierarchy, "
    "managers, object pooling); development roadmap; testing strategy; "
    "risk analysis.\n"
    "This must be a genuinely original IP - not a reskin. Tag facts and "
    "mark design decisions as decisions. Under 1800 words."
)


@dataclass
class ResearchReport:
    question: str
    sheets: List[dict] = field(default_factory=list)      # {"game", "text", "stats"}
    search_failures: List[str] = field(default_factory=list)
    temple_run_analysis: str = ""
    comparison: str = ""
    concepts: str = ""
    bible: str = ""
    elapsed_seconds: float = 0.0
    model_calls: int = 0

    def to_markdown(self) -> str:
        parts = [
            "# GameResearch AI — research report",
            "",
            f"_Question: {self.question}_",
            "",
            "## PHASE 1 — Game discovery fact sheets",
            "",
        ]
        for sheet in self.sheets:
            parts.append(f"### {sheet['game']}")
            parts.append("")
            parts.append(sheet["text"])
            parts.append("")
        if self.search_failures:
            parts.append("**Search/tool failures disclosed:** " + "; ".join(self.search_failures))
            parts.append("")
        if self.temple_run_analysis:
            parts += ["## PHASE 3 — Temple Run deep analysis", "", self.temple_run_analysis, ""]
        if self.comparison:
            parts += ["## PHASE 4 — Comparative analysis", "", self.comparison, ""]
        if self.concepts:
            parts += ["## PHASE 5 — Design gap and original concepts", "", self.concepts, ""]
        if self.bible:
            parts += ["## PHASE 6 — Original Game Bible", "", self.bible, ""]
        parts += [
            "---",
            "Tag compliance: "
            + ", ".join(
                f"{s['game']}: v={s['stats'].verified}, i={s['stats'].inference}, "
                f"u={s['stats'].unverified}, untagged={s['stats'].untagged_factual_lines}"
                for s in self.sheets
            ),
            "",
            "Every untagged factual line above was force-marked [UNVERIFIED] "
            "by the honesty gate before this report was assembled.",
        ]
        return "\n".join(parts)


class GameResearchPipeline:
    def __init__(
        self,
        *,
        model: ModelClient,
        search: Optional[SearchProvider] = None,
        verify_search: bool = False,
    ) -> None:
        self.model = model
        self.search = search or CannedSearch()
        # when True, run a live web check per game and record the top source
        self.verify_search = verify_search

    def _chat(self, prompt: str, max_tokens: int = 2048) -> str:
        text = self.model.chat(prompt, system=SYSTEM_PROMPT, max_tokens=max_tokens)
        return annotate_unverified(text)

    # -- phases ------------------------------------------------------------

    def phase1_discovery(self, games: Sequence[str]) -> List[dict]:
        sheets: List[dict] = []
        failures: List[str] = []
        for game in games:
            search_note = ""
            if self.verify_search and isinstance(self.search, DuckDuckGoSearch):
                hits = self.search.search(f"{game} mobile game developer official")
                if hits:
                    top = hits[0]
                    search_note = f"\nLive source found: {top.title} — {top.url}\n"
                else:
                    failures.append(f"no live source for {game}")
            text = self._chat(_DISCOVERY_TEMPLATE.format(game=game) + search_note,
                              max_tokens=1024)
            sheets.append({"game": game, "text": text, "stats": tag_stats(text)})
        self._last_search_failures = failures
        return sheets

    def phase3_temple_run(self) -> str:
        return self._chat(_TEMPLE_RUN_TEMPLATE, max_tokens=1200)

    def phase4_comparison(self, sheets: List[dict]) -> str:
        joined = "\n\n".join(f"[{s['game']}]\n{s['text']}" for s in sheets)
        return self._chat(_COMPARISON_TEMPLATE.format(sheets=joined), max_tokens=1400)

    def phase5_concepts(self, comparison: str) -> str:
        return self._chat(_GAP_TEMPLATE.format(comparison=comparison), max_tokens=1600)

    def phase6_bible(self, concept_block: str) -> str:
        return self._chat(_BIBLE_TEMPLATE.format(concept=concept_block), max_tokens=3000)

    # -- full run ------------------------------------------------------------

    def run(self, question: str, *, games: Optional[Sequence[str]] = None,
            quick: bool = False) -> ResearchReport:
        started = time.monotonic()
        games = list(games) if games else (REFERENCE_GAMES[:3] if quick else REFERENCE_GAMES)
        report = ResearchReport(question=question)

        report.sheets = self.phase1_discovery(games)
        report.search_failures = getattr(self, "_last_search_failures", [])
        report.temple_run_analysis = self.phase3_temple_run() if not quick else ""
        report.comparison = self.phase4_comparison(report.sheets)
        report.concepts = self.phase5_concepts(report.comparison)
        # the bible prompt takes the full concept block (recommendation included)
        report.bible = self.phase6_bible(report.concepts)

        report.elapsed_seconds = time.monotonic() - started
        report.model_calls = getattr(self.model, "calls", 0)
        return report
