"""Container stack orchestration for SpiritBox."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

from ..agents.analysis import AnalysisAgent, AnalysisReport
from ..agents.bridge import BridgeAgent
from ..agents.cleanup import CleanupAgent
from ..agents.containment import ContainmentAgent
from ..agents.heuristic import HeuristicAgent, HeuristicAlert
from ..agents.logging import LoggingAgent
from ..agents.monitoring import MonitorConfig
from ..agents.base import AgentStatus, HealthState


@dataclass(frozen=True)
class ContainerState:
    """Snapshot of a container, including its constituent agents."""

    name: str
    description: str
    detail: str
    agents: Tuple[AgentStatus, ...]


class ContainerBase:
    """Base helper encapsulating common container behaviour."""

    name: str = "Container"
    description: str = "SpiritBox container"

    def __init__(self) -> None:
        self._detail: str = ""

    def status(self) -> ContainerState:
        return ContainerState(
            name=self.name,
            description=self.description,
            detail=self._detail,
            agents=self._agents(),
        )

    def set_detail(self, detail: str) -> None:
        self._detail = detail

    def _agents(self) -> Tuple[AgentStatus, ...]:
        raise NotImplementedError


class ExtractionDetonationContainer(ContainerBase):
    """Inner extraction and detonation container (Container 1)."""

    name = "Extraction and Detonation Container"
    description = (
        "Built under C++ for speed and hardware-level control. Handles file "
        "capture, detonation, and isolation at high speed."
    )

    def __init__(self, workspace: Path) -> None:
        super().__init__()
        self.workspace = workspace
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.containment = ContainmentAgent(self.workspace)
        self.capture_dir: Optional[Path] = None

    def build(self) -> Path:
        self.capture_dir = self.containment.prepare()
        self.set_detail("Containment prepared and standing by")
        return self.capture_dir

    def isolate(self, source: Path) -> Path:
        isolated = self.containment.isolate(source)
        self.set_detail(f"File isolated for analysis: {isolated.name}")
        return isolated

    def teardown(self) -> None:
        self.containment.teardown()
        self.set_detail("Containment cleared")

    def _agents(self) -> Tuple[AgentStatus, ...]:
        return (self.containment.info(),)


class AnalysisBridgeContainer(ContainerBase):
    """Middle bridge and analysis container (Container 2)."""

    name = "Bridge and Analysis Container"
    description = (
        "Builds around the detonation container, provides forensic tooling, "
        "and brokers the SSH bridge between inner and outer containers."
    )

    def __init__(self, workspace: Path, log_path: Path) -> None:
        super().__init__()
        self.workspace = workspace
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.analysis = AnalysisAgent()
        self.heuristic = HeuristicAgent()
        self.logging = LoggingAgent(log_path)
        self.bridge = BridgeAgent()
        self._inner: Optional[ExtractionDetonationContainer] = None
        self._on_complete: Optional[Callable[[AnalysisReport, Tuple[HeuristicAlert, ...]], None]] = None

    def arm(
        self,
        *,
        inner: ExtractionDetonationContainer,
        watch_path: Path,
        expected_hash: str,
        poll_interval: float,
        on_complete: Callable[[AnalysisReport, Tuple[HeuristicAlert, ...]], None],
    ) -> None:
        self._inner = inner
        self._on_complete = on_complete

        config = MonitorConfig(
            watch_path=watch_path,
            expected_hash=expected_hash,
            poll_interval=poll_interval,
        )

        async def _handle_match(path: Path) -> None:
            assert self._inner is not None
            try:
                self.set_detail(f"File captured: {path.name}")
                self.logging.record("bridge_agent", f"Match captured for {path.name}")
                isolated = self._inner.isolate(path)
                report = self.analysis.analyze(isolated)
                alerts = tuple(self.heuristic.evaluate(report))
                self.logging.capture_report(report, list(alerts))
                if self._on_complete:
                    self._on_complete(report, alerts)
                self.set_detail(f"Analysis complete for {path.name}")
            except Exception as exc:  # pragma: no cover - defensive guard
                self.logging.record("analysis_agent", f"Fault during analysis: {exc}")
                self.set_detail(f"Analysis fault: {exc}")
                raise

        self.bridge.configure(config, _handle_match)
        port = self.bridge.ssh_port
        self.set_detail(f"Bridge armed on port {port}")

    async def start(self) -> None:
        await self.bridge.start()
        port = self.bridge.ssh_port
        self.set_detail(f"Awaiting file match via SSH tunnel {port}")

    async def stop(self) -> None:
        await self.bridge.stop()
        self.set_detail("Bridge offline")

    def export_log(self) -> Path:
        return self.logging.export()

    def teardown(self) -> None:
        self.set_detail("Bridge dismantled")
        self.bridge.reset()

    @property
    def ssh_port(self) -> Optional[int]:
        return self.bridge.ssh_port

    def _agents(self) -> Tuple[AgentStatus, ...]:
        return (
            self.bridge.info(),
            self.analysis.info(),
            self.heuristic.info(),
            self.logging.info(),
        )


class ConsoleContainer(ContainerBase):
    """Outer CLI and orchestration container (Container 3)."""

    name = "Console and Configuration Container"
    description = (
        "Hosts the SpiritBox CLI, handles configuration, lifecycle orchestration, "
        "and triggers the self-destruct sequence when the session ends."
    )

    def __init__(self, workspace: Path) -> None:
        super().__init__()
        self.workspace = workspace
        self.cleanup = CleanupAgent(workspace)
        self.cli_status = AgentStatus(agent_id="cli_agent", title="SpiritBox™ Console Shell")
        self.cli_status.transition(HealthState.HEALTHY, "Initialized")
        self._final_log: Optional[Path] = None
        self.set_detail("Initialized")

    def set_cli_state(self, detail: str, state: HealthState = HealthState.HEALTHY) -> None:
        self.cli_status.transition(state, detail)
        self.set_detail(detail)

    def destroy(self) -> Optional[Path]:
        preserved = self.cleanup.destroy()
        if preserved:
            self._final_log = preserved
            self.set_detail(f"Self-destruct complete; log preserved at {preserved}")
        else:
            self.set_detail("Self-destruct complete; no log preserved")
        return preserved

    @property
    def preserved_log(self) -> Optional[Path]:
        return self._final_log or self.cleanup.preserved_log

    def _agents(self) -> Tuple[AgentStatus, ...]:
        return (
            self.cli_status,
            self.cleanup.info(),
        )
