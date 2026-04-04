from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

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
)
from essaylens_testing.paths import get_project_paths
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
        help="Placeholder for profile inspection.",
    )
    config_show_parser.add_argument("--profile", help="Profile name to inspect.")
    config_show_parser.set_defaults(handler=_not_implemented)

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

    chat_parser = subparsers.add_parser(
        "chat",
        help="Placeholder for chat requests.",
    )
    chat_parser.add_argument("--profile", help="Profile name to use.")
    chat_parser.add_argument("--input", type=Path, help="Input file path.")
    chat_parser.add_argument("--stream", action="store_true", help="Enable streaming mode.")
    chat_parser.add_argument("--schema", type=Path, help="JSON schema path.")
    chat_parser.set_defaults(handler=_not_implemented)

    batch_parser = subparsers.add_parser(
        "run-batch",
        help="Placeholder for batch execution.",
    )
    batch_parser.add_argument("--profile", help="Profile name to use.")
    batch_parser.add_argument("--batch-file", type=Path, help="Batch input file.")
    batch_parser.add_argument("--save-run", action="store_true", help="Save run artifacts.")
    batch_parser.set_defaults(handler=_not_implemented)

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
    include_connection: bool = True,
    include_model: bool = True,
) -> None:
    parser.add_argument(
        "--name",
        default="default",
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
