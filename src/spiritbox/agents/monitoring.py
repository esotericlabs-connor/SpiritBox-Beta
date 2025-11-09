"""Monitoring agent responsible for file watch and trigger."""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Optional

from .base import Agent, AgentConfigError, AgentRuntimeError, HealthState


@dataclass
class MonitorConfig:
    watch_path: Path
    expected_hash: str
    poll_interval: float = 1.0

    def __post_init__(self) -> None:
        if not self.watch_path.exists():
            raise AgentConfigError(f"Watch path does not exist: {self.watch_path}")
        if not self.watch_path.is_dir():
            raise AgentConfigError("Watch path must be a directory")
        if len(self.expected_hash) != 64:
            raise AgentConfigError("Expected hash must be a SHA-256 string")


class MonitoringAgent(Agent):
    agent_id = "monitoring_agent"
    title = "File Monitoring & Match Trigger"

    def __init__(self) -> None:
        super().__init__()
        self._config: Optional[MonitorConfig] = None
        self._callback: Optional[Callable[[Path], Awaitable[None]]] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    def configure(self, config: MonitorConfig, callback: Callable[[Path], Awaitable[None]]) -> None:
        self._config = config
        self._callback = callback
        self.set_state(HealthState.HEALTHY, "Monitoring configured")

    async def start(self) -> None:
        if not self._config or not self._callback:
            raise AgentConfigError("Monitoring agent is not configured")

        if self._task and not self._task.done():
            raise AgentRuntimeError("Monitoring already running")

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        self.set_state(HealthState.HEALTHY, "Monitoring active")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._stop_event.set()
            await self._task
        self._task = None
        self.set_state(HealthState.HEALTHY, "Monitoring stopped")

    async def _run(self) -> None:
        assert self._config
        assert self._callback
        seen: set[str] = set()
        try:
            while not self._stop_event.is_set():
                for entry in sorted(self._config.watch_path.iterdir()):
                    if entry.is_file() and entry.name not in seen:
                        file_hash = self._hash_file(entry)
                        if file_hash == self._config.expected_hash:
                            self.set_state(HealthState.HEALTHY, f"Match located: {entry.name}")
                            await self._callback(entry)
                            seen.add(entry.name)
                        else:
                            seen.add(entry.name)
                    await asyncio.sleep(0)
                await asyncio.sleep(self._config.poll_interval)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.set_state(HealthState.FAULT, f"Monitoring failure: {exc}")
            raise

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()