# Third-Party Notices

GameResearch AI is an independent proprietary product that interoperates
with third-party services and software. Third-party components remain
under their respective licenses.

| Component | Used for | Source | License | Shipped in this repo? |
|---|---|---|---|---|
| NVIDIA NIM API | cloud model calls (user's own key) | https://build.nvidia.com | NVIDIA API terms of use | No — service, key required |
| DuckDuckGo HTML endpoints | keyless best-effort web search | https://duckduckgo.com | DDG terms | No — service |
| pytest | dev/test tooling | https://github.com/pytest-dev/pytest | MIT | Dev dependency only |
| Qwen3-0.6B (model) | local-mode model (llama.cpp binding point) | https://huggingface.co/Qwen | Apache-2.0 | No — user-supplied GGUF, never committed |
| llama.cpp | local runtime | https://github.com/ggml-org/llama.cpp | MIT | No — native runtime bound by the app |
| Nexivra AI (companion repo) | design lineage (loading gate pattern) | https://github.com/pocketagent98-ai/Nexivra-AI | Proprietary | No — referenced |

## Notes

- The NVIDIA API key is provided by the user per run via the
  NVIDIA_API_KEY environment variable; it is never stored, logged or
  committed, and never appears in exception messages.
- No game assets, characters, names, storylines or code from any
  referenced game are included in this repository. Research outputs tag
  statements [VERIFIED] / [INFERENCE] / [UNVERIFIED] and design only
  original IP.
- Qwen3-0.6B and llama.cpp are third-party technologies; they are never
  described as proprietary GameResearch AI components.

## GameResearch AI's own code

Copyright © 2026 pocketagent98-ai. All rights reserved.
Covered by the GameResearch AI Proprietary License (see LICENSE).
