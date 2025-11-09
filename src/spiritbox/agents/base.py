"""Core agent abstractions for SpiritBox."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict


class HealthState(str, Enum):
    """Standard health states used by all SpiritBox agents."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    WARNING = "warning"
    ALERT = "alert"
    FAULT = "fault"


@dataclass
class AgentStatus:
    """Snapshot of an agent's current status."""

    agent_id: str
    title: str
    state: HealthState = HealthState.HEALTHY
    detail: str = ""
    data: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def transition(self, state: HealthState, detail: str = "", **data: str) -> None:
        """Update the status to a new state with optional context."""

        self.state = state
        self.detail = detail
        if data:
            self.data.update(data)
        self.timestamp = datetime.utcnow()


class Agent:
    """Base class that all SpiritBox agents extend."""

    agent_id: str = "agent"
    title: str = "SpiritBox Agent"

    def __init__(self) -> None:
        self.status = AgentStatus(agent_id=self.agent_id, title=self.title)

    def set_state(self, state: HealthState, detail: str = "", **data: str) -> None:
        self.status.transition(state=state, detail=detail, **data)

    def info(self) -> AgentStatus:
        return self.status

    def reset(self) -> None:
        self.status = AgentStatus(agent_id=self.agent_id, title=self.title)


class SpiritBoxError(Exception):
    """Base error raised within the SpiritBox runtime."""


class AgentConfigError(SpiritBoxError):
    """Raised when an agent configuration is invalid."""


class AgentRuntimeError(SpiritBoxError):
    """Raised when an agent encounters a runtime fault."""