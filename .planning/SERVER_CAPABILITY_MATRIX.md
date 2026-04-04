# Server Capability Matrix

This document defines step 1 of the development plan: the concrete server capability matrix for the local `llama-server` backend used by Essay Lens Testing.

The backend in this repository is the vendored TurboQuant-enabled `llama.cpp` fork under `third_party/llama-cpp-turboquant`, currently on branch `feature/turboquant-kv-cache`.

## Purpose

Essay Lens Testing is a server-first local harness. Before building broader experiment features, the project must be able to:

- start the local server
- confirm readiness
- perform every server call the harness chooses to support
- stop the server cleanly

This file is the source of truth for that supported-call surface.

## Scope Categories

- `Required in initial server-first build`: must be implemented and verified before moving on to non-server features
- `Available in backend, deferred for app scope`: exposed by `llama-server`, but not part of the initial Essay Lens harness contract
- `Operational, not an inference request`: server management or inspection behavior rather than text-generation work

## Capability Matrix

| Capability | Route / behavior | Category | Why it matters |
| --- | --- | --- | --- |
| Server start | launch local `llama-server` process | Operational, not an inference request | Core lifecycle requirement |
| Readiness check | `GET /health` or `GET /v1/health` | Required in initial server-first build | Needed to know when the model is actually loaded |
| Server status | local process status plus reachable health check | Operational, not an inference request | Needed for reliable CLI lifecycle control |
| Server stop | terminate managed server process cleanly | Operational, not an inference request | Needed to keep local runs repeatable |
| Model discovery | `GET /models` or `GET /v1/models` | Required in initial server-first build | Confirms model identity and server reachability |
| Plain text completion | `POST /completion`, `POST /completions`, or `POST /v1/completions` | Required in initial server-first build | Establishes non-chat generation support exposed by llama.cpp |
| Chat completion | `POST /chat/completions` or `POST /v1/chat/completions` | Required in initial server-first build | Primary path for essay-feedback prompting |
| Streaming chat completion | `POST /chat/completions` or `POST /v1/chat/completions` with `stream=true` | Required in initial server-first build | Explicitly called for by repo docs |
| JSON-constrained chat | chat completions with `response_format` or `json_schema` | Required in initial server-first build | Explicitly called for by repo docs |
| JSON-constrained completion | completions with `json_schema` or `grammar` | Required in initial server-first build | Part of llama.cpp constrained-generation surface |
| Embeddings | `POST /embeddings` or `POST /v1/embeddings` | Required in initial server-first build | A first-class llama.cpp server endpoint |
| OpenAI responses API | `POST /v1/responses` | Required in initial server-first build | Part of backend’s OpenAI-compatible route surface |
| Anthropic messages API | `POST /v1/messages` | Required in initial server-first build | Part of backend’s compatible request surface |
| Anthropic token count | `POST /v1/messages/count_tokens` | Required in initial server-first build | Companion route if Messages API is exposed |
| Reranking | `POST /v1/rerank` or `POST /v1/reranking` | Required in initial server-first build | A first-class llama.cpp server endpoint |
| Server properties read | `GET /props` | Required in initial server-first build | Useful for introspection and debugging server config |
| Server properties write | `POST /props` when server started with `--props` | Required in initial server-first build | Part of mutable server control surface |
| Router model load | `POST /models/load` | Available in backend, deferred for app scope | Only relevant for multi-model router mode |
| Router model unload | `POST /models/unload` | Available in backend, deferred for app scope | Only relevant for multi-model router mode |
| Metrics | `GET /metrics` when enabled | Available in backend, deferred for app scope | Operational monitoring, not core harness behavior |
| Slots inspection | slot-monitoring endpoints when enabled | Available in backend, deferred for app scope | Useful for deep server ops, not required initially |
| Multimodal requests | multimodal payloads through completion/chat endpoints | Available in backend, deferred for app scope | Outside current essay-feedback scope |
| Tool calling / function calling | tool-capable chat payloads | Available in backend, deferred for app scope | Backend supports it, but current app docs do not require it |

## Initial Support Contract

For the initial server-first build, Essay Lens should establish and verify the following end-to-end:

1. server start
2. readiness check
3. server status
4. server stop
5. model discovery
6. plain text completion
7. chat completion
8. streaming chat completion
9. JSON-constrained chat
10. JSON-constrained completion
11. embeddings
12. OpenAI responses API call
13. Anthropic messages API call
14. Anthropic token counting
15. reranking
16. server properties read
17. server properties write

## Verification Expectation

Once these capabilities are implemented, the verification suite must be able to:

1. launch the vendored `llama-server`
2. wait until `/health` reports ready
3. exercise each required capability with a real local request
4. validate success at the response-shape level
5. stop the server cleanly

No later development step should proceed unless that same full verification set still passes.

## Notes

- Some capabilities may require server startup flags to be enabled, especially `POST /props`, embeddings-only mode, or reranking mode.
- If the backend behavior forces certain capabilities into separate server profiles or startup modes, the verification suite should treat those as separate required server profiles rather than silently dropping coverage.
- The current Essay Lens docs mention plain chat, streaming chat, and JSON-schema chat explicitly. This matrix intentionally broadens coverage to the larger `llama-server` request surface because the project plan now prioritizes establishing every supported server call before broader harness work.
