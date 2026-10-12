"""Generate the summary.md research-style report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from analysis.aggregator import distribution_percentages, numeric_summary, top_items
from analysis.models import DatasetStats


def _pct(part: int, whole: int) -> str:
    if whole == 0:
        return "0.0%"
    return f"{part / whole * 100:.1f}%"


def _format_table_rows(items: list[tuple[str, int]], total: int, limit: int = 15) -> list[str]:
    lines = []
    for name, count in items[:limit]:
        pct = count / total * 100 if total else 0
        lines.append(f"| {name} | {count:,} | {pct:.2f}% |")
    return lines


def generate_summary_report(output_dir: Path, dataset: DatasetStats, figure_names: list[str]) -> Path:
    """Write summary.md to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "summary.md"

    file_stats = numeric_summary(dataset.file_sizes)
    op_stats = numeric_summary(dataset.operations_per_model)
    sketch_stats = numeric_summary(dataset.sketches_per_model)
    depth_stats = numeric_summary(dataset.feature_tree_depths)

    total_ops = sum(dataset.operation_counts.values())
    total_geom = sum(dataset.geometry_counts.values())
    total_constraints = sum(dataset.constraint_counts.values())

    geom_pct = distribution_percentages(dataset.geometry_counts)
    constraint_pct = distribution_percentages(dataset.constraint_counts)
    unsupported_ops = top_items(dataset.unsupported_operation_counts, 20)
    common_chains = top_items(dataset.feature_chain_counts, 15)
    common_transitions = top_items(dataset.operation_cooccurrence, 15)

    fully_parsed = dataset.successfully_parsed - dataset.partially_parsed
    parser_coverage = _pct(dataset.successfully_parsed, dataset.total_models)

    lines = [
        "# Dataset Analysis Report",
        "",
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "## 1. Dataset Summary",
        "",
        "This report presents an automated analysis of the collected FreeCAD (`.FCStd`) dataset. "
        "The objective is to quantify dataset composition, parser coverage, sketch complexity, "
        "and unsupported CAD functionality prior to model training or parser extension.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total models | {dataset.total_models:,} |",
        f"| Successfully parsed (≥1 operation) | {dataset.successfully_parsed:,} ({parser_coverage}) |",
        f"| Fully parsed (no unsupported features) | {fully_parsed:,} ({_pct(fully_parsed, dataset.total_models)}) |",
        f"| Partially parsed | {dataset.partially_parsed:,} ({_pct(dataset.partially_parsed, dataset.total_models)}) |",
        f"| Parser failures | {dataset.parser_failures:,} ({_pct(dataset.parser_failures, dataset.total_models)}) |",
        f"| Corrupted files | {dataset.corrupted_files:,} |",
        f"| Unsupported models (no extractable body tree) | {dataset.unsupported_models:,} |",
        "",
        "### File Size Statistics",
        "",
        "| Statistic | Bytes |",
        "|---|---:|",
        f"| Mean | {file_stats['mean']:,.0f} |",
        f"| Median | {file_stats['median']:,.0f} |",
        f"| Minimum | {file_stats['min']:,.0f} |",
        f"| Maximum | {file_stats['max']:,.0f} |",
        "",
        "## 2. Parser Coverage",
        "",
        "Each model was processed using the existing CAD Copilot parser in lenient mode. "
        "Raw PartDesign feature trees were additionally inspected to identify operation types "
        "outside the current parser scope.",
        "",
        f"- **Parser success rate:** {parser_coverage} of models yielded at least one supported operation.",
        f"- **Full coverage rate:** {_pct(fully_parsed, dataset.total_models)} of models contain only parser-supported features.",
        f"- **Failure rate:** {_pct(dataset.parser_failures, dataset.total_models)} of models could not be usefully parsed.",
        "",
        "Detailed failure records are available in `parser_failures.csv`.",
        "",
        "## 3. Operation Distribution",
        "",
        f"The dataset contains **{total_ops:,}** PartDesign body features across all models.",
        "",
        "| Operation | Count | Percentage |",
        "|---|---:|---:|",
    ]
    lines.extend(_format_table_rows(top_items(dataset.operation_counts, 20), total_ops))
    lines.extend(
        [
            "",
            f"- Mean features per model: **{op_stats['mean']:.2f}**",
            f"- Median features per model: **{op_stats['median']:.1f}**",
            f"- Maximum feature tree depth: **{int(depth_stats['max'])}**",
            "",
            "## 4. Sketch Statistics",
            "",
            f"- Mean sketches per model: **{sketch_stats['mean']:.2f}**",
            f"- Median sketches per model: **{sketch_stats['median']:.1f}**",
            f"- Total sketch entities: **{total_geom:,}**",
            f"- Total sketch constraints: **{total_constraints:,}**",
            f"- Construction geometry entities: **{dataset.construction_geometry_count:,}**",
            "",
            "## 5. Geometry Statistics",
            "",
            "| Geometry Type | Count | Percentage |",
            "|---|---:|---:|",
        ]
    )
    lines.extend(_format_table_rows(top_items(dataset.geometry_counts, 15), total_geom))
    lines.extend(
        [
            "",
            "## 6. Constraint Statistics",
            "",
            "| Constraint Type | Count | Percentage |",
            "|---|---:|---:|",
        ]
    )
    lines.extend(_format_table_rows(top_items(dataset.constraint_counts, 15), total_constraints))
    lines.extend(
        [
            "",
            "## 7. Complexity Statistics",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Average feature tree depth | {depth_stats['mean']:.2f} |",
            f"| Median feature tree depth | {depth_stats['median']:.1f} |",
            f"| Maximum feature tree depth | {int(depth_stats['max'])} |",
            f"| 90th percentile feature tree depth | {depth_stats['p90']:.1f} |",
            "",
            "## 8. Unsupported Operations",
            "",
            "The following operation types appear in the dataset but are not fully supported by the current parser. "
            "These counts guide parser development prioritization.",
            "",
            "| Operation | Occurrences |",
            "|---|---:|",
        ]
    )
    if unsupported_ops:
        for name, count in unsupported_ops:
            lines.append(f"| {name} | {count:,} |")
    else:
        lines.append("| *(none detected)* | 0 |")

    lines.extend(
        [
            "",
            "## 9. Feature Sequences and Co-occurrence",
            "",
            "Transition patterns and common feature chains may inform future autoregressive CAD generation models.",
            "",
            "### Most Common Operation Transitions",
            "",
            "| Transition | Count |",
            "|---|---:|",
        ]
    )
    for name, count in common_transitions:
        lines.append(f"| {name} | {count:,} |")

    lines.extend(
        [
            "",
            "### Most Common Feature Chains",
            "",
            "| Feature Chain | Count |",
            "|---|---:|",
        ]
    )
    for name, count in common_chains:
        lines.append(f"| {name} | {count:,} |")

    lines.extend(
        [
            "",
            "## 10. Parameter Statistics",
            "",
            "Numeric parameter distributions for supported operations are exported in "
            "`parameter_statistics.csv` and visualized in `parameter_histograms.png`.",
            "",
            "| Parameter | Samples |",
            "|---|---:|",
        ]
    )
    for name, values in sorted(dataset.parameters.items()):
        lines.append(f"| {name} | {len(values):,} |")

    lines.extend(
        [
            "",
            "## 11. Potential Parser Improvements",
            "",
            "Based on unsupported operation frequency, the highest-impact parser extensions are:",
            "",
        ]
    )
    for index, (name, count) in enumerate(unsupported_ops[:8], start=1):
        lines.append(f"{index}. **{name}** — observed {count:,} times in the dataset.")

    if not unsupported_ops:
        lines.append("- No unsupported PartDesign operations were detected in body feature trees.")

    lines.extend(
        [
            "",
            "## 12. Figures",
            "",
        ]
    )
    for figure in figure_names:
        lines.append(f"![{figure}]({figure})")
        lines.append("")

    lines.extend(
        [
            "## 13. Output Files",
            "",
            "- `dataset_statistics.csv` — dataset-level summary metrics",
            "- `model_statistics.csv` — per-model analysis records",
            "- `operation_distribution.csv` — operation frequency table",
            "- `geometry_distribution.csv` — sketch geometry frequency table",
            "- `constraint_distribution.csv` — sketch constraint frequency table",
            "- `parameter_statistics.csv` — extracted parameter summaries",
            "- `unsupported_operations.csv` — unsupported operation counts",
            "- `parser_failures.csv` — parser failure log",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
