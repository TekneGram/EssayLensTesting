from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from essaylens_testing.paths import ensure_runtime_directories


@dataclass(frozen=True)
class ServerLaunchOptions:
    name: str
    host: str
    port: int
    model: Path
    device: str
    ctx_size: int
    flash_attn: str
    cache_type_k: str
    cache_type_v: str
    enable_props: bool
    enable_rerank: bool
    embeddings_only: bool
    extra_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class ServerInstancePaths:
    pid_file: Path
    meta_file: Path
    log_file: Path


@dataclass(frozen=True)
class ServerStatus:
    name: str
    pid: int | None
    running: bool
    reachable: bool
    ready: bool
    host: str | None
    port: int | None
    model: str | None
    pid_file: str
    meta_file: str
    log_file: str


def default_model_path() -> Path:
    paths = ensure_runtime_directories()
    candidates = sorted(
        path for path in paths.models_dir.glob("*.gguf") if path.is_file()
    )
    if not candidates:
        raise FileNotFoundError("No GGUF model found under assets/models.")
    return candidates[0]


def instance_paths(name: str) -> ServerInstancePaths:
    paths = ensure_runtime_directories()
    return ServerInstancePaths(
        pid_file=paths.run_dir / f"{name}.pid",
        meta_file=paths.run_dir / f"{name}.json",
        log_file=paths.log_dir / f"{name}.log",
    )


def build_server_command(options: ServerLaunchOptions) -> list[str]:
    paths = ensure_runtime_directories()
    command = [
        str(paths.llama_server_binary),
        "--host",
        options.host,
        "--port",
        str(options.port),
        "--model",
        str(options.model),
        "--device",
        options.device,
        "--ctx-size",
        str(options.ctx_size),
        "--flash-attn",
        options.flash_attn,
        "--cache-type-k",
        options.cache_type_k,
        "--cache-type-v",
        options.cache_type_v,
    ]
    if options.enable_props:
        command.append("--props")
    if options.enable_rerank:
        command.append("--reranking")
    if options.embeddings_only:
        command.append("--embedding")
    command.extend(options.extra_args)
    return command


def start_server(options: ServerLaunchOptions, timeout_seconds: float = 120.0) -> ServerStatus:
    paths = ensure_runtime_directories()
    if not paths.llama_server_binary.exists():
        raise FileNotFoundError(
            f"llama-server binary not found at {paths.llama_server_binary}"
        )
    if not options.model.exists():
        raise FileNotFoundError(f"Model not found at {options.model}")

    current = get_status(options.name)
    if current.running:
        raise RuntimeError(f"Server '{options.name}' is already running.")

    files = instance_paths(options.name)
    command = build_server_command(options)

    process_pid = spawn_detached_process(command=command, cwd=paths.root, log_file=files.log_file)

    metadata = {
        "name": options.name,
        "pid": process_pid,
        "host": options.host,
        "port": options.port,
        "model": str(options.model),
        "device": options.device,
        "ctx_size": options.ctx_size,
        "flash_attn": options.flash_attn,
        "cache_type_k": options.cache_type_k,
        "cache_type_v": options.cache_type_v,
        "enable_props": options.enable_props,
        "enable_rerank": options.enable_rerank,
        "embeddings_only": options.embeddings_only,
        "extra_args": list(options.extra_args),
        "command": command,
        "started_at": time.time(),
        "log_file": str(files.log_file),
    }
    files.pid_file.write_text(f"{process_pid}\n", encoding="utf-8")
    files.meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not pid_is_running(process_pid):
            raise RuntimeError(
                f"llama-server exited early. Check {files.log_file}"
            )
        ready, reachable = probe_health(options.host, options.port)
        if ready:
            return get_status(options.name)
        time.sleep(1.0 if not reachable else 0.5)

    raise TimeoutError(f"Timed out waiting for server '{options.name}' to become ready.")


def stop_server(name: str, timeout_seconds: float = 30.0) -> ServerStatus:
    status = get_status(name)
    if not status.pid or not status.running:
        return status

    os.kill(status.pid, signal.SIGTERM)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not pid_is_running(status.pid):
            cleanup_instance_files(name)
            return get_status(name)
        time.sleep(0.5)

    os.kill(status.pid, signal.SIGKILL)
    cleanup_instance_files(name)
    return get_status(name)


def verify_server(name: str) -> ServerStatus:
    status = get_status(name)
    if not status.running:
        raise RuntimeError(f"Server '{name}' is not running.")
    if not status.ready:
        raise RuntimeError(f"Server '{name}' is running but not ready.")
    return status


def get_status(name: str) -> ServerStatus:
    files = instance_paths(name)
    metadata = read_metadata(files.meta_file)
    pid = read_pid(files.pid_file)
    running = pid_is_running(pid) if pid is not None else False
    if pid is not None and not running:
        cleanup_instance_files(name)
        pid = None
        metadata = {}

    host = metadata.get("host")
    port = metadata.get("port")
    model = metadata.get("model")
    ready = False
    reachable = False
    if running and host and port:
        ready, reachable = probe_health(host, int(port))

    return ServerStatus(
        name=name,
        pid=pid,
        running=running,
        reachable=reachable,
        ready=ready,
        host=host,
        port=port,
        model=model,
        pid_file=str(files.pid_file),
        meta_file=str(files.meta_file),
        log_file=str(files.log_file),
    )


def probe_health(host: str, port: int, timeout_seconds: float = 2.0) -> tuple[bool, bool]:
    url = f"http://{host}:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("status") == "ok", True
    except urllib.error.HTTPError as exc:
        if exc.code == 503:
            return False, True
        return False, False
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False, False


def read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    raw_value = pid_file.read_text(encoding="utf-8").strip()
    if not raw_value:
        return None
    return int(raw_value)


def read_metadata(meta_file: Path) -> dict[str, object]:
    if not meta_file.exists():
        return {}
    return json.loads(meta_file.read_text(encoding="utf-8"))


def pid_is_running(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def cleanup_instance_files(name: str) -> None:
    files = instance_paths(name)
    for path in (files.pid_file, files.meta_file):
        try:
            path.unlink()
        except FileNotFoundError:
            continue


def status_payload(status: ServerStatus) -> dict[str, object]:
    return asdict(status)


def spawn_detached_process(command: list[str], cwd: Path, log_file: Path) -> int:
    if os.name != "posix":
        with log_file.open("ab") as log_handle:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        return process.pid

    read_fd, write_fd = os.pipe()
    first_pid = os.fork()
    if first_pid == 0:
        try:
            os.close(read_fd)
            os.setsid()
            second_pid = os.fork()
            if second_pid > 0:
                os.write(write_fd, str(second_pid).encode("utf-8"))
                os._exit(0)

            os.chdir(cwd)
            with open(os.devnull, "rb", buffering=0) as stdin_handle:
                with log_file.open("ab", buffering=0) as log_handle:
                    os.dup2(stdin_handle.fileno(), 0)
                    os.dup2(log_handle.fileno(), 1)
                    os.dup2(log_handle.fileno(), 2)
                    os.execv(command[0], command)
        finally:
            os._exit(1)

    os.close(write_fd)
    pid_bytes = os.read(read_fd, 64)
    os.close(read_fd)
    os.waitpid(first_pid, 0)
    if not pid_bytes:
        raise RuntimeError("Failed to detach llama-server process.")
    return int(pid_bytes.decode("utf-8"))
