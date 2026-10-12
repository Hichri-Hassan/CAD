"""3D mesh viewers and compile artifact display for the evaluation dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:
    from training.evaluation_app.compiler_service import CompileResult

__all__ = [
    "render_compile_artifacts",
    "render_stl_mesh",
    "render_stl_or_image",
]


def render_compile_artifacts(compile_result: CompileResult | Any | None, *, title: str = "3D Model") -> None:
    """Show compile status, FCStd download/open actions, and interactive STL preview."""
    from training.evaluation_app.compiler_service import open_fcstd_in_freecad

    st.markdown(f"**{title}**")

    if compile_result is None:
        st.info("Not compiled yet.")
        return

    if not compile_result.success:
        st.error(compile_result.error or "Compilation failed")
        if compile_result.compile_log:
            with st.expander("Compiler log"):
                st.code(compile_result.compile_log, language="text")
        return

    st.success("Compiled successfully")

    if compile_result.fcstd_path and compile_result.fcstd_path.exists():
        fcstd_path = compile_result.fcstd_path
        st.caption(f"FCStd: `{fcstd_path}`")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "Download .FCStd",
                data=fcstd_path.read_bytes(),
                file_name=fcstd_path.name,
                mime="application/octet-stream",
                use_container_width=True,
            )
        with col2:
            if compile_result.json_path and compile_result.json_path.exists():
                st.download_button(
                    "Download JSON",
                    data=compile_result.json_path.read_bytes(),
                    file_name=compile_result.json_path.name,
                    mime="application/json",
                    use_container_width=True,
                )
        with col3:
            if st.button("Open in FreeCAD", key=f"open_fcstd_{fcstd_path.name}", use_container_width=True):
                ok, message = open_fcstd_in_freecad(fcstd_path)
                if ok:
                    st.toast(message)
                else:
                    st.warning(message)

    if compile_result.stl_path and compile_result.stl_path.exists():
        render_stl_mesh(compile_result.stl_path, label="Interactive preview (rotate / zoom / pan)")
    elif compile_result.success:
        st.warning(
            "FCStd was created but STL preview is unavailable. "
            "Use **Open in FreeCAD** or **Download .FCStd** to inspect the model."
        )
        if compile_result.error:
            with st.expander("STL export log"):
                st.code(compile_result.error, language="text")


def render_stl_or_image(
    stl_path: Path | None,
    png_path: Path | None,
    *,
    fcstd_path: Path | None = None,
    label: str,
) -> None:
    st.caption(label)
    if fcstd_path is not None and fcstd_path.exists():
        from training.evaluation_app.compiler_service import open_fcstd_in_freecad

        if st.button(f"Open {label} in FreeCAD", key=f"open_{fcstd_path.name}_{label}"):
            ok, message = open_fcstd_in_freecad(fcstd_path)
            if ok:
                st.toast(message)
            else:
                st.warning(message)

    if png_path is not None and png_path.exists():
        st.image(str(png_path), use_container_width=True)
        return

    if stl_path is not None and stl_path.exists():
        render_stl_mesh(stl_path, label="")
        return

    st.info("No render available. Compile the model or attach a screenshot.")


def render_stl_mesh(stl_path: Path, *, label: str = "") -> None:
    if label:
        st.caption(label)
    try:
        import plotly.graph_objects as go

        vertices, faces = _load_stl(stl_path)
        fig = go.Figure(
            data=[
                go.Mesh3d(
                    x=vertices[:, 0],
                    y=vertices[:, 1],
                    z=vertices[:, 2],
                    i=faces[:, 0],
                    j=faces[:, 1],
                    k=faces[:, 2],
                    color="#6ea8fe",
                    opacity=0.95,
                )
            ]
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="#171a21",
            plot_bgcolor="#171a21",
            scene=dict(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                zaxis=dict(visible=False),
                bgcolor="#171a21",
                aspectmode="data",
            ),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not render STL: {exc}")


def _load_stl(path: Path):
    import numpy as np

    try:
        from stl import mesh

        stl_mesh = mesh.Mesh.from_file(str(path))
        vertices = stl_mesh.vectors.reshape(-1, 3)
        unique_vertices, inverse = np.unique(vertices, axis=0, return_inverse=True)
        faces = inverse.reshape(-1, 3)
        return unique_vertices, faces
    except ImportError:
        pass

    data = path.read_bytes()
    if data.startswith(b"solid"):
        return _parse_ascii_stl(data.decode("utf-8", errors="ignore"))
    return _parse_binary_stl(data)


def _parse_ascii_stl(text: str):
    import numpy as np

    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    current: list[list[float]] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        if parts[0] == "vertex" and len(parts) >= 4:
            current.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif parts[0] == "endloop" and len(current) == 3:
            base = len(vertices)
            vertices.extend(current)
            faces.append([base, base + 1, base + 2])
            current = []
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)


def _parse_binary_stl(data: bytes):
    import numpy as np
    import struct

    triangle_count = struct.unpack_from("<I", data, 80)[0]
    offset = 84
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for _ in range(triangle_count):
        tri = struct.unpack_from("<12f", data, offset)
        offset += 50
        base = len(vertices)
        vertices.extend([list(tri[3:6]), list(tri[6:9]), list(tri[9:12])])
        faces.append([base, base + 1, base + 2])
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)
