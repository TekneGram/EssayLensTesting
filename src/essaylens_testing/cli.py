from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any, Sequence

from essaylens_testing import __version__
from essaylens_testing.client.capabilities import REQUEST_MODES, capability_payload
from essaylens_testing.client.http import (
    ServerConnection,
    get_models,
    get_props,
    post_anthropic_count_tokens,
    post_anthropic_messages,
    post_chat,
    post_chat_json,
    post_chat_stream,
    post_completion,
    post_completion_json,
    post_embeddings,
    post_props,
    post_rerank,
    post_responses,
    post_json_payload,
    post_stream_payload,
)
from essaylens_testing.client.payloads import build_request_payload
from essaylens_testing.config import parse_cli_overrides, resolve_profile, resolved_config_payload
from essaylens_testing.io import load_schema_payload, load_system_prompt, read_text_file, render_user_prompt
from essaylens_testing.paths import get_project_paths
from essaylens_testing.runs import create_run_directory, write_json, write_text
from essaylens_testing.server.manager import (
    ServerLaunchOptions,
    default_model_path,
    get_status,
    read_metadata,
    start_server,
    status_payload,
    stop_server,
    verify_server,
)
from essaylens_testing.server.runtime import get_server_runtime_info
from essaylens_testing.server.verification import verify_all_server_modes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="essaylens",
        description="CLI harness for local LLM server testing.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    info_parser = subparsers.add_parser(
        "info",
        help="Show local package and backend paths.",
    )
    info_parser.set_defaults(handler=_handle_info)

    capabilities_parser = subparsers.add_parser(
        "capabilities",
        help="Show the current app-level server capability matrix.",
    )
    capabilities_parser.set_defaults(handler=_handle_capabilities)

    request_parser = subparsers.add_parser(
        "request",
        help="Send a single request to a running llama-server.",
    )
    request_parser.add_argument(
        "mode",
        choices=REQUEST_MODES,
        help="Request mode to execute.",
    )
    request_parser.add_argument(
        "--name",
        default="default",
        help="Managed server instance name to resolve host/port from.",
    )
    request_parser.add_argument(
        "--host",
        help="Override host instead of resolving from managed server metadata.",
    )
    request_parser.add_argument(
        "--port",
        type=int,
        help="Override port instead of resolving from managed server metadata.",
    )
    request_parser.add_argument(
        "--text",
        default="Say hello in one short sentence.",
        help="Prompt or input text for request modes that need one.",
    )
    request_parser.set_defaults(handler=_handle_request)

    config_parser = subparsers.add_parser(
        "config",
        help="Config commands placeholder for later steps.",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_show_parser = config_subparsers.add_parser(
        "show",
        help="Show resolved profile configuration.",
    )
    config_show_parser.add_argument("--profile", required=True, help="Profile name to inspect.")
    config_show_parser.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Additional preset override to apply. Repeat as needed.",
    )
    config_show_parser.add_argument(
        "--set",
        action="append",
        default=[],
        help="Override config fields using section.key=value. Repeat as needed.",
    )
    config_show_parser.set_defaults(handler=_handle_config_show)

    server_parser = subparsers.add_parser(
        "server",
        help="Server lifecycle commands.",
    )
    server_subparsers = server_parser.add_subparsers(dest="server_command")

    start_parser = server_subparsers.add_parser("start", help="Start a local llama-server process.")
    _add_server_common_arguments(start_parser)
    start_parser.add_argument(
        "--device",
        default="MTL0",
        help="Device selection passed to llama-server. Use 'none' for CPU-only.",
    )
    start_parser.add_argument(
        "--ctx-size",
        type=int,
        default=8192,
        help="Context size to pass to llama-server.",
    )
    start_parser.add_argument(
        "--flash-attn",
        default="auto",
        choices=("on", "off", "auto"),
        help="Flash attention setting.",
    )
    start_parser.add_argument(
        "--cache-type-k",
        default="f16",
        help="KV cache type for K.",
    )
    start_parser.add_argument(
        "--cache-type-v",
        default="f16",
        help="KV cache type for V.",
    )
    start_parser.add_argument(
        "--enable-props",
        action="store_true",
        help="Enable POST /props on the server.",
    )
    start_parser.add_argument(
        "--enable-rerank",
        action="store_true",
        help="Enable reranking endpoints on the server.",
    )
    start_parser.add_argument(
        "--embeddings-only",
        action="store_true",
        help="Start the server in embeddings-only mode.",
    )
    start_parser.add_argument(
        "--llama-arg",
        action="append",
        default=[],
        help="Extra argument to pass through to llama-server. Repeat as needed.",
    )
    start_parser.set_defaults(handler=_handle_server_start)

    status_parser = server_subparsers.add_parser("status", help="Show managed server status.")
    _add_server_common_arguments(status_parser, include_connection=False, include_model=False)
    status_parser.set_defaults(handler=_handle_server_status)

    stop_parser = server_subparsers.add_parser("stop", help="Stop a managed server.")
    _add_server_common_arguments(stop_parser, include_connection=False, include_model=False)
    stop_parser.set_defaults(handler=_handle_server_stop)

    verify_parser = server_subparsers.add_parser(
        "verify",
        help="Confirm a managed server is running and ready.",
    )
    _add_server_common_arguments(verify_parser, include_connection=False, include_model=False)
    verify_parser.set_defaults(handler=_handle_server_verify)

    verify_all_parser = server_subparsers.add_parser(
        "verify-all",
        help="Start the server, exercise all supported request modes, and stop it cleanly.",
    )
    _add_server_common_arguments(verify_all_parser, default_name="verify", include_connection=True)
    verify_all_parser.add_argument(
        "--device",
        default="MTL0",
        help="Device selection passed to llama-server. Falls back to 'none' if startup fails.",
    )
    verify_all_parser.add_argument(
        "--ctx-size",
        type=int,
        default=8192,
        help="Context size to pass to llama-server.",
    )
    verify_all_parser.add_argument(
        "--flash-attn",
        default="auto",
        choices=("on", "off", "auto"),
        help="Flash attention setting.",
    )
    verify_all_parser.add_argument(
        "--cache-type-k",
        default="f16",
        help="KV cache type for K.",
    )
    verify_all_parser.add_argument(
        "--cache-type-v",
        default="f16",
        help="KV cache type for V.",
    )
    verify_all_parser.add_argument(
        "--llama-arg",
        action="append",
        default=[],
        help="Extra argument to pass through to llama-server. Repeat as needed.",
    )
    verify_all_parser.set_defaults(handler=_handle_server_verify_all)

    chat_parser = subparsers.add_parser(
        "chat",
        help="Run a profile-driven prompt request.",
    )
    chat_parser.add_argument("--profile", required=True, help="Profile name to use.")
    chat_parser.add_argument("--input", type=Path, help="Input file path.")
    chat_parser.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Additional preset override to apply. Repeat as needed.",
    )
    chat_parser.add_argument(
        "--system-prompt-file",
        type=Path,
        help="Override the resolved system prompt file.",
    )
    chat_parser.add_argument("--stream", action="store_true", help="Force streaming mode.")
    chat_parser.add_argument("--schema", type=Path, help="JSON schema path.")
    chat_parser.add_argument(
        "--set",
        action="append",
        default=[],
        help="Override config fields using section.key=value. Repeat as needed.",
    )
    chat_parser.add_argument(
        "--save-run",
        action="store_true",
        help="Save resolved config, prompt, and response artifacts under runs/.",
    )
    chat_parser.add_argument(
        "--start-server",
        action="store_true",
        help="Start and stop a managed server for this request.",
    )
    chat_parser.set_defaults(handler=_handle_chat)

    batch_parser = subparsers.add_parser(
        "run-batch",
        help="Run a sequential batch of prompt experiments.",
    )
    batch_parser.add_argument("--profile", required=True, help="Profile name to use.")
    batch_parser.add_argument("--batch-file", type=Path, required=True, help="Batch input TOML file.")
    batch_parser.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Additional preset override to apply to all cases. Repeat as needed.",
    )
    batch_parser.add_argument(
        "--set",
        action="append",
        default=[],
        help="Override config fields using section.key=value. Repeat as needed.",
    )
    batch_parser.add_argument("--save-run", action="store_true", help="Save run artifacts.")
    batch_parser.set_defaults(handler=_handle_run_batch)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    try:
        return handler(args)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def main_server(argv: Sequence[str] | None = None) -> int:
    server_args = ["server"]
    if argv is None:
        server_args.extend(sys.argv[1:])
    else:
        server_args.extend(argv)
    return main(server_args)


