# Essay Lens Testing

This repo is a local CLI harness for testing Essay Lens prompts against local LLM servers, starting with the vendored `llama.cpp` server in `third_party/llama-cpp-turboquant`.

## What is here

- `bin/essaylens`: main CLI wrapper
- `bin/essaylens-server`: server-only wrapper around `essaylens server ...`
- `configs/models`: model-level config such as model path, alias, and template
- `configs/servers`: server runtime config such as port, context size, and KV-cache settings
- `configs/requests`: request-time generation config such as temperature, streaming, and JSON mode
- `configs/profiles`: user-facing combinations of model + server + request config
- `configs/presets`: optional reusable overrides for context or cache experiments
- `prompts`: prompt files and JSON schemas
- `inputs`: source files for CLI-driven testing
- `src/essaylens_testing`: Python package for the CLI, config loader, server launcher, and clients

## Requirements

- Python 3.11+
- A built `llama-server` binary under `third_party/llama-cpp-turboquant/build/...`

## Install

### 1. Build the backend server

One example flow:

```bash
cd third_party/llama-cpp-turboquant
cmake -B build -DLLAMA_BUILD_SERVER=ON
cmake --build build --target llama-server -j
cd ../..
```

### 2. Install the CLI

Inside the repo root:

```bash
python3 -m pip install -e .
```

You can also skip installation and call the wrappers directly:

```bash
./bin/essaylens --help
./bin/essaylens-server --help
```

## Config model

Profiles are the main unit you switch between.

- `models/*.toml`: model path and model-specific metadata
- `servers/*.toml`: server process flags including KV-cache settings
- `requests/*.toml`: inference request defaults
- `profiles/*.toml`: references to one model, one server config, one request config, plus local overrides
- `presets/*.toml`: reusable experiment tweaks

Example profile:

```toml
model = "gemma4"
server = "llama-cpp-default"
request = "default-chat"
presets = ["kv-cache-reuse"]
```

## Usage

### Inspect a profile

```bash
essaylens config show --profile local-gemma-fast
```

### Start a server

```bash
essaylens server start --profile local-gemma-fast
```

### Check status

```bash
essaylens server status --profile local-gemma-fast
```

### Stop a server

```bash
essaylens server stop --profile local-gemma-fast
```

### Simple chat from a file

```bash
essaylens chat \
  --profile local-gemma-fast \
  --input inputs/essays/sample_essay.md
```

### Streaming chat

```bash
essaylens chat \
  --profile long-context-eval \
  --input inputs/essays/sample_essay.md \
  --stream
```

### JSON schema chat

```bash
essaylens chat \
  --profile local-gemma-json \
  --input inputs/essays/sample_essay.md \
  --schema prompts/schemas/essay_feedback.schema.json
```

### Batch run from a list of files

Create a text file with one input path per line, then run:

```bash
essaylens run-batch \
  --profile local-gemma-fast \
  --batch-file inputs/batches/my_batch.txt \
  --save-run
```

## Runtime files

- PID files: `var/run/*.pid`
- Server logs: `var/log/*.log`
- Saved request and response artifacts: `runs/*`

These are ignored by git.

## First-pass scope

The current scaffold supports:

- local `llama-server` lifecycle management
- plain chat
- streaming chat
- JSON-schema chat
- file-driven terminal usage
- split configuration for model, server, request, profile, and cache experiments

Not implemented yet:

- multi-turn persisted conversations
- automatic summarization of overflowing context
- model-agnostic adapters beyond `llama.cpp`
- judge/evaluation pipelines
- benchmark dashboards
