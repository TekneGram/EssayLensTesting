from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from essaylens_testing.config.schema import ProfileConfig
from essaylens_testing.server.adapters.llama_cpp import base_url, build_server_command, resolve_binary


class ServerProcessError(RuntimeError):
    """Raised for server lifecycle failures."""


@dataclass
class ServerStatus:
    running: bool
    pid: int | None
    pid_file: Path
    base_url: str


class ServerProcessManager:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def _pid_file(self, profile: ProfileConfig) -> Path:
        path = Path(profile.runtime.pid_file)
        if not path.is_absolute():
            path = (self.repo_root / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _log_file(self, profile: ProfileConfig) -> Path:
        path = Path(profile.runtime.log_file)
        if not path.is_absolute():
            path = (self.repo_root / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _read_pid_payload(self, profile: ProfileConfig) -> dict | None:
        pid_file = self._pid_file(profile)
        if not pid_file.exists():
            return None
        return json.loads(pid_file.read_text())

    def _write_pid_payload(self, profile: ProfileConfig, pid: int, command: list[str]) -> None:
        pid_file = self._pid_file(profile)
        payload = {
            "pid": pid,
            "profile": profile.name,
            "base_url": base_url(profile),
            "command": command,
        }
        pid_file.write_text(json.dumps(payload, indent=2))

    def _remove_pid_file(self, profile: ProfileConfig) -> None:
        pid_file = self._pid_file(profile)
        if pid_file.exists():
            pid_file.unlink()

    def is_pid_running(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def health_check(self, profile: ProfileConfig, timeout_seconds: int = 5) -> bool:
        url = f"{base_url(profile)}/health"
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                with urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return True
            except URLError:
                time.sleep(0.25)
        return False

    def status(self, profile: ProfileConfig) -> ServerStatus:
        pid_file = self._pid_file(profile)
        payload = self._read_pid_payload(profile)
        if not payload:
            return ServerStatus(False, None, pid_file, base_url(profile))

        pid = int(payload["pid"])
        running = self.is_pid_running(pid) and self.health_check(profile, timeout_seconds=1)
        if not running:
            self._remove_pid_file(profile)
            return ServerStatus(False, None, pid_file, base_url(profile))
        return ServerStatus(True, pid, pid_file, base_url(profile))

    def start(self, profile: ProfileConfig) -> ServerStatus:
        current = self.status(profile)
        if current.running:
            return current

        binary = resolve_binary(profile, self.repo_root)
        if not binary.exists():
            raise ServerProcessError(
                f"llama-server binary not found at {binary}. Build it first in third_party/llama-cpp-turboquant."
            )

        command = build_server_command(profile, self.repo_root)
        log_file = self._log_file(profile)
        with log_file.open("ab") as handle:
            process = subprocess.Popen(
                command,
                cwd=self.repo_root,
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

        self._write_pid_payload(profile, process.pid, command)

        if not self.health_check(profile, timeout_seconds=profile.runtime.startup_timeout_seconds):
            self.stop(profile, missing_ok=True)
            raise ServerProcessError(
                f"Server failed to become healthy within {profile.runtime.startup_timeout_seconds}s. "
                f"See log: {log_file}"
            )

        return self.status(profile)

    def stop(self, profile: ProfileConfig, missing_ok: bool = False) -> None:
        payload = self._read_pid_payload(profile)
        if not payload:
            if missing_ok:
                return
            raise ServerProcessError("No pid file found for the configured server.")

        pid = int(payload["pid"])
        if self.is_pid_running(pid):
            os.killpg(pid, signal.SIGTERM)
            deadline = time.time() + 10
            while time.time() < deadline:
                if not self.is_pid_running(pid):
                    break
                time.sleep(0.2)
            if self.is_pid_running(pid):
                os.killpg(pid, signal.SIGKILL)
        self._remove_pid_file(profile)
