"""Heuristic agent responsible for runtime threat monitoring."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .analysis import AnalysisReport
from .base import Agent, HealthState


@dataclass(frozen=True)
class HeuristicAlert:
    """Alert raised by the heuristic agent when suspicious behaviour is detected."""

    severity: str
    message: str


class HeuristicAgent(Agent):
    """Runtime behaviour and threat monitoring for the analysis container."""

    agent_id = "heuristic_agent"
    title = "Runtime Behavior & Threat Monitoring"

    def __init__(self) -> None:
        super().__init__()

    def evaluate(self, report: AnalysisReport) -> List[HeuristicAlert]:
        """Generate heuristic alerts based on an analysis report."""

        alerts: List[HeuristicAlert] = []

        alerts.extend(self._entropy_checks(report))
        alerts.extend(self._size_checks(report))
        alerts.extend(self._signature_checks(report))

        if alerts:
            self.set_state(
                HealthState.ALERT,
                "; ".join(alert.message for alert in alerts),
                file=report.file_path.name,
            )
        else:
            self.set_state(HealthState.HEALTHY, "No anomalies detected", file=report.file_path.name)

        return alerts

    @staticmethod
    def _entropy_checks(report: AnalysisReport) -> Iterable[HeuristicAlert]:
        if report.entropy >= 7.5:
            yield HeuristicAlert(
                severity="alert",
                message="High entropy suggests packed or encrypted payload",
            )
        elif report.entropy <= 1.0 and report.file_size > 0:
            yield HeuristicAlert(
                severity="warning",
                message="Extremely low entropy detected",
            )

    @staticmethod
    def _size_checks(report: AnalysisReport) -> Iterable[HeuristicAlert]:
        if report.file_size == 0:
            yield HeuristicAlert(severity="warning", message="Captured file is empty")
        elif report.file_size > 50 * 1024 * 1024:  # 50 MiB heuristic limit
            yield HeuristicAlert(severity="warning", message="Large payload captured (>50 MiB)")

    @staticmethod
    def _signature_checks(report: AnalysisReport) -> Iterable[HeuristicAlert]:
        suspicious_tokens: Sequence[str] = (
            "mimikatz",
            "ransom",
            "payload",
            "shellcode",
        )
        lower_name = report.file_path.name.lower()
        for token in suspicious_tokens:
            if token in lower_name:
                yield HeuristicAlert(
                    severity="alert",
                    message=f"Filename indicator detected: '{token}'",
                )
