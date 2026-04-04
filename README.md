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

The current scaffold exposes direct server lifecycle and request commands. The profile/config-driven workflow described above is planned, but it is not the current user-facing path yet.

### Show local paths and capability surface

```bash
essaylens info
essaylens capabilities
```

### Start a server

By default, `essaylens-server` now prefers Metal for normal local use.

```bash
essaylens-server start --port 8080
```

If you want CPU-only instead:

```bash
essaylens-server start --port 8080 --device none
```

You can also pass the model path explicitly:

```bash
essaylens-server start \
  --port 8080 \
  --model assets/models/gemma-4-E4B-it-Q4_K_M.gguf \
  --ctx-size 2048
```

### Check server status and readiness

```bash
essaylens-server status
essaylens-server verify
```

### Stop a managed server

```bash
essaylens-server stop
```

### Send requests to a running server

Using an explicit host and port:

```bash
essaylens request models --host 127.0.0.1 --port 8080
essaylens request completion --host 127.0.0.1 --port 8080 --text "Essay feedback should be"
essaylens request chat --host 127.0.0.1 --port 8080 --text "Give feedback on this essay."
essaylens request chat-stream --host 127.0.0.1 --port 8080 --text "Count from 1 to 3."
essaylens request chat-json --host 127.0.0.1 --port 8080 --text "Return a JSON object with answer set to hello."
essaylens request completion-json --host 127.0.0.1 --port 8080 --text "Return a JSON object with answer set to hello."
essaylens request embeddings --host 127.0.0.1 --port 8080 --text "Essay feedback should be specific."
essaylens request responses --host 127.0.0.1 --port 8080 --text "Say hello in one short sentence."
essaylens request anthropic-messages --host 127.0.0.1 --port 8080 --text "Say hello in one short sentence."
essaylens request anthropic-count-tokens --host 127.0.0.1 --port 8080 --text "Say hello in one short sentence."
essaylens request rerank --host 127.0.0.1 --port 8080 --text "Which sentence is about essay feedback?"
essaylens request props-get --host 127.0.0.1 --port 8080
essaylens request props-set --host 127.0.0.1 --port 8080
```

If you started the default managed server, you can omit host and port:

```bash
essaylens request chat --name default --text "Give feedback on this essay."
```

### Direct `llama-server` invocation

If you want to bypass the Python CLI entirely:

```bash
third_party/llama-cpp-turboquant/build/bin/llama-server \
  --host 127.0.0.1 \
  --port 8080 \
  --model assets/models/gemma-4-E4B-it-Q4_K_M.gguf \
  --ctx-size 2048
```

### Verifying Metal use

When running in a normal local Terminal session, check the server log for Metal usage:

```bash
grep -nE "using device|offloading|MTL" /tmp/llama_server_metal.log
```


## Running a simple first experiment

This is the shortest end-to-end setup for running the sample essay experiment in a fresh environment.

### 1. Build the backend server

```bash
cd third_party/llama-cpp-turboquant
cmake -B build -DLLAMA_BUILD_SERVER=ON -DGGML_METAL=ON
cmake --build build --target llama-server -j
cd ../..
```

### 2. Install the Python package

After making sure you are in a python environment:

```bash
python3 -m pip install -e .
```

### 3. Confirm the sample model path

The sample profile uses [configs/models/gemma4.toml](/Users/danielparsons/Documents/Development/EssayLensTesting/configs/models/gemma4.toml), which points to:

```text
assets/models/gemma-4-E4B-it-Q4_K_M.gguf
```

If your GGUF file has a different name, update that config file first.

### 4. Inspect the resolved experiment config

```bash
essaylens config show --profile essay-feedback
```

### 5. Start the server with Metal

```bash
essaylens-server start \
  --model assets/models/gemma-4-E4B-it-Q4_K_M.gguf \
  --device MTL0 \
  --ctx-size 8192 \
  --flash-attn on
```

Verify it is ready:

```bash
essaylens-server verify
```

### 6. Run the sample essay experiment

This uses [inputs/sample_essay.md](/Users/danielparsons/Documents/Development/EssayLensTesting/inputs/sample_essay.md) with the `essay-feedback` profile.

```bash
essaylens chat \
  --profile essay-feedback \
  --input inputs/sample_essay.md
```

### 7. Save run artifacts

```bash
essaylens chat \
  --profile essay-feedback \
  --input inputs/sample_essay.md \
  --save-run
```

This writes resolved config, prompts, request payload, and response artifacts under `runs/`.

### 8. Try a KV/cache experiment

```bash
essaylens chat \
  --profile essay-feedback \
  --input inputs/sample_essay.md \
  --preset kv-turbo3 \
  --preset ctx-32k \
  --save-run
```

### 9. Run the sample batch file

The sample batch file is [inputs/essay_batch.toml](/Users/danielparsons/Documents/Development/EssayLensTesting/inputs/essay_batch.toml).

```bash
essaylens run-batch \
  --profile essay-feedback \
  --batch-file inputs/essay_batch.toml \
  --save-run
```

### 10. Stop the server

```bash
essaylens-server stop
```
