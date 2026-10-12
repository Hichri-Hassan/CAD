"""Generate classification_summary.md forensic report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from analysis.forensics.aggregator import top_counts
from analysis.forensics.models import ForensicDataset


def _pct(part: int, whole: int) -> str:
    if whole == 0:
        return "0.0%"
    return f"{part / whole * 100:.1f}%"


def generate_classification_summary(output_dir: Path, dataset: ForensicDataset) -> Path:
    total = len(dataset.documents)
    parsed = sum(1 for doc in dataset.documents if doc.parse_success)
    has_body = sum(1 for doc in dataset.documents if doc.has_partdesign_body)
    multi_body = sum(1 for doc in dataset.documents if doc.body_count > 1)
    named_body = sum(1 for doc in dataset.documents if doc.has_body_named_body)
    assembly = sum(1 for doc in dataset.documents if doc.primary_category == "Assembly")
    assembly_tagged = sum(1 for doc in dataset.documents if "Assembly" in doc.categories)
    part_wb = sum(1 for doc in dataset.documents if "Part Workbench Model" in doc.categories)
    imported = sum(1 for doc in dataset.documents if "Imported STEP/BREP" in doc.categories)
    partdesign_single = sum(1 for doc in dataset.documents if doc.primary_category == "PartDesign Part")

    failure_items = [
        (reason, count)
        for reason, count in top_counts(dataset.failure_reason_counts, 30)
        if reason != "Parsed successfully"
    ]
    parsed_success_count = dataset.failure_reason_counts.get("Parsed successfully", parsed)

    lines = [
        "# Forensic Dataset Classification Report",
        "",
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "## Executive Summary",
        "",
        "This report explains **why the current CAD Copilot parser succeeds on only "
        f"{_pct(parsed, total)}** of the collected FreeCAD-library dataset. "
        "The analysis inspects raw `Document.xml` structure for every `.FCStd` file "
        "without modifying the parser.",
        "",
        f"- **Total models:** {total:,}",
        f"- **Parser success (≥1 operation extracted):** {parsed:,} ({_pct(parsed, total)})",
        f"- **Parser failures:** {total - parsed:,} ({_pct(total - parsed, total)})",
        "",
        "### Key Finding",
        "",
        "The low parser coverage is **primarily a dataset heterogeneity problem**, not a "
        "large-scale parser bug. Most files were never authored as single-body PartDesign "
        "documents matching the parser's assumptions.",
        "",
        "## 1. Dataset Composition",
        "",
        "| Document Category | Count | Percentage |",
        "|---|---:|---:|",
    ]

    for category, count in sorted(dataset.category_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {category} | {count:,} | {_pct(count, total)} |")

    lines.extend(
        [
            "",
            "## 2. Distribution of FreeCAD Object Types",
            "",
            "Complete inventory: `object_type_distribution.csv`. Top types:",
            "",
            "| TypeId | Count |",
            "|---|---:|",
        ]
    )
    for type_id, count in top_counts(dataset.type_id_counts, 20):
        lines.append(f"| `{type_id}` | {count:,} |")

    lines.extend(
        [
            "",
            "## 3. Why the Parser Fails",
            "",
            "| Failure Reason | Count | Percentage |",
            "|---|---:|---:|",
        ]
    )
    failure_total = sum(count for _, count in failure_items)
    for reason, count in failure_items:
        lines.append(f"| {reason} | {count:,} | {_pct(count, total)} |")

    lines.extend(
        [
            "",
            "## 4. Structural Metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Files with any PartDesign::Body | {has_body:,} ({_pct(has_body, total)}) |",
            f"| Files with exactly one body (PartDesign Part category) | {partdesign_single:,} ({_pct(partdesign_single, total)}) |",
            f"| Files with body literally named `Body` | {named_body:,} ({_pct(named_body, total)}) |",
            f"| Files with multiple PartDesign bodies | {multi_body:,} ({_pct(multi_body, total)}) |",
            f"| Assembly-classified files (primary) | {assembly:,} ({_pct(assembly, total)}) |",
            f"| Files also tagged Assembly (incl. multi-body) | {assembly_tagged:,} ({_pct(assembly_tagged, total)}) |",
            f"| Part Workbench models (no PartDesign body) | {part_wb:,} ({_pct(part_wb, total)}) |",
            f"| Imported STEP/BREP style files | {imported:,} ({_pct(imported, total)}) |",
            "",
            "## 5. Answering the Coverage Questions",
            "",
            "### Are most failures caused by unsupported operations?",
            "",
        ]
    )

    unsupported_count = dataset.failure_reason_counts.get("Unsupported PartDesign feature", 0)
    no_body_count = dataset.failure_reason_counts.get("No PartDesign Body", 0)
    part_wb_count = dataset.failure_reason_counts.get("Part Workbench instead of PartDesign", 0)
    multi_count = dataset.failure_reason_counts.get("Multiple PartDesign Bodies", 0)
    naming_count = dataset.failure_reason_counts.get("PartDesign Body not named 'Body'", 0)

    lines.extend(
        [
            f"**No.** Only **{unsupported_count:,}** files ({_pct(unsupported_count, total)}) fail "
            f"because of unsupported PartDesign features inside an otherwise valid body tree. "
            f"The largest single cause is **No PartDesign Body** ({no_body_count:,} files, "
            f"{_pct(no_body_count, total)}), followed by **Part Workbench instead of PartDesign** "
            f"({part_wb_count:,} files, {_pct(part_wb_count, total)}).",
            "",
            "### Are many files not PartDesign documents?",
            "",
            f"**Yes.** **{total - has_body:,}** files ({_pct(total - has_body, total)}) contain "
            "no `PartDesign::Body` at all. These are predominantly Part workbench models built "
            "from `Part::Extrusion`, `Sketcher::SketchObject`, and grouped feature trees.",
            "",
            "### Are many files assemblies?",
            "",
            f"**Some, but not the dominant failure mode.** **{assembly:,}** files ({_pct(assembly, total)}) "
            "are classified as assemblies. Multi-body PartDesign files add another "
            f"**{multi_body:,}** ({_pct(multi_body, total)}).",
            "",
            "### Does the parser fail because multiple bodies are present?",
            "",
            f"**Partially.** **{multi_count:,}** files ({_pct(multi_count, total)}) contain multiple "
            f"`PartDesign::Body` objects. Additionally, **{naming_count:,}** files ({_pct(naming_count, total)}) "
            "have a PartDesign body that is not named `Body`, which the current parser does not read.",
            "",
            "### Is the dataset heterogeneous?",
            "",
            "**Yes.** The FreeCAD-library collection mixes PartDesign parametric models, Part workbench "
            "history trees, multi-body templates, architectural BIM objects, imported solids, and "
            "grouped sub-assemblies. The parser was designed for single-body PartDesign feature trees.",
            "",
            "## 6. Parser Assumptions vs Dataset Reality",
            "",
            "The current parser (`parser/fcstd_reader.py`) assumes:",
            "",
            "1. A PartDesign object named exactly `Body` exists.",
            "2. Features are stored in that body's `Group` property in order.",
            "3. Feature types belong to a small supported subset (Sketch, Pad, Pocket, Hole, Fillet, Chamfer).",
            "",
            "Forensic inspection shows:",
            "",
            f"- Only **{named_body:,}/{total:,}** files ({_pct(named_body, total)}) have a body named `Body`.",
            f"- Only **{has_body:,}/{total:,}** files ({_pct(has_body, total)}) contain any PartDesign body.",
            f"- Only **{parsed:,}/{total:,}** files ({_pct(parsed, total)}) yield extractable operations under these assumptions.",
            "",
            "## 7. Recommendations",
            "",
            "1. **Filter the training corpus** to single-body PartDesign files (`PartDesign Part` category) "
            f"for initial model development — approximately **{partdesign_single:,}** candidates.",
            "2. **Extend body discovery** to enumerate all `PartDesign::Body` objects by type, not by name `Body`.",
            "3. **Prioritize parser extensions** based on `unsupported_operations.csv`: Groove, Polar Pattern, Mirror, Revolution.",
            "4. **Treat Part workbench files separately** — they require a different extraction pipeline, not PartDesign parsing.",
            "5. **Do not expect 100% coverage** on FreeCAD-library without supporting multiple workbenches.",
            "",
            "## 8. Output Files",
            "",
            "- `document_classification.csv` — per-file category and parser status",
            "- `failure_reason_distribution.csv` — aggregated failure reasons",
            "- `object_type_distribution.csv` — complete TypeId inventory",
            "- `body_statistics.csv` — per-body feature counts and depth",
            "",
        ]
    )

    report_path = output_dir / "classification_summary.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
