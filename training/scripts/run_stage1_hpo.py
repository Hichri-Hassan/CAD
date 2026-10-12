#!/usr/bin/env python3
"""Run Stage 1 HPO experiments and generate the final report."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT_ROOT / "training" / "scripts"


def main() -> int:
    stage_dir = PROJECT_ROOT / "training" / "experiments" / "stage1"

    run_cmd = [sys.executable, str(SCRIPTS / "run_hpo_stage.py"), "--stage-dir", str(stage_dir)]
    print("Starting Stage 1 HPO training...")
    run_result = subprocess.run(run_cmd, check=False)
    if run_result.returncode != 0:
        print("Stage 1 completed with one or more failures; generating report anyway.")

    report_cmd = [
        sys.executable,
        str(SCRIPTS / "report_stage.py"),
        "--stage",
        "stage1",
    ]
    report_result = subprocess.run(report_cmd, check=False)
    return report_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
