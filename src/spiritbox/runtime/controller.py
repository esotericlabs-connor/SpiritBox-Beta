"""SpiritBox runtime controller orchestrating agents."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..agents.analysis import AnalysisAgent, AnalysisReport
from ..agents.cleanup import CleanupAgent
from ..agents.containment import ContainmentAgent
from ..agents.heuristic import HeuristicAgent, HeuristicAlert
from ..agents.logging import LoggingAgent
from ..agents.monitoring import MonitorConfig, MonitoringAgent
from ..agents.base import AgentStatus


@dataclass
class SpiritBoxConfig:
    watch_path: Path
    expected_hash: str
    workspace: Path
    poll_interval: float = 1.0


@dataclass
class SpiritBoxState:
    monitoring: AgentStatus
    containment: AgentStatus
    analysis: AgentStatus
    heuristic: AgentStatus
    logging: AgentStatus
    cleanup: AgentStatus
    last_report: Optional[AnalysisReport] = None
    last_alerts: tuple[HeuristicAlert, ...] = tuple()


class SpiritBoxController:
    """Coordinates all agents according to the project manifest."""

    def __init__(self) -> None:
        self._monitoring = MonitoringAgent()
        self._analysis = AnalysisAgent()
        self._heuristic = HeuristicAgent()
        self._containment: Optional[ContainmentAgent] = None
        self._logging: Optional[LoggingAgent] = None
        self._cleanup: Optional[CleanupAgent] = None
        self._config: Optional[SpiritBoxConfig] = None
        self._workspace: Optional[Path] = None
        self._report: Optional[AnalysisReport] = None
        self._alerts: tuple[HeuristicAlert, ...] = tuple()
        self._final_log: Optional[Path] = None

    def configure(self, config: SpiritBoxConfig) -> None:
        self._config = config
        self._workspace = config.workspace
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._containment = ContainmentAgent(config.workspace)
        self._containment.prepare()
        log_path = config.workspace / "sbox-log.txt"
        self._logging = LoggingAgent(log_path)
        self._cleanup = CleanupAgent(config.workspace)
        self._final_log = None

        monitor_config = MonitorConfig(
            watch_path=config.watch_path,
            expected_hash=config.expected_hash,
            poll_interval=config.poll_interval,
        )
        self._monitoring.configure(monitor_config, self._on_capture)
        self._logging.record("cli_agent", "Monitoring configured")

    async def start(self) -> None:
        await self._monitoring.start()

    async def stop(self) -> None:
        await self._monitoring.stop()

    async def _on_capture(self, file_path: Path) -> None:
        assert self._containment and self._logging
        isolated = self._containment.isolate(file_path)
        self._logging.record("containment_agent", f"File isolated at {isolated}")

        report = self._analysis.analyze(isolated)
        alerts = self._heuristic.evaluate(report)
        self._logging.capture_report(report, alerts)

        self._report = report
        self._alerts = tuple(alerts)
        self._logging.record("analysis_agent", "Analysis complete; ready for review")

    def export_log(self) -> Optional[Path]:
        if not self._logging:
            return None
        path = self._logging.export()
        self._final_log = path
        return path

    def teardown(self) -> Optional[Path]:
        if self._containment:
            self._containment.teardown()
        if self._cleanup:
            preserved = self._cleanup.destroy()
            if preserved:
                self._final_log = preserved
            return preserved
        return None

    def final_log(self) -> Optional[Path]:
        return self._final_log

    def state(self) -> SpiritBoxState:
        return SpiritBoxState(
            monitoring=self._monitoring.info(),
            containment=self._containment.info() if self._containment else AgentStatus("containment", "Containment"),
            analysis=self._analysis.info(),
            heuristic=self._heuristic.info(),
            logging=self._logging.info() if self._logging else AgentStatus("logging", "Logging"),
            cleanup=self._cleanup.info() if self._cleanup else AgentStatus("cleanup", "Cleanup"),
            last_report=self._report,
            last_alerts=self._alerts,
        )