def _handle_info(_: argparse.Namespace) -> int:
    paths = get_project_paths()
    runtime = get_server_runtime_info()
    payload = {
        "repo_root": str(paths.root),
        "llama_cpp_dir": str(runtime.llama_cpp_dir),
        "llama_server_binary": str(runtime.llama_server_binary),
        "llama_server_binary_exists": runtime.binary_exists,
        "models_dir": str(paths.models_dir),
        "var_dir": str(paths.var_dir),
        "run_dir": str(paths.run_dir),
        "log_dir": str(paths.log_dir),
        "runs_dir": str(paths.runs_dir),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _handle_capabilities(_: argparse.Namespace) -> int:
    print(json.dumps(capability_payload(), indent=2, sort_keys=True))
    return 0


def _handle_request(args: argparse.Namespace) -> int:
    connection = _resolve_connection(args)
    result = _dispatch_request(args.mode, connection, args.text)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _handle_config_show(args: argparse.Namespace) -> int:
    resolved = resolve_profile(
        args.profile,
        preset_names=args.preset,
        cli_overrides=parse_cli_overrides(args.set),
    )
    print(json.dumps(resolved_config_payload(resolved), indent=2, sort_keys=True))
    return 0


def _handle_server_start(args: argparse.Namespace) -> int:
    model = args.model or default_model_path()
    options = ServerLaunchOptions(
        name=args.name,
        host=args.host,
        port=args.port,
        model=model,
        device=args.device,
        ctx_size=args.ctx_size,
        flash_attn=args.flash_attn,
        cache_type_k=args.cache_type_k,
        cache_type_v=args.cache_type_v,
        enable_props=args.enable_props,
        enable_rerank=args.enable_rerank,
        embeddings_only=args.embeddings_only,
        extra_args=tuple(args.llama_arg),
    )
    status = start_server(options)
    print(json.dumps(status_payload(status), indent=2, sort_keys=True))
    return 0


def _handle_server_status(args: argparse.Namespace) -> int:
    status = get_status(args.name)
    print(json.dumps(status_payload(status), indent=2, sort_keys=True))
    return 0


def _handle_server_stop(args: argparse.Namespace) -> int:
    status = stop_server(args.name)
    print(json.dumps(status_payload(status), indent=2, sort_keys=True))
    return 0


def _handle_server_verify(args: argparse.Namespace) -> int:
    status = verify_server(args.name)
    print(json.dumps(status_payload(status), indent=2, sort_keys=True))
    return 0


def _handle_server_verify_all(args: argparse.Namespace) -> int:
    model = args.model or default_model_path()
    options = ServerLaunchOptions(
        name=args.name,
        host=args.host,
        port=args.port,
        model=model,
        device=args.device,
        ctx_size=args.ctx_size,
        flash_attn=args.flash_attn,
        cache_type_k=args.cache_type_k,
        cache_type_v=args.cache_type_v,
        enable_props=False,
        enable_rerank=False,
        embeddings_only=False,
        extra_args=tuple(args.llama_arg),
    )
    result = verify_all_server_modes(options)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


def _handle_chat(args: argparse.Namespace) -> int:
    cli_overrides = parse_cli_overrides(args.set)
    request_cli_overrides = cli_overrides.setdefault("request", {})
    if args.stream:
        request_cli_overrides["stream"] = True
    if args.schema:
        request_cli_overrides["schema_file"] = str(args.schema)
    if args.system_prompt_file:
        request_cli_overrides["system_prompt_file"] = str(args.system_prompt_file)
    if args.input:
        request_cli_overrides["input_file"] = str(args.input)

    resolved = resolve_profile(
        args.profile,
        preset_names=args.preset,
        cli_overrides=cli_overrides,
    )
    execution = _execute_resolved_request(
        resolved,
        run_label=args.profile,
        save_run=args.save_run,
        start_server=args.start_server,
    )
    print(json.dumps(execution["result"], indent=2, sort_keys=True))
    return 0


def _handle_run_batch(args: argparse.Namespace) -> int:
    batch_path = args.batch_file
    with batch_path.open("rb") as handle:
        payload = tomllib.load(handle)

    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise RuntimeError("Batch file must define at least one [[cases]] entry.")

    batch_cli_overrides = parse_cli_overrides(args.set)
    cases: list[dict[str, Any]] = []
    run_dir = create_run_directory(f"batch-{args.profile}") if args.save_run else None
    server_started = False
    active_name = f"batch-{args.profile}"

    try:
        for index, raw_case in enumerate(raw_cases, start=1):
            if not isinstance(raw_case, dict):
                raise RuntimeError("Each [[cases]] entry must be a TOML table.")
            case_name = str(raw_case.get("name") or f"case-{index}")
            case_presets = [*args.preset, *[str(item) for item in raw_case.get("presets", [])]]
            case_overrides = _merge_cli_override_dicts(
                batch_cli_overrides,
                {
                    "model": dict(raw_case.get("model_overrides", {})),
                    "server": dict(raw_case.get("server_overrides", {})),
                    "request": dict(raw_case.get("request_overrides", {})),
                },
            )
            request_case_overrides = case_overrides.setdefault("request", {})
            if raw_case.get("input_file"):
                request_case_overrides["input_file"] = str(raw_case["input_file"])
            if raw_case.get("prompt_file"):
                request_case_overrides["prompt_file"] = str(raw_case["prompt_file"])
            if raw_case.get("system_prompt_file"):
                request_case_overrides["system_prompt_file"] = str(raw_case["system_prompt_file"])
            if raw_case.get("schema_file"):
                request_case_overrides["schema_file"] = str(raw_case["schema_file"])
            if "stream" in raw_case:
                request_case_overrides["stream"] = bool(raw_case["stream"])

            resolved = resolve_profile(
                args.profile,
                preset_names=case_presets,
                cli_overrides=case_overrides,
            )
            if not server_started:
                _start_managed_server_for_resolved(resolved, active_name)
                server_started = True
            else:
                current_server_options = _server_identity_tuple(resolved)
                previous_server_options = _server_identity_tuple(cases[-1]["resolved"])
                if current_server_options != previous_server_options:
                    stop_server(active_name)
                    _start_managed_server_for_resolved(resolved, active_name)

            execution = _execute_resolved_request(
                resolved,
                run_label=case_name,
                save_run=False,
                start_server=False,
                managed_name=active_name,
            )
            case_record = {
                "name": case_name,
                "resolved": resolved,
                "payload": resolved_config_payload(resolved),
                "result": execution["result"],
            }
            cases.append(case_record)
            if run_dir is not None:
                case_dir = run_dir / f"{index:03d}-{case_name}"
                case_dir.mkdir(parents=True, exist_ok=True)
                write_json(case_dir / "resolved_config.json", case_record["payload"])
                write_json(case_dir / "request_payload.json", execution["request_payload"])
                write_json(case_dir / "response.json", execution["result"])
                write_text(case_dir / "user_prompt.txt", execution["user_prompt"])
                if execution["system_prompt"] is not None:
                    write_text(case_dir / "system_prompt.txt", execution["system_prompt"])
    finally:
        if server_started:
            stop_server(active_name)

    summary = {
        "profile": args.profile,
        "count": len(cases),
        "cases": [
            {
                "name": item["name"],
                "result": item["result"],
            }
            for item in cases
        ],
    }
    if run_dir is not None:
        summary["run_dir"] = str(run_dir)
        write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _not_implemented(args: argparse.Namespace) -> int:
    command_path = [args.command]
    for attr in ("config_command", "server_command"):
        value = getattr(args, attr, None)
        if value:
            command_path.append(value)
    joined = " ".join(part for part in command_path if part)
    raise SystemExit(f"`{joined}` is reserved for a later development step.")


def _add_server_common_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_name: str = "default",
    include_connection: bool = True,
    include_model: bool = True,
) -> None:
    parser.add_argument(
        "--name",
        default=default_name,
        help="Managed server instance name.",
    )
    parser.add_argument(
        "--profile",
        help="Reserved for a later config-driven step.",
    )
    if include_connection:
        parser.add_argument(
            "--host",
            default="127.0.0.1",
            help="Host to bind the llama-server process to.",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8080,
            help="Port to bind the llama-server process to.",
        )
    if include_model:
        parser.add_argument(
            "--model",
            type=Path,
            help="Model path. Defaults to the first GGUF under assets/models.",
        )


