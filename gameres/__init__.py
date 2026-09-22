"""GameResearch AI — autonomous AAA mobile-game deep research and original
game design agent.

Pipeline (from the master build prompt):

    PHASE 1  Game discovery (10-12 reference games, fact sheets)
    PHASE 2  Gameplay observation (human-in-the-loop; automated runs mark
             findings [UNVERIFIED] instead of pretending to have played)
    PHASE 3  Temple Run deep analysis (movement / camera / level / loop /
             psychology)
    PHASE 4  Comparative analysis (common patterns, differentiators,
             friction, underused ideas)
    PHASE 5  Design gap + 5 original concepts (no arbitrary scores —
             trade-offs explained)
    PHASE 6  Final original Game Bible (original IP, never a clone)

Hard rules encoded here:
- No copyrighted assets, characters, maps, names, storylines or code from
  reference games. Extract principles, not expression.
- Every factual statement in outputs is tagged [VERIFIED], [INFERENCE] or
  [UNVERIFIED]. Inference is never presented as fact.
- Model access goes through one abstraction: cloud (NVIDIA NIM) first,
  local model (llama.cpp/Qwen3 GGUF binding point) only when the cloud
  API is unusable — never a silent paid switch.

Proprietary code (see LICENSE). Third-party components keep their own
licenses (see THIRD-PARTY-NOTICES.md).
"""

__version__ = "0.1.0"

from .models import ModelClient, NIMClient, StaticModel, LocalGate, StubLocalRuntime
from .search import CannedSearch, DuckDuckGoSearch, SearchHit
from .tags import TAG_VERIFIED, TAG_INFERENCE, TAG_UNVERIFIED, tag_stats
from .pipeline import (
    GameResearchPipeline,
    REFERENCE_GAMES,
    ResearchReport,
)

__all__ = [
    "ModelClient",
    "NIMClient",
    "StaticModel",
    "LocalGate",
    "StubLocalRuntime",
    "CannedSearch",
    "DuckDuckGoSearch",
    "SearchHit",
    "TAG_VERIFIED",
    "TAG_INFERENCE",
    "TAG_UNVERIFIED",
    "tag_stats",
    "GameResearchPipeline",
    "REFERENCE_GAMES",
    "ResearchReport",
    "__version__",
]
