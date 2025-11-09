"""Bridge agent responsible for linking containers 1 and 3 via SSH."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Awaitable, Callable, Optional

from .base import AgentConfigError, HealthState
from .monitoring import MonitorConfig, MonitoringAgent


Callback = Callable[[Path], Awaitable[None]]


class BridgeAgent(MonitoringAgent):
    """Specialised monitoring agent that brokers the SSH bridge."""

    agent_id = "bridge_agent"
    title = "Container 1 to container 2 SSH bridge"

    def __init__(self) -> None:
        super().__init__()
        self._ssh_port: Optional[int] = None

    def configure(self, config: MonitorConfig, callback: Callback) -> None:  # type: ignore[override]
        self._ssh_port = self._allocate_port()
        super().configure(config, callback)
        self.set_state(HealthState.HEALTHY, f"Bridge armed on port {self._ssh_port}")

    async def start(self) -> None:  # type: ignore[override]
        if self._ssh_port is None:
            raise AgentConfigError("SSH bridge not configured")
        await super().start()
        self.set_state(HealthState.HEALTHY, f"Bridge active on port {self._ssh_port}")

    async def stop(self) -> None:  # type: ignore[override]
        await super().stop()
        if self._ssh_port is not None:
            self.set_state(HealthState.HEALTHY, "Bridge offline")

    @property
    def ssh_port(self) -> Optional[int]:
        return self._ssh_port

    @staticmethod
    def _allocate_port() -> int:
        while True:
            candidate = random.randint(10000, 65000)
            if candidate != 22:
                return candidate
            