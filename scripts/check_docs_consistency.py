#!/usr/bin/env python3
"""Check consistency between specs/planning.md and specs/progress.md.

Guardrails enforced:
- Project name must match
- Phase must match (planning ACTIVE phase vs progress current phase)
- Primary version marker in status lines must match (e.g. v0.3.0)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Could not read {path}: {exc}") from exc


def _extract_project(text: str, label: str) -> str:
    m = re.search(r"^\*\*Project:\*\*\s*(.+)$", text, flags=re.MULTILINE)
    if not m:
        raise RuntimeError(f"{label}: missing '**Project:**' field")
    return m.group(1).strip()


def _extract_status_version(text: str, label: str) -> str:
    m = re.search(r"^\*\*Status:\*\*\s*(.+)$", text, flags=re.MULTILINE)
    if not m:
        raise RuntimeError(f"{label}: missing '**Status:**' field")
    status = m.group(1)
    vm = re.search(r"(v\d+\.\d+\.\d+)", status)
    return vm.group(1) if vm else ""


def _extract_planning_active_phase(text: str) -> str:
    m = re.search(r"^###\s+Phase\s+(\d+):.*-\s+ACTIVE\s*$", text, flags=re.MULTILINE)
    if not m:
        raise RuntimeError(
            "planning.md: could not find an ACTIVE phase heading like '### Phase N: ... - ACTIVE'"
        )
    return m.group(1)


def _extract_progress_current_phase(text: str) -> str:
    m = re.search(
        r"^-\s+\*\*Current Phase:\*\*\s+Phase\s+(\d+)\b",
        text,
        flags=re.MULTILINE,
    )
    if not m:
        raise RuntimeError(
            "progress.md: missing '- **Current Phase:** Phase N ...' line"
        )
    return m.group(1)


def check(planning_path: Path, progress_path: Path) -> list[str]:
    planning = _read(planning_path)
    progress = _read(progress_path)

    errors: list[str] = []

    project_planning = _extract_project(planning, "planning.md")
    project_progress = _extract_project(progress, "progress.md")
    if project_planning != project_progress:
        errors.append(
            f"Project mismatch: planning='{project_planning}' progress='{project_progress}'"
        )

    phase_planning = _extract_planning_active_phase(planning)
    phase_progress = _extract_progress_current_phase(progress)
    if phase_planning != phase_progress:
        errors.append(
            f"Phase mismatch: planning ACTIVE phase={phase_planning}, progress current phase={phase_progress}"
        )

    version_planning = _extract_status_version(planning, "planning.md")
    version_progress = _extract_status_version(progress, "progress.md")
    if version_planning and version_progress and version_planning != version_progress:
        errors.append(
            f"Version mismatch in status lines: planning={version_planning}, progress={version_progress}"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate planning/progress doc consistency.")
    parser.add_argument("--planning", default="specs/planning.md")
    parser.add_argument("--progress", default="specs/progress.md")
    args = parser.parse_args()

    planning = Path(args.planning)
    progress = Path(args.progress)

    try:
        errors = check(planning, progress)
    except RuntimeError as exc:
        print(f"[docs-check] ERROR: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("[docs-check] FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            "[docs-check] Fix hint: update specs/planning.md and specs/progress.md in the same PR.",
            file=sys.stderr,
        )
        return 1

    print("[docs-check] OK: planning/progress are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
