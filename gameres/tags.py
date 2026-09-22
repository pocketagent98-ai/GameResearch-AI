"""Evidence-tag verification.

The master prompt's most important honesty rule: never present an
inference as a fact. Every factual statement in generated research must
carry one of:

    [VERIFIED]    — supported by a collected source
    [INFERENCE]   — reasoned from evidence, not directly observed
    [UNVERIFIED]  — could not be confirmed

``tag_stats`` reports how well an agent output complies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TAG_VERIFIED = "[VERIFIED]"
TAG_INFERENCE = "[INFERENCE]"
TAG_UNVERIFIED = "[UNVERIFIED]"

_ALL_TAGS = (TAG_VERIFIED, TAG_INFERENCE, TAG_UNVERIFIED)

# a statement looks factual when it carries a number or a year
_FACTUAL_RE = re.compile(r"\d")


@dataclass
class TagStats:
    verified: int = 0
    inference: int = 0
    unverified: int = 0
    untagged_factual_lines: int = 0
    total_lines: int = 0

    @property
    def compliant(self) -> bool:
        return self.untagged_factual_lines == 0 and (
            self.verified + self.inference + self.unverified
        ) > 0


def tag_stats(text: str) -> TagStats:
    stats = TagStats()
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("|"):
            continue  # headings/tables carry structure, not facts
        stats.total_lines += 1
        if TAG_VERIFIED in line:
            stats.verified += 1
        elif TAG_INFERENCE in line:
            stats.inference += 1
        elif TAG_UNVERIFIED in line:
            stats.unverified += 1
        elif _FACTUAL_RE.search(line) and len(line) > 25:
            # a substantive line with a number but no tag at all
            stats.untagged_factual_lines += 1
    return stats


def annotate_unverified(text: str) -> str:
    """Post-process: mark untagged factual lines as [UNVERIFIED] rather than
    letting them pass as silent facts."""
    out = []
    for raw_line in (text or "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith("#")
            and not stripped.startswith("|")
            and not any(t in stripped for t in _ALL_TAGS)
            and _FACTUAL_RE.search(stripped)
            and len(stripped) > 25
        ):
            line = line + " [UNVERIFIED]"
        out.append(line)
    return "\n".join(out)
