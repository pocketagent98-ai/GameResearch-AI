# Changelog

## [0.1.0] — 2026-09-22

Initial release of the game-research agent.

### Added
- Pipeline phases 1/3/4/5/6 from the master build prompt (discovery fact
  sheets, Temple Run deep analysis, comparative analysis, 5 original
  concepts, complete Game Bible) with a markdown report writer.
- Honesty gate: [VERIFIED]/[INFERENCE]/[UNVERIFIED] tagging, tag stats,
  and force-marking of untagged factual lines.
- NIMClient: NVIDIA NIM (OpenAI-compatible) cloud model client with
  retries on 429/5xx, token accounting, and structural key masking.
- DuckDuckGoSearch: keyless best-effort search with an SSRF guard and
  graceful degradation; CannedSearch for offline runs.
- LocalGate: cloud-first loading gate for local Qwen3-0.6B via a llama.cpp
  binding point (StubLocalRuntime in tests; native binding on roadmap).
- 30 offline tests; offline + live examples; CI and live-check workflows.

### Not yet implemented (roadmap)
- Real llama.cpp native binding; Blender/Godot asset pipeline; automated
  playtest analysis; web UI.
