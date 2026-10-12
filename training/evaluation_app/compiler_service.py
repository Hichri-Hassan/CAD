"""Compilation and mesh export via FreeCAD."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from compiler.freecad_launcher import find_freecadcmd, run_in_freecad
from compiler.loader import load_cad_json
from training.evaluation_app.config import AppPaths, default_paths
from training.scripts.evaluate_generation import wrap_for_compiler


@dataclass
class CompileResult:
    success: bool
    json_path: Path | None = None
    fcstd_path: Path | None = None
    stl_path: Path | None = None
    error: str | None = None
    compile_log: str | None = None


def compile_payload(
    payload: dict[str, Any],
    output_dir: Path,
    *,
    basename: str,
    project_root: Path,
    export_stl: bool = True,
) -> CompileResult:
    """Compile JSON to .FCStd and optionally export an STL for in-browser viewing."""
    output_dir.mkdir(parents=True, exist_ok=True)
    wrapped = wrap_for_compiler(payload)
    json_path = output_dir / f"{basename}.json"
    fcstd_path = output_dir / f"{basename}.FCStd"
    stl_path = output_dir / f"{basename}.stl" if export_stl else None

    json_path.write_text(json.dumps(wrapped, indent=2), encoding="utf-8")
    try:
        load_cad_json(json_path)
    except ValueError as exc:
        return CompileResult(success=False, json_path=json_path, error=str(exc))

    freecadcmd = find_freecadcmd()
    if freecadcmd is None:
        return CompileResult(
            success=False,
            json_path=json_path,
            error="FreeCAD not found. Install FreeCAD or set FREECAD_CMD.",
        )

    script_path = project_root / "compiler" / "freecad_main.py"
    result = run_in_freecad(
        script_path,
        [str(json_path.resolve()), "-o", str(fcstd_path.resolve())],
        project_root=project_root,
    )
    compile_log = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode != 0 or not fcstd_path.exists():
        return CompileResult(
            success=False,
            json_path=json_path,
            error=compile_log or "Compilation failed",
            compile_log=compile_log or None,
        )

    stl_error: str | None = None
    if export_stl and stl_path is not None:
        stl_error = _export_stl_headless(freecadcmd, fcstd_path, stl_path, project_root)

    return CompileResult(
        success=True,
        json_path=json_path,
        fcstd_path=fcstd_path,
        stl_path=stl_path if stl_path and stl_path.exists() else None,
        error=stl_error,
        compile_log=compile_log or None,
    )


def _export_stl_headless(
    freecadcmd: Path,
    fcstd_path: Path,
    stl_path: Path,
    project_root: Path,
) -> str | None:
    export_script = (project_root / "training" / "evaluation_app" / "freecad_export_stl.py").resolve()
    fcstd_arg = str(fcstd_path.resolve())
    stl_arg = str(stl_path.resolve())
    command = [
        str(freecadcmd),
        "-c",
        (
            "import sys; "
            f"sys.argv = ['export_stl', {fcstd_arg!r}, {stl_arg!r}]; "
            f"exec(open({str(export_script)!r}).read())"
        ),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not stl_path.exists():
        log = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        return log or "STL export failed"
    return None


def open_fcstd_in_freecad(fcstd_path: Path) -> tuple[bool, str]:
    """Open an .FCStd file in the desktop FreeCAD app (macOS/Linux/Windows)."""
    if not fcstd_path.exists():
        return False, f"File not found: {fcstd_path}"

    if sys.platform == "darwin":
        freecad_app = Path("/Applications/FreeCAD.app")
        if freecad_app.exists():
            proc = subprocess.run(
                ["open", "-a", str(freecad_app), str(fcstd_path.resolve())],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                return True, "Opened in FreeCAD"
        proc = subprocess.run(
            ["open", str(fcstd_path.resolve())],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode == 0, proc.stderr.strip() or "Opened with default app"

    if sys.platform.startswith("linux"):
        proc = subprocess.run(
            ["xdg-open", str(fcstd_path.resolve())],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode == 0, proc.stderr.strip() or "Opened with xdg-open"

    proc = subprocess.run(
        ["cmd", "/c", "start", "", str(fcstd_path.resolve())],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0, proc.stderr.strip() or "Opened with default app"


def export_fcstd_to_stl(
    fcstd_path: Path,
    stl_path: Path,
    *,
    project_root: Path,
) -> tuple[bool, str | None]:
    """Export an existing .FCStd to STL for in-browser preview."""
    if not fcstd_path.exists():
        return False, f"FCStd not found: {fcstd_path}"
    freecadcmd = find_freecadcmd()
    if freecadcmd is None:
        return False, "FreeCAD not found. Install FreeCAD or set FREECAD_CMD."
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    if stl_path.exists() and stl_path.stat().st_mtime >= fcstd_path.stat().st_mtime:
        return True, None
    error = _export_stl_headless(freecadcmd, fcstd_path, stl_path, project_root)
    if error:
        return False, error
    return True, None


def compile_reference_if_needed(
    reference_document: dict[str, Any],
    output_dir: Path,
    *,
    basename: str,
    project_root: Path,
) -> CompileResult:
    payload = {
        "metadata": reference_document.get("metadata", {}),
        "operations": reference_document.get("operations", []),
    }
    return compile_payload(payload, output_dir, basename=basename, project_root=project_root)


def ensure_model_artifacts(
    paths: AppPaths,
    model_id: str,
    *,
    reference_document: dict[str, Any] | None = None,
    generated_payload: dict[str, Any] | None = None,
) -> dict[str, Path | None]:
    ref_dir = paths.reference_models_dir
    gen_dir = paths.generated_models_dir
    ref_dir.mkdir(parents=True, exist_ok=True)
    gen_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, Path | None] = {
        "reference_fcstd": ref_dir / f"{model_id}.FCStd",
        "reference_stl": ref_dir / f"{model_id}.stl",
        "generated_fcstd": gen_dir / f"{model_id}.FCStd",
        "generated_stl": gen_dir / f"{model_id}.stl",
    }

    if reference_document is not None and not artifacts["reference_fcstd"].exists():
        result = compile_reference_if_needed(
            reference_document,
            ref_dir,
            basename=model_id,
            project_root=paths.project_root,
        )
        if result.fcstd_path:
            artifacts["reference_fcstd"] = result.fcstd_path
        if result.stl_path:
            artifacts["reference_stl"] = result.stl_path

    if generated_payload is not None and not artifacts["generated_fcstd"].exists():
        result = compile_payload(
            generated_payload,
            gen_dir,
            basename=model_id,
            project_root=paths.project_root,
        )
        if result.fcstd_path:
            artifacts["generated_fcstd"] = result.fcstd_path
        if result.stl_path:
            artifacts["generated_stl"] = result.stl_path

    for key, path in list(artifacts.items()):
        if path is not None and not path.exists():
            artifacts[key] = None
    return artifacts