def _resolve_connection(args: argparse.Namespace) -> ServerConnection:
    if args.host and args.port:
        return ServerConnection(host=args.host, port=args.port)

    status = get_status(args.name)
    if status.running and status.host and status.port:
        return ServerConnection(host=status.host, port=status.port)

    paths = get_project_paths()
    metadata_path = paths.run_dir / f"{args.name}.json"
    metadata = read_metadata(metadata_path)
    host = metadata.get("host")
    port = metadata.get("port")
    if not host or not port:
        raise RuntimeError(
            "Could not resolve server connection. Provide --host and --port or start a managed server first."
        )
    return ServerConnection(host=str(host), port=int(port))


def _dispatch_request(mode: str, connection: ServerConnection, text: str) -> object:
    if mode == "models":
        return get_models(connection)
    if mode == "completion":
        return post_completion(connection, text)
    if mode == "chat":
        return post_chat(connection, text)
    if mode == "chat-stream":
        return post_chat_stream(connection, text)
    if mode == "chat-json":
        return post_chat_json(connection, text)
    if mode == "completion-json":
        return post_completion_json(connection, text)
    if mode == "embeddings":
        return post_embeddings(connection, text)
    if mode == "responses":
        return post_responses(connection, text)
    if mode == "anthropic-messages":
        return post_anthropic_messages(connection, text)
    if mode == "anthropic-count-tokens":
        return post_anthropic_count_tokens(connection, text)
    if mode == "rerank":
        return post_rerank(connection, text)
    if mode == "props-get":
        return get_props(connection)
    if mode == "props-set":
        return post_props(connection)
    raise RuntimeError(f"Unsupported request mode: {mode}")


