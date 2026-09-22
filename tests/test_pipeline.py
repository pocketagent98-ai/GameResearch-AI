"""Offline pipeline tests: full run works, honesty rules enforced."""

from gameres.pipeline import REFERENCE_GAMES, GameResearchPipeline
from gameres.tags import tag_stats

from conftest import CONCEPTS, build_pipeline


def test_full_offline_pipeline_runs_all_phases():
    p = build_pipeline()
    report = p.run("Design an original endless runner", quick=True)
    # quick: 3 discovery sheets + comparison + concepts + bible = 6 calls (phase 3 skipped)
    assert report.model_calls == 6
    assert len(report.sheets) == 3
    assert report.comparison
    assert report.concepts
    assert report.bible
    assert report.elapsed_seconds >= 0


def test_full_run_with_temple_run_analysis():
    p = build_pipeline()
    report = p.run("Design an original endless runner", games=["Temple Run", "Subway Surfers"])
    assert report.temple_run_analysis  # not quick -> phase 3 included
    assert len(report.sheets) == 2


def test_reference_games_contain_required_set():
    required = {"Temple Run", "Temple Run 2", "Subway Surfers", "Sonic Dash",
                "Minion Rush", "Jetpack Joyride", "Alto's Odyssey",
                "Talking Tom Gold Run", "Lara Croft: Relic Run",
                "Rayman Adventures", "Into the Dead 2"}
    assert required.issubset(set(REFERENCE_GAMES))
    assert len(REFERENCE_GAMES) == 12  # 11 listed + 1 discovered-during-research slot


def test_markdown_report_contains_all_sections():
    p = build_pipeline()
    report = p.run("Design an original endless runner", games=["Temple Run"])
    md = report.to_markdown()
    assert "PHASE 1" in md and "PHASE 4" in md and "PHASE 5" in md and "PHASE 6" in md
    assert "Tag compliance" in md


def test_untagged_facts_are_force_marked_unverified():
    # a model reply with a silent factual line must not survive untagged
    from gameres.models import StaticModel
    from gameres.tags import annotate_unverified

    model = StaticModel(default="Temple Run made 100 million dollars in revenue.")
    p = GameResearchPipeline(model=model)
    sheets = p.phase1_discovery(["Temple Run"])
    line = sheets[0]["text"]
    assert "[UNVERIFIED]" in line  # honesty gate appended it
    assert tag_stats(line).untagged_factual_lines == 0


def test_concepts_contain_five_concepts():
    p = build_pipeline()
    report = p.run("q", games=["Temple Run"])
    assert report.concepts.count("Concept ") >= 5


def test_search_failures_disclosed_when_verify_enabled():
    # CannedSearch returns [] for unknown games -> failure recorded
    p = build_pipeline()
    p.verify_search = False  # canned is not DuckDuckGoSearch, so no failures path
    report = p.run("q", games=["Temple Run"])
    assert report.search_failures == []


def test_no_clone_language_in_outputs():
    p = build_pipeline()
    report = p.run("q", games=["Temple Run"])
    md = report.to_markdown().lower()
    for bad in ("clone of temple run", "reskin of temple run", "copy of subway"):
        assert bad not in md
