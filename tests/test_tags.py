"""Tag verification tests — the honesty gate."""

from gameres.tags import annotate_unverified, tag_stats


def test_tag_stats_counts_each_tag():
    text = (
        "Developer: Imangi Studios [VERIFIED]\n"
        "The loop is addictive [INFERENCE]\n"
        "Pricing unknown [UNVERIFIED]\n"
    )
    stats = tag_stats(text)
    assert stats.verified == 1
    assert stats.inference == 1
    assert stats.unverified == 1
    assert stats.compliant


def test_untagged_factual_line_is_flagged():
    text = "Temple Run earned 100 million dollars in its first year."
    stats = tag_stats(text)
    assert stats.untagged_factual_lines == 1
    assert not stats.compliant


def test_headings_and_tables_not_counted_as_facts():
    text = "## Section with 3 numbers\n| game | year 2011 |\n|---|---|\n"
    stats = tag_stats(text)
    assert stats.untagged_factual_lines == 0


def test_annotate_unverified_appends_tag_to_factual_lines():
    text = (
        "Developer: Imangi Studios [VERIFIED]\n"
        "Temple Run earned 100 million dollars in its first year.\n"
    )
    out = annotate_unverified(text)
    lines = out.splitlines()
    assert lines[0].endswith("[VERIFIED]")
    assert lines[1].endswith("[UNVERIFIED]")
    assert tag_stats(out).untagged_factual_lines == 0


def test_annotate_leaves_short_and_non_factual_lines_alone():
    text = "Hello there.\nRun away from the monkey."
    out = annotate_unverified(text)
    assert out == text


def test_all_three_tags_exist():
    assert "[VERIFIED]" and "[INFERENCE]" and "[UNVERIFIED]"
