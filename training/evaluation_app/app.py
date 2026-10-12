#!/usr/bin/env python3
"""CAD Copilot qualitative evaluation dashboard."""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.evaluation_app.compiler_service import compile_payload, ensure_model_artifacts, export_fcstd_to_stl, open_fcstd_in_freecad
from training.evaluation_app.config import ADAPTER_PRESETS, AppPaths, default_paths
from training.evaluation_app.data_loader import EvalExample, dataset_stats, load_eval_examples
from training.evaluation_app.diff_engine import compare_operations, format_json, highlight_json, unified_json_diff
from training.evaluation_app.export_service import build_markdown_report, export_json_metrics, write_exports
from training.evaluation_app.feature_loader import extract_hole_specs, load_through_hole_records
from training.evaluation_app.inference import InferenceService
from training.evaluation_app.metrics import aggregate_metrics
from training.evaluation_app.theme import DARK_THEME_CSS
from training.evaluation_app.viewer import render_compile_artifacts, render_stl_mesh, render_stl_or_image


def main() -> None:
    st.set_page_config(
        page_title="CAD Copilot Eval",
        page_icon="📐",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

    _ensure_session_state()
    paths = _paths_from_sidebar()
    _sync_paths(paths)

    tab_compare, tab_dataset, tab_through_holes, tab_playground, tab_ambiguity, tab_export = st.tabs(
        ["Compare", "Dataset", "Through holes", "Playground", "Ambiguity", "Export"]
    )

    examples = load_eval_examples(paths, prompt_index=st.session_state.prompt_index)
    filtered = _filter_examples(examples, st.session_state.search_query)
    aggregate = aggregate_metrics([ex.analysis for ex in examples])

    with tab_compare:
        _render_compare_view(paths, examples, filtered, aggregate)

    with tab_dataset:
        _render_dataset_view(examples)

    with tab_through_holes:
        _render_through_holes_view(paths)

    with tab_playground:
        _render_playground(paths)

    with tab_ambiguity:
        _render_ambiguity_mode(paths)

    with tab_export:
        _render_export_tab(paths, examples, aggregate)


def _ensure_session_state() -> None:
    base = default_paths()
    if "selected_model_id" not in st.session_state:
        st.session_state.selected_model_id = None
    if "prompt_index" not in st.session_state:
        st.session_state.prompt_index = 0
    if "inference" not in st.session_state:
        st.session_state.inference = InferenceService(base)
    if "playground_results" not in st.session_state:
        st.session_state.playground_results = []
    if "ambiguity_results" not in st.session_state:
        st.session_state.ambiguity_results = []


def _sync_paths(paths: AppPaths) -> None:
    st.session_state.paths = paths
    st.session_state.inference.paths = paths


def _paths_from_sidebar() -> AppPaths:
    base = default_paths()
    with st.sidebar:
        st.title("CAD Copilot Eval")
        st.caption("Qualitative generation analysis")
        st.markdown("Shortcuts: <kbd>j</kbd>/<kbd>k</kbd> navigate", unsafe_allow_html=True)

        eval_dir = Path(st.text_input("Evaluation dir", str(base.eval_dir)))
        preset_labels = list(ADAPTER_PRESETS.keys())
        default_label = next(
            (label for label, path in ADAPTER_PRESETS.items() if path == base.adapter),
            preset_labels[0],
        )
        selected_label = st.selectbox(
            "Adapter",
            options=preset_labels,
            index=preset_labels.index(default_label),
        )
        adapter = ADAPTER_PRESETS[selected_label]
        st.caption(str(adapter))
        prompt_index = st.selectbox("Prompt index", options=[0, 1, 2, 3, 4], index=0)
        st.session_state.prompt_index = prompt_index

        load_model = st.toggle("Load model for generation", value=False)
        if load_model:
            try:
                st.session_state.inference.load()
                st.success("Model loaded")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Model load failed: {exc}")
        else:
            st.session_state.inference.unload()

        st.divider()
        st.text_input("Search examples", key="search_query", placeholder="Filter by model or prompt…")

    return AppPaths(
        project_root=base.project_root,
        adapter=adapter,
        config=base.config,
        system_prompt=base.system_prompt,
        test_json_dir=base.test_json_dir,
        metadata=base.metadata,
        eval_dir=eval_dir,
        screenshots_dir=eval_dir / "screenshots",
        export_dir=eval_dir / "exports",
        features_dir=base.features_dir,
    )


def _filter_examples(examples: list[EvalExample], query: str) -> list[EvalExample]:
    if not query.strip():
        return examples
    q = query.strip().lower()
    return [
        ex
        for ex in examples
        if q in ex.model_id.lower() or q in ex.prompt.lower() or q in " ".join(ex.analysis.error_labels).lower()
    ]


def _render_compare_view(
    paths: AppPaths,
    examples: list[EvalExample],
    filtered: list[EvalExample],
    aggregate: dict,
) -> None:
    left, center, right = st.columns([1.1, 2.2, 1.2], gap="medium")

    with left:
        st.subheader("Examples")
        if not filtered:
            st.info("No examples match your filter.")
            return

        model_ids = [ex.model_id for ex in filtered]
        if st.session_state.selected_model_id not in model_ids:
            st.session_state.selected_model_id = model_ids[0]

        for example in filtered:
            selected = example.model_id == st.session_state.selected_model_id
            card_class = "eval-card selected" if selected else "eval-card"
            acc = example.analysis.metrics.type_accuracy
            acc_text = f"{acc:.0%}" if acc is not None else "—"
            exact = "yes" if example.analysis.metrics.exact_match else "no"
            compile_ok = example.compilation_success
            compile_text = "✓" if compile_ok else ("✗" if compile_ok is False else "—")
            if st.button(
                f"{example.model_id}\n{example.prompt[:48]}…\n"
                f"status={example.generation_status} | compile={compile_text} | acc={acc_text} | exact={exact}",
                key=f"pick_{example.model_id}",
                use_container_width=True,
            ):
                st.session_state.selected_model_id = example.model_id

    selected = next((ex for ex in filtered if ex.model_id == st.session_state.selected_model_id), None)
    if selected is None:
        return

    with center:
        st.subheader(selected.model_id)
        st.markdown(f"**Prompt:** {selected.prompt}")

        ref_json = {"operations": selected.reference_ops}
        gen_json = {"operations": selected.generated_ops or []}

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Ground Truth JSON**")
            st.markdown(
                f'<div class="json-panel">{highlight_json(format_json(ref_json))}</div>',
                unsafe_allow_html=True,
            )
        with col_b:
            st.markdown("**Generated JSON**")
            st.markdown(
                f'<div class="json-panel">{highlight_json(format_json(gen_json))}</div>',
                unsafe_allow_html=True,
            )

        with st.expander("Unified diff", expanded=False):
            st.code(unified_json_diff(ref_json, gen_json), language="diff")

        diffs = compare_operations(selected.reference_ops, selected.generated_ops)
        diff_rows = [
            {
                "Index": d.index,
                "Kind": d.kind,
                "Reference": d.reference.get("type") if d.reference else "—",
                "Generated": d.generated.get("type") if d.generated else "—",
                "Detail": d.detail,
            }
            for d in diffs
            if d.kind != "match"
        ]
        if diff_rows:
            st.markdown("**Operation differences**")
            st.dataframe(pd.DataFrame(diff_rows), use_container_width=True, hide_index=True)

    with right:
        st.subheader("Statistics")
        _metric_row("JSON valid", selected.json_valid)
        _metric_row("Schema valid", selected.schema_valid)
        _metric_row("Compiled", selected.compilation_success)
        st.markdown(
            f"**Operation accuracy:** {_pct(selected.analysis.metrics.type_accuracy)}  \n"
            f"**Exact match:** {'Yes' if selected.analysis.metrics.exact_match else 'No'}"
        )
        st.markdown("**GT operations**  \n" + " → ".join(selected.analysis.metrics.reference_types))
        st.markdown("**Prediction**  \n" + " → ".join(selected.analysis.metrics.generated_types or ["—"]))

        if selected.analysis.error_labels:
            st.markdown("**Error categories**")
            for label in selected.analysis.error_labels:
                st.markdown(f'<span class="error-chip">{label}</span>', unsafe_allow_html=True)

        st.divider()
        st.markdown("**CAD viewer**")
        artifacts = ensure_model_artifacts(
            paths,
            selected.model_id,
            reference_document=selected.reference_document,
            generated_payload=selected.generated_payload,
        )
        vcol1, vcol2 = st.columns(2)
        with vcol1:
            render_stl_or_image(
                artifacts.get("reference_stl"),
                None,
                fcstd_path=artifacts.get("reference_fcstd"),
                label="Ground Truth",
            )
        with vcol2:
            render_stl_or_image(
                artifacts.get("generated_stl"),
                None,
                fcstd_path=artifacts.get("generated_fcstd"),
                label="Generated",
            )

        _screenshot_uploader(paths, selected.model_id)

    st.divider()
    st.subheader("Dataset metrics")
    metric_cols = st.columns(7)
    metric_cols[0].metric("JSON validity", _pct(aggregate.get("json_validity_rate")))
    metric_cols[1].metric("Schema validity", _pct(aggregate.get("schema_validity_rate")))
    metric_cols[2].metric("Compile success", _pct(aggregate.get("compilation_success_rate")))
    metric_cols[3].metric("Op precision", _pct(aggregate.get("operation_precision")))
    metric_cols[4].metric("Op recall", _pct(aggregate.get("operation_recall")))
    metric_cols[5].metric("Op F1", _pct(aggregate.get("operation_f1")))
    metric_cols[6].metric("Exact match", _pct(aggregate.get("exact_match_rate")))

    rows = []
    for ex in examples:
        rows.append(
            {
                "Model": ex.model_id,
                "JSON": ex.json_valid,
                "Schema": ex.schema_valid,
                "Compile": ex.compilation_success,
                "Precision": ex.analysis.metrics.precision,
                "Recall": ex.analysis.metrics.recall,
                "F1": ex.analysis.metrics.f1,
                "Type acc": ex.analysis.metrics.type_accuracy,
                "Exact": ex.analysis.metrics.exact_match,
                "Errors": ", ".join(ex.analysis.error_labels),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_dataset_view(examples: list[EvalExample]) -> None:
    stats = dataset_stats(examples)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Examples", stats["example_count"])
    c2.metric("Avg prompt length", f"{stats['avg_prompt_length']:.0f}")
    c3.metric("Avg op count", f"{stats['avg_operation_count']:.1f}")
    c4.metric("Unique models", stats["unique_models"])

    op_df = pd.DataFrame(
        [{"operation": k, "count": v} for k, v in stats["operation_frequency"].items()]
    ).sort_values("count", ascending=False)
    if not op_df.empty:
        fig = px.bar(op_df, x="operation", y="count", title="Operation frequency (ground truth)")
        fig.update_layout(paper_bgcolor="#171a21", plot_bgcolor="#171a21", font_color="#e6e9ef")
        st.plotly_chart(fig, use_container_width=True)

    prompt_df = pd.DataFrame({"prompt_length": stats["prompt_lengths"], "operation_count": stats["operation_counts"]})
    if not prompt_df.empty:
        fig2 = px.scatter(prompt_df, x="prompt_length", y="operation_count", title="Prompt length vs operation count")
        fig2.update_layout(paper_bgcolor="#171a21", plot_bgcolor="#171a21", font_color="#e6e9ef")
        st.plotly_chart(fig2, use_container_width=True)


def _render_through_holes_view(paths: AppPaths) -> None:
    st.subheader("Through-hole feature dataset")
    st.caption(
        "Browse the generated through-hole ground-truth models with dimensions, "
        "validation results, and interactive 3D preview."
    )

    records = load_through_hole_records(paths.features_dir, paths.project_root)
    if not records:
        st.warning(
            f"No through-hole models found under `{paths.features_dir / 'through_holes'}`. "
            "Run `python3 scripts/generate_feature_models.py --mode family --count 30` first."
        )
        return

    passed = sum(1 for record in records if record.passed_validation)
    st.metric("Models", f"{len(records)}", delta=f"{passed} passed validation")

    labels = [f"{record.index:02d} · {record.shape_id}" for record in records]
    label_to_record = dict(zip(labels, records, strict=True))
    selected_label = st.selectbox("Select model", labels, index=0)
    record = label_to_record[selected_label]
    specs = extract_hole_specs(record.operations)

    col_dims, col_view = st.columns([1, 1.4])

    with col_dims:
        st.markdown("**Expected dimensions (mm)**")
        dim_rows = [
            ("Prism length (X)", record.length_mm),
            ("Prism width (Y)", record.width_mm),
            ("Prism height (Z / pad)", record.height_mm),
            ("Hole diameter", record.diameter_mm),
            ("Circle radius (JSON)", specs.get("circle_radius_mm")),
            ("Hole center X", specs.get("circle_center_mm", [None, None])[0]),
            ("Hole center Y", specs.get("circle_center_mm", [None, None])[1]),
            ("Hole depth", specs.get("hole_depth")),
        ]
        st.table(
            {
                "Parameter": [row[0] for row in dim_rows],
                "Value": [row[1] for row in dim_rows],
            }
        )

        if record.validation_summary.get("bbox"):
            st.markdown("**Measured bounding box (FreeCAD)**")
            bbox = record.validation_summary["bbox"]
            st.json(bbox)

        if record.validation_summary.get("volume") is not None:
            expected_vol = record.length_mm * record.width_mm * record.height_mm
            hole_vol = math.pi * (record.diameter_mm / 2) ** 2 * record.height_mm
            expected_vol -= hole_vol
            st.markdown("**Volume check**")
            st.write(f"Measured: **{record.validation_summary['volume']:.2f} mm³**")
            st.write(f"Expected: **{expected_vol:.2f} mm³**")

        status = "PASS" if record.passed_validation else "FAIL"
        st.markdown(f"Validation: **{status}**")

        with st.expander("Training prompts"):
            for idx, prompt in enumerate(record.prompts, start=1):
                st.markdown(f"{idx}. {prompt}")

    with col_view:
        stl_path = paths.feature_stl_cache_dir / f"{record.shape_id}.stl"
        if record.fcstd_path.exists():
            with st.spinner("Preparing 3D preview…"):
                ok, err = export_fcstd_to_stl(
                    record.fcstd_path,
                    stl_path,
                    project_root=paths.project_root,
                )
            if ok and stl_path.exists():
                render_stl_mesh(stl_path, label="Interactive 3D preview (rotate / zoom)")
            else:
                st.error(err or "Could not export STL for preview.")
        else:
            st.error(f"FCStd not found: `{record.fcstd_path}`")

        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if record.fcstd_path.exists():
                st.download_button(
                    "Download .FCStd",
                    data=record.fcstd_path.read_bytes(),
                    file_name=record.fcstd_path.name,
                    use_container_width=True,
                )
        with btn2:
            if record.json_path.exists():
                st.download_button(
                    "Download JSON",
                    data=record.json_path.read_bytes(),
                    file_name=record.json_path.name,
                    use_container_width=True,
                )
        with btn3:
            if record.fcstd_path.exists() and st.button("Open in FreeCAD", use_container_width=True):
                ok, message = open_fcstd_in_freecad(record.fcstd_path)
                if ok:
                    st.toast(message)
                else:
                    st.warning(message)

    with st.expander("Canonical CAD JSON", expanded=False):
        st.code(format_json({"operations": record.operations}), language="json")


def _render_playground(paths: AppPaths) -> None:
    st.subheader("Prompt experimentation")
    st.caption("Generate, compile to .FCStd, and preview the 3D model without modifying the held-out dataset.")

    if not st.session_state.inference.is_loaded:
        st.info("Enable **Load model for generation** in the sidebar to generate new prompts.")

    prompt = st.text_area("Prompt", height=120, placeholder="Describe the CAD model to generate…")
    max_tokens = st.slider("Max new tokens", 256, 4096, 2048, 256)
    temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.05)
    auto_compile = st.checkbox("Auto-compile to .FCStd after generation", value=True)

    if st.button("Generate", type="primary"):
        if not prompt.strip():
            st.warning("Enter a prompt first.")
            return
        if not st.session_state.inference.is_loaded:
            st.error("Load the model in the sidebar first.")
            return
        try:
            with st.spinner("Generating CAD JSON…"):
                result = st.session_state.inference.generate(
                    prompt.strip(),
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                )

            compile_result = None
            if auto_compile:
                compile_result = _compile_generation_result(paths, result, prompt.strip())

            st.session_state.playground_results.insert(
                0,
                {
                    "prompt": prompt.strip(),
                    "result": result,
                    "compile": compile_result,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    for idx, item in enumerate(st.session_state.playground_results[:10]):
        with st.expander(f"{item['created_at']} — {item['prompt'][:60]}", expanded=idx == 0):
            result = item["result"]
            st.markdown(
                f"JSON valid: **{result.json_valid}** | Schema valid: **{result.schema_valid}** | "
                f"Operations: **{len(result.operations or [])}**"
            )
            if result.payload is not None:
                st.code(format_json(result.payload), language="json")
            else:
                st.code(result.raw_text, language="text")

            compile_result = item.get("compile")
            if compile_result is None and result.payload is not None:
                if st.button("Compile to .FCStd", key=f"compile_playground_{idx}"):
                    item["compile"] = _compile_generation_result(paths, result, item["prompt"])
                    st.rerun()
            else:
                render_compile_artifacts(compile_result, title="Compiled model")


def _compile_generation_result(paths: AppPaths, result, prompt: str):
    from training.evaluation_app.compiler_service import CompileResult

    if not result.payload or not result.operations:
        return CompileResult(success=False, error="No operations to compile.")

    slug = _playground_slug(prompt)
    out_dir = paths.eval_dir / "playground"
    with st.spinner("Compiling to .FCStd…"):
        return compile_payload(
            result.payload,
            out_dir,
            basename=slug,
            project_root=paths.project_root,
        )


def _playground_slug(prompt: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in prompt.lower())[:40].strip("_")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"playground_{safe or 'model'}_{timestamp}"


def _render_ambiguity_mode(paths: AppPaths) -> None:
    st.subheader("Prompt Ambiguity Mode")
    st.caption("Generate multiple outputs with different seeds and compare side by side.")

    examples = load_eval_examples(paths, prompt_index=st.session_state.prompt_index)
    model_ids = [ex.model_id for ex in examples]
    selected_id = st.selectbox("Example prompt", model_ids) if model_ids else None
    default_prompt = next((ex.prompt for ex in examples if ex.model_id == selected_id), "")
    prompt = st.text_area("Prompt", value=default_prompt, height=100)
    count = st.slider("Number of generations", 2, 10, 5)
    base_seed = st.number_input("Base seed", min_value=0, value=42, step=1)

    if st.button("Generate N outputs", type="primary"):
        if not prompt.strip():
            st.warning("Enter a prompt.")
            return
        if not st.session_state.inference.is_loaded:
            st.error("Load the model in the sidebar first.")
            return
        try:
            with st.spinner(f"Generating {count} outputs…"):
                results = st.session_state.inference.generate_many(
                    prompt.strip(),
                    count=count,
                    base_seed=int(base_seed),
                )
            compiled = []
            for idx, result in enumerate(results):
                compile_result = None
                if result.payload and result.operations:
                    compile_result = compile_payload(
                        result.payload,
                        paths.eval_dir / "playground" / "ambiguity",
                        basename=f"ambiguity_{idx + 1}_seed{result.seed}",
                        project_root=paths.project_root,
                    )
                compiled.append({"result": result, "compile": compile_result})
            st.session_state.ambiguity_results = compiled
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    if not st.session_state.ambiguity_results:
        return

    for idx, item in enumerate(st.session_state.ambiguity_results):
        result = item["result"]
        compile_result = item.get("compile")
        with st.expander(f"Generation {idx + 1} (seed={result.seed})", expanded=idx == 0):
            st.caption(f"ops={len(result.operations or [])} | schema={result.schema_valid}")
            if result.payload is not None:
                st.code(format_json(result.payload), language="json")
            else:
                st.code(result.raw_text[:800], language="text")
            render_compile_artifacts(compile_result, title=f"Model {idx + 1}")


def _render_export_tab(paths: AppPaths, examples: list[EvalExample], aggregate: dict) -> None:
    st.subheader("Export")
    out_dir = paths.export_dir
    st.text(f"Output directory: {out_dir}")

    c1, c2, c3 = st.columns(3)
    if c1.button("Export markdown report"):
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "comparison_report.md"
        path.write_text(build_markdown_report(examples, aggregate), encoding="utf-8")
        st.success(f"Wrote {path}")

    if c2.button("Export metrics JSON"):
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "metrics.json"
        path.write_text(json.dumps(export_json_metrics(examples, aggregate), indent=2) + "\n", encoding="utf-8")
        st.success(f"Wrote {path}")

    if c3.button("Export bundle"):
        written = write_exports(out_dir, examples)
        st.success(f"Exported: {', '.join(str(p) for p in written.values())}")

    st.download_button(
        "Download markdown",
        data=build_markdown_report(examples, aggregate),
        file_name="cad_copilot_eval_report.md",
        mime="text/markdown",
    )
    st.download_button(
        "Download metrics JSON",
        data=json.dumps(export_json_metrics(examples, aggregate), indent=2),
        file_name="cad_copilot_metrics.json",
        mime="application/json",
    )


def _screenshot_uploader(paths: AppPaths, model_id: str) -> None:
    with st.expander("Attach screenshots", expanded=False):
        shot_dir = paths.screenshots_dir / model_id
        shot_dir.mkdir(parents=True, exist_ok=True)
        gt_file = st.file_uploader("Ground truth screenshot", type=["png", "jpg", "jpeg", "webp"], key=f"gt_{model_id}")
        pred_file = st.file_uploader("Prediction screenshot", type=["png", "jpg", "jpeg", "webp"], key=f"pred_{model_id}")
        if gt_file is not None:
            target = shot_dir / f"ground_truth{Path(gt_file.name).suffix}"
            target.write_bytes(gt_file.getvalue())
            st.image(str(target), caption="Saved GT screenshot", use_container_width=True)
        if pred_file is not None:
            target = shot_dir / f"prediction{Path(pred_file.name).suffix}"
            target.write_bytes(pred_file.getvalue())
            st.image(str(target), caption="Saved prediction screenshot", use_container_width=True)

        saved = list(shot_dir.glob("*"))
        if saved:
            st.caption(f"{len(saved)} screenshot(s) stored in {shot_dir}")


def _metric_row(label: str, value: bool | None) -> None:
    if value is True:
        st.markdown(f"{label}: <span class='metric-pill good'>✓</span>", unsafe_allow_html=True)
    elif value is False:
        st.markdown(f"{label}: <span class='metric-pill bad'>✗</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"{label}: <span class='metric-pill warn'>—</span>", unsafe_allow_html=True)


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1%}"


if __name__ == "__main__":
    main()
