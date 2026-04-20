"""CLI compatibility layer — makes gate-server discoverable by gate-cli.

When gate-cli is installed alongside gate-server, this module provides
server management commands accessible via the gate CLI:

    gate server start    # start gate-server in background
    gate server stop     # stop gate-server
    gate server logs     # tail server logs

NOT WIRED YET — An Improver should:
  1. Import this as a Click group in gate-cli's server command
  2. Use subprocess or uvicorn programmatic API for start/stop
  3. Add PID file tracking for process management
  4. Add log file configuration

Seeded by Creator 2 (gate-cli), Loop 5.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path


PID_FILE = Path("~/.gate/server.pid").expanduser()
LOG_FILE = Path("~/.gate/server.log").expanduser()


def ensure_gate_dir():
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)


def start_server(host: str = "0.0.0.0", port: int = 8900) -> int | None:
    """Start gate-server as a background process.

    Returns PID on success, None on failure.
    """
    ensure_gate_dir()
    # TODO: implement with uvicorn programmatic API or subprocess
    # proc = subprocess.Popen(
    #     [sys.executable, "-m", "gate_server",
    #      "--host", host, "--port", str(port)],
    #     stdout=open(LOG_FILE, "a"),
    #     stderr=subprocess.STDOUT,
    #     start_new_session=True,
    # )
    # PID_FILE.write_text(str(proc.pid))
    # return proc.pid
    return None


def stop_server() -> bool:
    """Stop the background gate-server process."""
    # TODO: read PID from PID_FILE, send SIGTERM
    return False


def server_status() -> dict:
    """Check if gate-server is running."""
    return {
        "running": False,
        "pid": None,
        "pid_file": str(PID_FILE),
    }
