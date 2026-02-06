#!/usr/bin/env python3
"""Fail CI if Alembic autogenerate produces changes.

Runs alembic autogenerate against the configured DB and checks for operations
in the upgrade/downgrade blocks.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "mcp-server"


def _run() -> str:
    env = os.environ.copy()
    cmd = [
        "alembic",
        "revision",
        "--autogenerate",
        "-m",
        "ci-check",
        "--head",
        "head",
        "--stdout",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(MCP_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        sys.exit(proc.returncode)
    return proc.stdout


def _section_ops(text: str) -> bool:
    return bool(re.search(r"^\s*op\.", text, re.MULTILINE))


def _extract_section(output: str, name: str) -> str:
    pattern = rf"def {name}\(\):\n(.*?)(?:\n\n|\Z)"
    match = re.search(pattern, output, re.DOTALL)
    return match.group(1) if match else ""


def main() -> None:
    output = _run()
    upgrade = _extract_section(output, "upgrade")
    downgrade = _extract_section(output, "downgrade")

    if _section_ops(upgrade) or _section_ops(downgrade):
        sys.stderr.write("Alembic autogenerate detected changes. Add a migration.\n")
        sys.exit(1)

    print("Alembic autogenerate check passed (no schema changes detected).")


if __name__ == "__main__":
    main()
