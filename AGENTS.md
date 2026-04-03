# Essay Lens Testing

## Goals
- Test various prompts under different conditions
- Gradually build a harness for agent capabilities.

## Prompts
- Feedback on essays: one shot and looped

## Conditions
- Different local LLMs
- Different context lengths
- Different kv-cache approaches

## Evaluations
- Compare with human expectations
- Superior model as judge (e.g., Gemini)

## Current Scaffold
- Primary CLI package: `src/essaylens_testing`
- Entry points: `bin/essaylens`, `bin/essaylens-server`
- Config system: split `TOML` files under `configs/models`, `configs/servers`, `configs/requests`, `configs/profiles`, `configs/presets`
- Backend: local `llama.cpp` server wrapper via `src/essaylens_testing/server`
- Clients: plain chat, streaming chat, and JSON-schema chat under `src/essaylens_testing/client`
- Runtime artifacts: `var/run`, `var/log`, and `runs`

## Design Intent
- Keep the harness CLI-first and file-oriented.
- Treat KV-cache as server/runtime config, not as conversation-history config.
- Keep model config, server config, and request config separate so experiments can swap one axis at a time.
- Prefer a thin adapter layer around inference backends. Right now only `llama.cpp` is implemented.

## Continuation Notes
- The current CLI expects a built `llama-server` binary under `third_party/llama-cpp-turboquant/build/...` unless overridden in server config.
- `essaylens chat` requires the server for the selected profile to already be running.
- `configs/profiles/*.toml` are the main user-facing switching points.
- The first pass truncates input by character count, not token count. If continuing, token-aware truncation is the next obvious upgrade.
- The batch runner currently prints outputs sequentially and does not yet aggregate metrics.
- No evaluation or judge pipeline exists yet; add that under `src/essaylens_testing/experiments` or a new `evaluation/` package.
- No tests have been added yet. Add CLI/config tests before broadening behavior.