def _execute_resolved_request(
    resolved,
    *,
    run_label: str,
    save_run: bool,
    start_server: bool,
    managed_name: str | None = None,
) -> dict[str, Any]:
    request = resolved.request
    input_text = None
    if request.input_file:
        input_text = read_text_file(request.input_file)
    user_prompt = render_user_prompt(request, input_text=input_text)
    system_prompt = load_system_prompt(request)
    schema = load_schema_payload(request)
    path, payload = build_request_payload(
        request,
        model=resolved.model,
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        schema=schema,
    )

    server_name = managed_name or resolved.profile_name
    if start_server:
        _start_managed_server_for_resolved(resolved, server_name)
    try:
        connection = _resolve_connection_from_resolved(resolved, server_name)
        if request.stream:
            result = post_stream_payload(connection, path, payload)
        else:
            result = post_json_payload(connection, path, payload)
    finally:
        if start_server:
            stop_server(server_name)

    artifact_dir = None
    if save_run:
        artifact_dir = create_run_directory(run_label)
        write_json(artifact_dir / "resolved_config.json", resolved_config_payload(resolved))
        write_json(artifact_dir / "request_payload.json", payload)
        write_json(artifact_dir / "response.json", result)
        write_text(artifact_dir / "user_prompt.txt", user_prompt)
        if system_prompt is not None:
            write_text(artifact_dir / "system_prompt.txt", system_prompt)

    execution: dict[str, Any] = {
        "result": result,
        "user_prompt": user_prompt,
        "system_prompt": system_prompt,
        "request_payload": payload,
    }
    if artifact_dir is not None:
        execution["run_dir"] = str(artifact_dir)
    return execution


