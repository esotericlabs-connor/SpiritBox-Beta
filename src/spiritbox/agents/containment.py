"""Containment agent responsible for isolating captured files."""
from __future__ import annotations

import shutil
import stat
from pathlib import Path
from typing import Optional

from .base import Agent, AgentRuntimeError, HealthState


class ContainmentAgent(Agent):
    agent_id = "containment_agent"
    title = "Capture & Isolation Agent"

    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.capture_dir: Optional[Path] = None

    def prepare(self) -> Path:
        self.capture_dir = self.base_dir / "capture"
        if self.capture_dir.exists():
            shutil.rmtree(self.capture_dir)
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.set_state(HealthState.HEALTHY, "Capture directory prepared")
        return self.capture_dir

    def isolate(self, source: Path) -> Path:
        if not self.capture_dir:
            raise AgentRuntimeError("Capture directory not prepared")
        if not source.exists():
            raise AgentRuntimeError(f"Source file missing: {source}")

        destination = self.capture_dir / source.name
        shutil.copy2(source, destination)
        destination.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.set_state(HealthState.HEALTHY, "File isolated", file=destination.name)
        return destination

    def teardown(self) -> None:
        if self.capture_dir and self.capture_dir.exists():
            shutil.rmtree(self.capture_dir)
        self.capture_dir = None
        self.set_state(HealthState.HEALTHY, "Containment cleared")