"""Cleanup agent responsible for teardown operations."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from .base import Agent, HealthState


class CleanupAgent(Agent):
    agent_id = "cleanup_agent"
    title = "Container Teardown & Ephemeral Self-Destruct"

    def __init__(self, workspace: Path, log_name: str = "sbox-log.txt") -> None:
        super().__init__()
        self.workspace = workspace
        self.log_name = log_name
        self._preserved_log: Optional[Path] = None

    def destroy(self) -> Optional[Path]:
        log_path = self.workspace / self.log_name
        saved_log: Optional[Path] = None
        if log_path.exists():
            saved_log = self.workspace.parent / self.log_name
            shutil.move(str(log_path), saved_log)
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        self._preserved_log = saved_log
        detail = f"Log preserved at {saved_log}" if saved_log else "Workspace destroyed"
        self.set_state(HealthState.HEALTHY, detail)
        return saved_log

    @property
    def preserved_log(self) -> Optional[Path]:
        return self._preserved_log