def _resolve_connection_from_resolved(resolved, server_name: str) -> ServerConnection:
    status = get_status(server_name)
    if status.running and status.host and status.port:
        return ServerConnection(host=status.host, port=status.port)
    return ServerConnection(host=resolved.server.host, port=resolved.server.port)


def _start_managed_server_for_resolved(resolved, name: str) -> None:
    current = get_status(name)
    if current.running:
        stop_server(name)
    options = ServerLaunchOptions(
        name=name,
        host=resolved.server.host,
        port=resolved.server.port,
        model=resolved.model.path,
        device=resolved.server.device,
        ctx_size=resolved.server.ctx_size,
        flash_attn=resolved.server.flash_attn,
        cache_type_k=resolved.server.cache_type_k,
        cache_type_v=resolved.server.cache_type_v,
        enable_props=resolved.server.enable_props,
        enable_rerank=resolved.server.enable_rerank,
        embeddings_only=resolved.server.embeddings_only,
        extra_args=resolved.server.extra_args,
    )
    start_server(options)


def _server_identity_tuple(resolved) -> tuple[object, ...]:
    server = resolved.server
    return (
        str(resolved.model.path),
        server.host,
        server.port,
        server.device,
        server.ctx_size,
        server.flash_attn,
        server.cache_type_k,
        server.cache_type_v,
        server.enable_props,
        server.enable_rerank,
        server.embeddings_only,
        tuple(server.extra_args),
    )


def _merge_cli_override_dicts(
    base: dict[str, dict[str, Any]],
    extra: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    merged = {
        "model": dict(base.get("model", {})),
        "server": dict(base.get("server", {})),
        "request": dict(base.get("request", {})),
    }
    for section in ("model", "server", "request"):
        merged[section].update(extra.get(section, {}))
    return merged
