from __future__ import annotations

import argparse
import json
from pathlib import Path

from essaylens_testing.config.loader import ConfigLoader
from essaylens_testing.context.file_ingest import read_text_file
from essaylens_testing.experiments.batch_run import iter_batch_file
from essaylens_testing.experiments.run_once import run_chat
from essaylens_testing.server.launcher import ServerLauncher


REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="essaylens", description="Essay Lens local LLM testing CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    server_parser = subparsers.add_parser("server", help="Manage the local LLM server process")
    server_subparsers = server_parser.add_subparsers(dest="server_command", required=True)
    for name in ("start", "stop", "status"):
        action_parser = server_subparsers.add_parser(name)
        action_parser.add_argument("--profile", required=True)

    chat_parser = subparsers.add_parser("chat", help="Send a single prompt from a file or inline text")
    chat_parser.add_argument("--profile", required=True)
    source_group = chat_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", type=Path, help="Path to a text or markdown file")
    source_group.add_argument("--text", help="Inline prompt text")
    chat_parser.add_argument("--system", type=Path, help="Override system prompt file")
    chat_parser.add_argument("--stream", action="store_true", help="Use streaming mode")
    chat_parser.add_argument("--schema", type=Path, help="JSON schema file for structured output")
    chat_parser.add_argument("--save-run", action="store_true", help="Save request and response artifacts")

    batch_parser = subparsers.add_parser("run-batch", help="Run each input listed in a batch file")
    batch_parser.add_argument("--profile", required=True)
    batch_parser.add_argument("--batch-file", type=Path, required=True)
    batch_parser.add_argument("--stream", action="store_true")
    batch_parser.add_argument("--save-run", action="store_true")

    config_parser = subparsers.add_parser("config", help="Inspect resolved profile configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    config_show = config_subparsers.add_parser("show")
    config_show.add_argument("--profile", required=True)

    return parser


def _require_healthy_server(launcher: ServerLauncher, profile_name: str) -> None:
    status = launcher.status(profile_name)
    if not status.running:
        raise SystemExit(
            f"Server for profile '{profile_name}' is not running. Start it with: essaylens server start --profile {profile_name}"
        )


def _handle_server(args: argparse.Namespace) -> int:
    launcher = ServerLauncher(REPO_ROOT)
    if args.server_command == "start":
        status = launcher.start(args.profile)
        print(json.dumps({"running": status.running, "pid": status.pid, "base_url": status.base_url}, indent=2))
        return 0
    if args.server_command == "stop":
        launcher.stop(args.profile)
        print(f"Stopped server for profile '{args.profile}'.")
        return 0
    if args.server_command == "status":
        status = launcher.status(args.profile)
        print(json.dumps({"running": status.running, "pid": status.pid, "base_url": status.base_url}, indent=2))
        return 0
    raise SystemExit(f"Unknown server subcommand: {args.server_command}")


def _handle_chat(args: argparse.Namespace) -> int:
    loader = ConfigLoader(REPO_ROOT)
    profile = loader.load_profile(args.profile)
    launcher = ServerLauncher(REPO_ROOT)
    _require_healthy_server(launcher, args.profile)

    input_text = args.text if args.text is not None else read_text_file(args.input)
    schema_path = args.schema
    if schema_path is None and profile.request.json_schema_path:
        schema_path = Path(profile.request.json_schema_path)
    if schema_path is not None and not schema_path.is_absolute():
        schema_path = (REPO_ROOT / schema_path).resolve()

    system_path = args.system
    if system_path is not None and not system_path.is_absolute():
        system_path = (REPO_ROOT / system_path).resolve()

    text, run_dir = run_chat(
        repo_root=REPO_ROOT,
        profile=profile,
        input_text=input_text,
        stream=args.stream or profile.request.stream,
        schema_path=schema_path,
        system_prompt_path=system_path,
        save_run=args.save_run,
    )
    print(text)
    if run_dir is not None:
        print(f"\n[run saved to {run_dir}]")
    return 0


def _handle_batch(args: argparse.Namespace) -> int:
    loader = ConfigLoader(REPO_ROOT)
    profile = loader.load_profile(args.profile)
    launcher = ServerLauncher(REPO_ROOT)
    _require_healthy_server(launcher, args.profile)

    for entry in iter_batch_file(args.batch_file):
        input_path = Path(entry)
        if not input_path.is_absolute():
            input_path = (REPO_ROOT / input_path).resolve()
        input_text = read_text_file(input_path)
        text, run_dir = run_chat(
            repo_root=REPO_ROOT,
            profile=profile,
            input_text=input_text,
            stream=args.stream or profile.request.stream,
            save_run=args.save_run,
        )
        print(f"=== {input_path.name} ===")
        print(text)
        if run_dir is not None:
            print(f"[run saved to {run_dir}]")
    return 0


def _handle_config(args: argparse.Namespace) -> int:
    loader = ConfigLoader(REPO_ROOT)
    print(loader.render_profile_json(args.profile))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "server":
        return _handle_server(args)
    if args.command == "chat":
        return _handle_chat(args)
    if args.command == "run-batch":
        return _handle_batch(args)
    if args.command == "config":
        return _handle_config(args)
    raise SystemExit(f"Unknown command: {args.command}")


def main_server(argv: list[str] | None = None) -> int:
    return main(["server", *(argv or [])])


if __name__ == "__main__":
    raise SystemExit(main())
