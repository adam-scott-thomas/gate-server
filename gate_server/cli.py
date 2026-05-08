"""gate-server CLI — quick ops tool for testing and administration.

Usage:
    python -m gate_server.cli health
    python -m gate_server.cli register --file tools.json
    python -m gate_server.cli filter --mode 0.7
    python -m gate_server.cli history

NOT WIRED YET — An Improver should:
  1. Add `click` or `typer` to pyproject.toml
  2. Implement the HTTP calls using httpx
  3. Add a [project.scripts] entry: gate-ctl = "gate_server.cli:main"

Seeded by Creator 2 (gate-server), Loop 5.
"""
from __future__ import annotations

import argparse
import json
import sys


# Placeholder base URL — should come from env or --url flag
DEFAULT_URL = "http://localhost:8900/api/v1"


def cmd_health(args):
    """GET /health — check if gate-server is running."""
    # TODO: httpx.get(f"{args.url}/health")
    print(f"[stub] Would check health at {args.url}/health")


def cmd_register(args):
    """POST /tools/register — register tools from a JSON file."""
    # TODO: load args.file, httpx.post(f"{args.url}/tools/register", json=payload)
    print(f"[stub] Would register tools from {args.file} at {args.url}/tools/register")


def cmd_filter(args):
    """POST /tools/filter — filter tools at a given mode signal."""
    # TODO: httpx.post(f"{args.url}/tools/filter", json={"mode": args.mode})
    print(f"[stub] Would filter at mode={args.mode} via {args.url}/tools/filter")


def cmd_history(args):
    """GET /mode/history — show recent mode signal history."""
    # TODO: httpx.get(f"{args.url}/mode/history")
    print(f"[stub] Would fetch mode history from {args.url}/mode/history")


def cmd_export(args):
    """POST /tools/openai — export OpenAI-compatible tool list."""
    # TODO: httpx.post(f"{args.url}/tools/openai", json={"mode": args.mode})
    print(f"[stub] Would export OpenAI tools at mode={args.mode}")


def cmd_envelope(args):
    """POST /envelope/build — build authorization envelope for a tool."""
    # TODO: httpx.post(f"{args.url}/envelope/build", json={...})
    print(f"[stub] Would build envelope for tool={args.tool} at mode={args.mode}")


def main():
    parser = argparse.ArgumentParser(
        prog="gate-ctl",
        description="CLI for Gatekeeper Server operations",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="gate-server base URL")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="Check server health")

    p_reg = sub.add_parser("register", help="Register tools from JSON file")
    p_reg.add_argument("--file", "-f", required=True, help="Path to tools JSON")

    p_filt = sub.add_parser("filter", help="Filter tools at mode signal")
    p_filt.add_argument("--mode", "-m", type=float, required=True)

    sub.add_parser("history", help="Show mode signal history")

    p_exp = sub.add_parser("export", help="Export OpenAI-compatible tool list")
    p_exp.add_argument("--mode", "-m", type=float, default=0.0)

    p_env = sub.add_parser("envelope", help="Build authorization envelope")
    p_env.add_argument("--tool", "-t", required=True, help="Tool name")
    p_env.add_argument("--mode", "-m", type=float, default=0.0)

    args = parser.parse_args()
    dispatch = {
        "health": cmd_health,
        "register": cmd_register,
        "filter": cmd_filter,
        "history": cmd_history,
        "export": cmd_export,
        "envelope": cmd_envelope,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
