# GameResearch AI

**Autonomous AAA mobile-game deep research and original game design agent.**

Researches successful endless-runner / action-adventure mobile games
(Temple Run, Temple Run 2, Subway Surfers, Sonic Dash, Minion Rush,
Jetpack Joyride, Alto's Odyssey, Talking Tom Gold Run, Lara Croft: Relic
Run, Rayman Adventures, Into the Dead 2 + one discovered during research),
compares them, finds the design gap, creates 5 original concepts and
designs the complete original Game Bible — **never a clone, never a reskin.**

Pipeline (from the master build prompt):

```
PHASE 1  Game discovery fact sheets (10–12 games)
PHASE 3  Temple Run deep analysis (movement / camera / level / loop / psychology)
PHASE 4  Comparative analysis (patterns, differentiators, friction, gaps)
PHASE 5  Design gap + exactly 5 original concepts (trade-offs, not scores)
PHASE 6  Complete original Game Bible (design, UI/UX, world, Godot architecture)
```

## Honesty rules enforced in code

- Every factual statement in agent output must be tagged **[VERIFIED]**,
  **[INFERENCE]** or **[UNVERIFIED]**. An untagged factual line is
  force-marked `[UNVERIFIED]` by the honesty gate before the report is
  assembled — an inference can never silently pass as a fact.
- Phase 2 (actually playing the games) is not automated: gameplay-derived
  observations stay `[UNVERIFIED]` and the pipeline relies on documented
  sources instead, exactly as the master prompt allows.
- No copyrighted assets, characters, maps, names, storylines or code from
  reference games. Principles, not expression.
- Model access has one abstraction with a cloud-first loading gate: a
  healthy authorized cloud API is used (local model MUST NOT be loaded);
  with no usable API the local model (Qwen3-0.6B GGUF via llama.cpp binding
  point) loads lazily; when the cloud recovers, local unloads when safe.
  Never a silent paid switch.
- The NVIDIA API key is read from the `NVIDIA_API_KEY` environment
  variable only. It is never stored, never logged, never committed, and
  never appears in exception messages.

## Quick start

```bash
git clone https://github.com/pocketagent98-ai/GameResearch-AI.git
cd GameResearch-AI
pip install -e ".[dev]"

# offline test suite (no network, no keys) — 30 tests
python -m pytest

# offline pipeline demo (deterministic scripted model)
python examples/offline_demo.py

# LIVE research run with NVIDIA NIM (your key, your account)
export NVIDIA_API_KEY="nvapi-..."     # from build.nvidia.com
python examples/live_nim_research.py --quick          # 3 games
python examples/live_nim_research.py                  # all 12 games
```

The live runner first verifies the connection (`GET /v1/models`), picks a
small instruct model automatically, optionally performs real DuckDuckGo
source lookups per game (best-effort, keyless), then runs the pipeline and
prints a markdown research report with per-game tag-compliance stats.

There is also a manual **Live NVIDIA NIM check** GitHub Actions workflow
(`.github/workflows/live-check.yml`): it runs the offline suite first and
then a real pipeline run using the `NVIDIA_API_KEY` repository secret
(add it under Settings → Secrets and variables → Actions). Public repos
run Actions free of charge.

## Status

**v0.1.0 — core pipeline, not production-ready.** Implemented and tested:
pipeline phases, honesty gate, NIM client (OpenAI-compatible, retryable,
key-masking), DuckDuckGo search with SSRF guard, cloud/local loading gate
with a stub runtime. Roadmap: real llama.cpp binding for the local model,
Blender/Godot asset pipeline, playtest-analysis tooling, UI.

## License

GameResearch AI is proprietary software, published source-available under
the [GameResearch AI Proprietary License](LICENSE). Third-party components
remain under their own licenses — see
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). Not affiliated with any
game studio, publisher, NVIDIA, DuckDuckGo or model provider.
