# Development Plan

## Principle

Server functionality comes first. Before building broader harness features, the project must be able to start the local `llama.cpp` server and successfully perform every supported request type against it. After that point, every later development step must re-verify that the full server workflow still works unchanged.

Normal local Terminal validation is the source of truth for Metal/GPU verification. Codex-managed runs may not have reliable Metal device access, so GPU-capability checks must be confirmed in a standard user shell before treating Metal as broken on the machine.

For user-facing defaults, the app should prefer Metal/GPU execution when available. CPU fallback is a Codex-sandbox testing workaround only and must not become the normal default behavior for local users.

## Step-by-Step Plan

1. Define the complete server capability matrix up front.
   Establish the exact set of server behaviors the harness must support before anything else is built. At minimum this includes:
   - server start
   - readiness check
   - server status
   - server stop
   - plain chat requests
   - streaming chat requests
   - JSON-schema chat requests
   - any additional llama.cpp/OpenAI-compatible call the harness intends to expose
   This matrix is recorded in `SERVER_CAPABILITY_MATRIX.md` and becomes the contract for all later verification work.

2. Build only the minimum editable Python package needed to drive those server behaviors.
   Create the package/module structure required for `pip install -e .` and for a CLI that can launch, query, and stop the vendored `llama-server`.

3. Implement server process management first.
   Add binary resolution, command construction, launch, PID tracking, log capture, readiness polling, status, and clean shutdown. Do not add experiment orchestration, batching, or judge logic here.

4. Implement every supported request mode against a real running server.
   Add end-to-end support for plain chat, streaming chat, JSON-schema chat, and any other required llama.cpp request mode. These should be real local requests to the actual server, not only mocked abstractions.

5. Create a single repeatable server verification suite.
   This suite should:
   - start the server
   - wait for readiness
   - exercise every supported request mode
   - confirm each response is valid enough to prove success
   - stop the server cleanly
   - record whether verification was performed in a normal local Terminal session or in a Codex-managed environment when GPU/Metal is involved

6. Make the full server verification suite the gate for every later step.
   No later work counts as complete unless the same suite still passes after the change.

7. Add the config system on top of the already-working server workflow.
   Implement TOML loading for model, server, request, profile, and preset configuration only after direct server usage is proven. Re-run the full verification suite using config-driven inputs.

8. Add the user-facing CLI commands on top of the verified server layer.
   Expose commands such as `config show`, `server start`, `server status`, `server stop`, `chat`, streaming chat, and JSON-schema chat through the editable install. Re-run the full verification suite through the CLI path.

9. Add batch execution only after all single-request server modes are stable.
   Implement batch behavior as a thin wrapper around the already-verified request paths. Re-run the full server verification suite before and after adding batch-specific checks.

10. Add evaluation, judge, and experiment features last.
    Only after server lifecycle and all request modes are stable under the editable install should the project add metrics, comparison workflows, judge-model evaluation, or other experiment-layer features. Each such step still requires the unchanged full server verification suite to pass.

## Completion Rule

After step 4, every subsequent change must preserve this invariant:

- the app can start the server
- the app can verify readiness
- the app can perform every supported server request type
- the app can stop the server cleanly

If any of those regress, the step is not done.

## Environment Note

Metal verification has already been tested on this machine and is known to work in a normal Terminal session with the local `llama.cpp` server build. A prior Metal failure observed from within Codex was environmental rather than a confirmed `llama.cpp` or machine-level problem.

Because of that, server verification should distinguish between:

- normal local shell verification, which is authoritative for Metal/GPU support
- Codex-managed verification, which is still useful for CPU/server logic but may not reliably prove Metal availability

Accordingly:

- `essaylens-server` should default to Metal-oriented local execution for the user
- CPU-only execution should be used by Codex only when sandbox constraints prevent reliable Metal validation
- documentation and error messages should not steer the user toward CPU as the default path unless Metal has actually failed in the user's own shell
