from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _write_docs(tmp_path: Path, planning_status: str, progress_status: str) -> tuple[Path, Path]:
    planning = tmp_path / "planning.md"
    progress = tmp_path / "progress.md"

    planning.write_text(
        "\n".join(
            [
                "# Development Project Planning",
                "",
                "**Project:** orbitr",
                f"**Status:** {planning_status}",
                "",
                "### Phase 8: v0.3.0 Planning and Reliability - ACTIVE",
            ]
        ),
        encoding="utf-8",
    )

    progress.write_text(
        "\n".join(
            [
                "# Development Project Progress",
                "",
                "**Project:** orbitr",
                f"**Status:** {progress_status}",
                "",
                "- **Current Phase:** Phase 8 (v0.3.0 planning and reliability)",
            ]
        ),
        encoding="utf-8",
    )

    return planning, progress


def test_docs_consistency_script_passes(tmp_path: Path) -> None:
    planning, progress = _write_docs(
        tmp_path,
        planning_status="Active development - v0.3.0 planning",
        progress_status="Active development - v0.3.0 planning in progress",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/check_docs_consistency.py",
            "--planning",
            str(planning),
            "--progress",
            str(progress),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0
    assert "OK" in proc.stdout


def test_docs_consistency_script_fails_on_version_mismatch(tmp_path: Path) -> None:
    planning, progress = _write_docs(
        tmp_path,
        planning_status="Active development - v0.3.0 planning",
        progress_status="Active development - v0.2.0 maintenance",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/check_docs_consistency.py",
            "--planning",
            str(planning),
            "--progress",
            str(progress),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert "Version mismatch" in proc.stderr
