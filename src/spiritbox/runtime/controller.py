"""SpiritBox runtime controller orchestrating the three container stack."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from ..agents.analysis import AnalysisReport
from ..agents.base import AgentStatus, HealthState
from ..agents.heuristic import HeuristicAlert
from .containers import (
    AnalysisBridgeContainer,
    ContainerState,
    ConsoleContainer,
    ExtractionDetonationContainer,
)


@dataclass
class SpiritBoxConfig:
    """Configuration provided by the CLI container."""

    watch_path: Path
    expected_hash: str
    workspace: Path
    poll_interval: float = 1.0


@dataclass
class SpiritBoxState:
    """Aggregated view of SpiritBox runtime state."""

    containers: Tuple[ContainerState, ...]
    last_report: Optional[AnalysisReport] = None
    last_alerts: Tuple[HeuristicAlert, ...] = tuple()
    ssh_port: Optional[int] = None


class SpiritBoxController:
    """Coordinates container lifecycle according to the project manifest."""

    def __init__(self) -> None:
        self._config: Optional[SpiritBoxConfig] = None
        self._inner: Optional[ExtractionDetonationContainer] = None
        self._middle: Optional[AnalysisBridgeContainer] = None
        self._outer: Optional[ConsoleContainer] = None
        self._report: Optional[AnalysisReport] = None
        self._alerts: Tuple[HeuristicAlert, ...] = tuple()
        self._final_log: Optional[Path] = None

    def configure(self, config: SpiritBoxConfig) -> None:
        self._config = config
        workspace = config.workspace
        workspace.mkdir(parents=True, exist_ok=True)

        inner_workspace = workspace / "container1"
        middle_workspace = workspace / "container2"

        self._inner = ExtractionDetonationContainer(inner_workspace)
        self._inner.build()

        log_path = workspace / "sbox-log.txt"
        self._middle = AnalysisBridgeContainer(middle_workspace, log_path)

        self._outer = ConsoleContainer(workspace)
        self._outer.set_cli_state("Configured; activate to begin monitoring")

        self._middle.arm(
            inner=self._inner,
            watch_path=config.watch_path,
            expected_hash=config.expected_hash,
            poll_interval=config.poll_interval,
            on_complete=self._on_analysis_complete,
        )

        self._report = None
        self._alerts = tuple()
        self._final_log = None

    async def start(self) -> None:
        if not self._middle or not self._outer:
            raise RuntimeError("SpiritBox is not configured")
        await self._middle.start()
        port = self._middle.ssh_port
        detail = "Ready for extraction"
        if port:
            detail += f" (SSH port {port})"
        self._outer.set_cli_state(detail)

    async def stop(self) -> None:
        if not self._middle or not self._outer:
            return
        await self._middle.stop()
        self._outer.set_cli_state("Monitoring paused")

    def export_log(self) -> Optional[Path]:
        if not self._middle:
            return None
        path = self._middle.export_log()
        self._final_log = path
        return path

    def teardown(self) -> Optional[Path]:
        if self._middle:
            self._middle.teardown()
        if self._inner:
            self._inner.teardown()
        preserved: Optional[Path] = None
        if self._outer:
            preserved = self._outer.destroy()
        if preserved:
            self._final_log = preserved
        return preserved

    def final_log(self) -> Optional[Path]:
        return self._final_log or (self._outer.preserved_log if self._outer else None)

    def state(self) -> SpiritBoxState:
        containers = (
            self._outer.status() if self._outer else self._placeholder_console(),
            self._middle.status() if self._middle else self._placeholder_middle(),
            self._inner.status() if self._inner else self._placeholder_inner(),
        )
        ssh_port = self._middle.ssh_port if self._middle else None
        return SpiritBoxState(
            containers=containers,
            last_report=self._report,
            last_alerts=self._alerts,
            ssh_port=ssh_port,
        )

    def _on_analysis_complete(self, report: AnalysisReport, alerts: Tuple[HeuristicAlert, ...]) -> None:
        self._report = report
        self._alerts = alerts
        if self._outer:
            self._outer.set_cli_state("Analysis complete; ready for review")

    @staticmethod
    def _placeholder_console() -> ContainerState:
        agents = (
            AgentStatus(
                agent_id="cli_agent",
                title="SpiritBox™ Console Shell",
                state=HealthState.WARNING,
                detail="Not configured",
            ),
            AgentStatus(
                agent_id="cleanup_agent",
                title="Container Teardown & Ephemeral Self-Destruct",
                state=HealthState.WARNING,
                detail="Not configured",
            ),
        )
        return ContainerState(
            name=ConsoleContainer.name,
            description=ConsoleContainer.description,
            detail="Not configured",
            agents=agents,
        )

    @staticmethod
    def _placeholder_middle() -> ContainerState:
        agents = (
            AgentStatus(
                agent_id="bridge_agent",
                title="Container 1 to container 2 SSH bridge",
                state=HealthState.WARNING,
                detail="Not configured",
            ),
            AgentStatus(
                agent_id="analysis_agent",
                title="Analyst Shell & Static Analysis Tools",
                state=HealthState.WARNING,
                detail="Not configured",
            ),
            AgentStatus(
                agent_id="heuristic_agent",
                title="Runtime Behavior & Threat Monitoring",
                state=HealthState.WARNING,
                detail="Not configured",
            ),
            AgentStatus(
                agent_id="logging_agent",
                title="Session Forensics Logger",
                state=HealthState.WARNING,
                detail="Not configured",
            ),
        )
        return ContainerState(
            name=AnalysisBridgeContainer.name,
            description=AnalysisBridgeContainer.description,
            detail="Not configured",
            agents=agents,
        )

    @staticmethod
    def _placeholder_inner() -> ContainerState:
        agents = (
            AgentStatus(
                agent_id="containment_agent",
                title="Capture & Isolation Agent",
                state=HealthState.WARNING,
                detail="Not configured",
            ),
        )
        return ContainerState(
            name=ExtractionDetonationContainer.name,
            description=ExtractionDetonationContainer.description,
            detail="Not configured",
            agents=agents,
        )
