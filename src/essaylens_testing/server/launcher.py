from __future__ import annotations

from pathlib import Path

from essaylens_testing.config.loader import ConfigLoader
from essaylens_testing.server.process_manager import ServerProcessManager, ServerStatus


class ServerLauncher:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.loader = ConfigLoader(repo_root)
        self.manager = ServerProcessManager(repo_root)

    def start(self, profile_name: str) -> ServerStatus:
        profile = self.loader.load_profile(profile_name)
        return self.manager.start(profile)

    def stop(self, profile_name: str) -> None:
        profile = self.loader.load_profile(profile_name)
        self.manager.stop(profile)

    def status(self, profile_name: str) -> ServerStatus:
        profile = self.loader.load_profile(profile_name)
        return self.manager.status(profile)
