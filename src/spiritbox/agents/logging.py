"""Logging agent that records session activity."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from .analysis import AnalysisReport
from .base import Agent, HealthState
from .heuristic import HeuristicAlert


@dataclass
class LogEvent:
    timestamp: datetime
    source: str
    message: str


class LoggingAgent(Agent):
    agent_id = "logging_agent"
    title = "Session Forensics Logger"

    def __init__(self, log_path: Path) -> None:
        super().__init__()
        self.log_path = log_path
        self.events: List[LogEvent] = []

    def record(self, source: str, message: str) -> None:
        event = LogEvent(timestamp=datetime.utcnow(), source=source, message=message)
        self.events.append(event)
        self.set_state(HealthState.HEALTHY, "Event recorded", count=str(len(self.events)))

    def capture_report(self, report: AnalysisReport, alerts: List[HeuristicAlert]) -> None:
        self.record("analysis_agent", f"SHA256={report.sha256} size={report.file_size} bytes entropy={report.entropy}")
        if alerts:
            for alert in alerts:
                self.record("heuristic_agent", f"{alert.severity.upper()}: {alert.message}")
        else:
            self.record("heuristic_agent", "No alerts raised")

    def export(self) -> Path:
        if not self.events:
            self.set_state(HealthState.WARNING, "No events to export")
        with self.log_path.open("w", encoding="utf-8") as handle:
            for event in self.events:
                timestamp = event.timestamp.isoformat(timespec="seconds") + "Z"
                handle.write(f"[{timestamp}] {event.source}: {event.message}\n")
        self.set_state(HealthState.HEALTHY, "Log exported", path=str(self.log_path))
        return self.log_path

    def reset(self) -> None:
        super().reset()
        self.events.clear()