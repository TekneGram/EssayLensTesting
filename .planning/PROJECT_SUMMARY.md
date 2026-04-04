# Project Summary

Essay Lens Testing is a local, CLI-first harness for testing essay-feedback prompts against local LLM inference servers. The immediate goal is to evaluate how prompt behavior changes under different local-model conditions, especially across different context lengths and KV-cache strategies, while keeping the workflow file-oriented and easy to reproduce.

The intended scaffold separates configuration into distinct layers so experiments can swap one axis at a time:

- model config
- server/runtime config
- request/inference config
- profile composition
- optional experiment presets

The current backend target is `llama.cpp`, wrapped as a thin local server adapter. In this repository, that backend is the vendored TurboQuant-enabled fork under `third_party/llama-cpp-turboquant`, not upstream vanilla `llama.cpp`.

## Backend Version

The vendored inference backend matches the TurboQuant fork described in the SOTAAZ article "TurboQuant in Practice — KV Cache Compression with llama.cpp and HuggingFace":

- repository: `https://github.com/TheTom/llama-cpp-turboquant.git`
- branch: `feature/turboquant-kv-cache`
- current vendored commit: `63b832bc0799ba7270e695e0987d0bd2272bdc7e`

This fork is used so the harness can experiment with KV-cache quantization modes such as `turbo3` and `turbo4`, which are central to the repository's design intent.

## Build Intent

The app should be developed as an editable Python package with a local CLI entry point, while relying on a separately built local `llama-server` binary from the vendored TurboQuant fork.

The expected build flow is:

1. Build `llama-server` from `third_party/llama-cpp-turboquant`
2. Install the Python package in editable mode with `python3 -m pip install -e .`
3. Use the `essaylens` CLI to start servers, verify them, and send requests

The most important operational requirement is that the harness must be able to start the local server and successfully perform every supported request type against it before higher-level experiment features are added.
