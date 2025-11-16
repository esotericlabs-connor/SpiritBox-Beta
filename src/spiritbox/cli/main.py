"""Command line interface for SpiritBox."""
from __future__ import annotations

import argparse
import asyncio
import os
import shlex
import subprocess
import threading
import sys
from cmd import Cmd
from pathlib import Path
from typing import Optional

from ..runtime.controller import SpiritBoxConfig, SpiritBoxController, SpiritBoxState
from .banner import load_banner


class SpiritBoxShell(Cmd):
    intro = ""
    
    prompt = "sbox> "

    def __init__(self, banner: str) -> None:
        super().__init__()
        self.controller = SpiritBoxController()
        self.loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._loop_thread.start()
        self._config: Optional[SpiritBoxConfig] = None
        self._monitoring_active = False
        self._shutdown = False
        self._banner = banner
        self._status_line = "Preparing SpiritBox... Ready for instruction."
        self._footer_line = "SpiritBox CLI - type 'help' to list commands."
        self._last_command = ""
        self._render_shell_header()

    # ------------------------------------------------------------------
    # CLI command implementations
    # ------------------------------------------------------------------

    def do_banner(self, arg: str) -> None:
        """Display the SpiritBox ASCII banner."""

        print(self._banner)

    def do_status(self, arg: str) -> None:
        """Show current agent health and last analysis report."""

        self._update_status()
        self._refresh_after_status_change()
        state = self.controller.state()
        self._render_container_status(state)
        self._render_agent_health(state)

    def do_set_conjure(self, arg: str) -> None:
        """Configure SpiritBox watch path and hash.

        Usage: set_conjure <folder> <sha256>
        """

        try:
            parts = shlex.split(arg, posix=os.name != "nt")
        except ValueError:
            print("Usage: set_conjure <folder> <sha256>")
            return

        if len(parts) < 2:
            print("Usage: set_conjure <folder> <sha256>")
            return

        folder, expected_hash = parts[0], parts[1]

        path = Path(folder).expanduser()
        try:
            path = path.resolve()
        except FileNotFoundError:
            path = path.resolve(strict=False)

        if len(expected_hash) != 64:
            print("[!] Expected hash must be a SHA-256 string (64 hex characters).")
            return
        try:
            config = SpiritBoxConfig(
                watch_path=path,
                expected_hash=expected_hash.lower(),
                workspace=Path.cwd() / ".spiritbox",
            )
            self.controller.configure(config)
            self._config = config
            self._update_status()
            self._refresh_after_status_change()
            print("[+] SpiritBox configured. Use 'activate' to begin monitoring.")
        except Exception as exc:
            print(f"[!] Configuration failed: {exc}")

    def do_activate(self, arg: str) -> None:
        """Begin monitoring for the configured file."""

        if not self._config:
            print("[!] SpiritBox is not configured. Use 'set_conjure' first.")
            return

        if self._monitoring_active:
            print("[!] Monitoring already active.")
            return

        future = asyncio.run_coroutine_threadsafe(self.controller.start(), self.loop)
        future.result()
        self._monitoring_active = True
        self._update_status()
        self._refresh_after_status_change()
        print("[+] Activating SpiritBox monitoring...")
        state = self.controller.state()
        if state.ssh_port:
            print(f"[+] Bridge online via SSH port {state.ssh_port}. Awaiting file match.")
        else:
            print("[+] Monitoring active. Awaiting file match.")       

    def do_deactivate(self, arg: str) -> None:
        """Stop monitoring for files."""

        if not self._monitoring_active:
            print("[!] Monitoring is not active.")
            return

        asyncio.run_coroutine_threadsafe(self.controller.stop(), self.loop).result()
        self._monitoring_active = False
        print("[+] Monitoring stopped.")

    def do_export(self, arg: str) -> None:
        """Export the session log (sbox-log.txt)."""

        path = self.controller.export_log()
        if path:
            print(f"[+] Log exported to {path}")
        else:
            print("[!] No log available.")

    def do_self_destruct(self, arg: str) -> bool:
        """Destroy the SpiritBox workspace and exit."""

        self._perform_shutdown()
        return True

    def do_exit(self, arg: str) -> bool:
        """Exit SpiritBox, exporting logs first."""

        self.do_export("")
        self._perform_shutdown()
        print("[+] SpiritBox shutdown complete. Goodbye.")
        return True

    def do_EOF(self, arg: str) -> bool:  # pragma: no cover - interactive convenience
        print()
        return self.do_exit(arg)
    
    def do_clear(self, arg: str) -> None:
        """Clear the console while keeping the SpiritBox banner visible."""

        self._refresh_after_status_change()

    # ------------------------------------------------------------------
    # cmd.Cmd lifecycle hooks
    # ------------------------------------------------------------------

    def precmd(self, line: str) -> str:
        cleaned = super().precmd(line)
        self._last_command = cleaned
        self._update_status()
        self._render_shell_header()
        if cleaned.strip():
            print(f"{self.prompt}{cleaned}")
        return cleaned

    def emptyline(self) -> None:
        """Prevent repeating the previous command on empty input."""

        return


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _perform_shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        if self._monitoring_active:
            asyncio.run_coroutine_threadsafe(self.controller.stop(), self.loop).result()
            self._monitoring_active = False
        preserved = self.controller.teardown()
        final_log = preserved or self.controller.final_log()
        if final_log:
            print(f"[+] Final log preserved at {final_log}")
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._loop_thread.join()
        self.loop.close()

    def _render_shell_header(self) -> None:
        if sys.stdout.isatty():
            os.system("cls" if os.name == "nt" else "clear")
        print(self._banner)
        print()
        print(self._status_line)
        if self._footer_line:
            print(self._footer_line)
        print()

    def _update_status(self) -> None:
        state = self.controller.state()
        if state.containers:
            detail = state.containers[0].detail
            if detail and detail.lower() != "not configured":
                self._status_line = detail

    def _refresh_after_status_change(self) -> None:
        self._render_shell_header()
        if self._last_command.strip():
            print(f"{self.prompt}{self._last_command}")


    @staticmethod
    def _render_container_status(state: SpiritBoxState) -> None:
        print("\nContainer Stack:")
        for container in state.containers:
            detail = container.detail or "Idle"
            print(f"- {container.name}: {detail}")
            print(f"    {container.description}")
            for agent in container.agents:
                agent_detail = f" - {agent.detail}" if agent.detail else ""
                print(f"    [{agent.state}] {agent.title}{agent_detail}")

        if state.ssh_port:
            print(f"\nSSH Bridge Port: {state.ssh_port}")

    @staticmethod
    def _render_agent_health(state: SpiritBoxState) -> None:
        print("\nAgent Health States:")
        for status in (
            state.monitoring,
            state.containment,
            state.analysis,
            state.heuristic,
            state.logging,
            state.cleanup,
        ):
            detail = f" - {status.detail}" if status.detail else ""
            print(f"  [{status.state}] {status.title}{detail}")

        if state.last_report:
            report = state.last_report
            print("\nLast Analysis Report:")
            print(f"  File: {report.file_path}")
            print(f"  Size: {report.file_size} bytes")
            print(f"  SHA256: {report.sha256}")
            print(f"  Entropy: {report.entropy}")
            print(f"  ClamAV: {report.clamav_scan}")
            print("  YARA Matches: " + (", ".join(report.yara_matches) or "None"))

        if state.last_alerts:
            print("\nHeuristic Alerts:")
            for alert in state.last_alerts:
                print(f"  - ({alert.severity}) {alert.message}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="SpiritBox containment console")
    parser.add_argument("--banner", type=Path, default=None, help="Optional path to custom banner art")
    parser.add_argument(
        "--no-window",
        action="store_true",
        help="Run inside the current console instead of launching a dedicated window.",
    )
    args = parser.parse_args(argv)

    if _maybe_launch_dedicated_window(args):
        return 0
    try:
        shell.cmdloop()
    except KeyboardInterrupt:  # pragma: no cover - interactive convenience
        shell.do_exit("")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry
    raise SystemExit(main())


def _maybe_launch_dedicated_window(args: argparse.Namespace) -> bool:
    """Launch SpiritBox in its own console window when supported."""

    if args.no_window or os.environ.get("SPIRITBOX_CHILD"):
        return False

    if os.name != "nt":
        return False

    creation_flag = getattr(subprocess, "CREATE_NEW_CONSOLE", None)
    if creation_flag is None:
        return False

    command = [sys.executable, "-m", "spiritbox"]
    if args.banner:
        command.extend(["--banner", str(Path(args.banner))])
    command.append("--no-window")

    env = os.environ.copy()
    env["SPIRITBOX_CHILD"] = "1"

    try:
        subprocess.Popen(command, creationflags=creation_flag, env=env)
    except OSError:
        return False

    return True