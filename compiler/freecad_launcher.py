"""Locate FreeCAD command-line binary."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def find_freecadcmd() -> Path | None:
    """Return the path to a FreeCAD command-line executable, if available."""
    env_path = os.environ.get("FREECAD_CMD")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate

    which = shutil.which("freecadcmd") or shutil.which("FreeCADCmd")
    if which:
        return Path(which)

    candidates = [
        Path("/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"),
        Path("/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd"),
        Path("/Applications/FreeCAD.app/Contents/MacOS/freecadcmd"),
        Path("/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd"),
        Path.home() / "Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def run_in_freecad(
    script_path: Path,
    args: list[str],
    *,
    project_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a Python script inside the FreeCAD environment."""
    freecadcmd = find_freecadcmd()
    if freecadcmd is None:
        raise FileNotFoundError(
            "FreeCAD command-line executable not found. "
            "Install FreeCAD or set FREECAD_CMD to the FreeCADCmd binary."
        )

    if project_root is None:
        project_root = script_path.resolve().parent.parent

    env = os.environ.copy()
    env["CAD_COMPILER_ROOT"] = str(project_root)

    arg_literal = ", ".join(repr(arg) for arg in args)
    command = [
        str(freecadcmd),
        "-c",
        (
            "import sys; "
            f"sys.argv = ['freecad_main', {arg_literal}]; "
            f"exec(open({str(script_path)!r}).read())"
        ),
    ]
    return subprocess.run(command, check=False, text=True, capture_output=True, env=env)
