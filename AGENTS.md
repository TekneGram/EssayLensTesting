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

## Scaffold
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
