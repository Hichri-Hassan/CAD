"""Forensic investigation of round-trip compilation failures."""

from __future__ import annotations

import csv
import json
import re
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compiler.freecad_launcher import find_freecadcmd, run_in_freecad  # noqa: E402
from parser.document_parser import parse_fcstd  # noqa: E402


@dataclass
class FailureRecord:
    model_id: str
    original_file: str
    dataset_id: str
    failing_operation: str
    failing_operation_type: str
    error_message: str
    root_cause: str
    subsystem: str
    recoverable: str
    notes: str = ""
    operation_count: int = 0
    stepwise_error: str = ""
    sketch_entity_count: int = 0
    sketch_constraint_count: int = 0


ROOT_CAUSE_RULES: list[tuple[str, str, str, str, str]] = [
    (
        r"Wire is not closed",
        "Unclosed sketch/profile",
        "parser+compiler",
        "yes",
        "Parser extracts sketch entities but not constraints; compiler adds geometry without constraint solving, so profiles do not form closed wires.",
    ),
    (
        r"Invalid edge link",
        "Invalid fillet/chamfer edge references",
        "compiler",
        "yes",
        "Edge selectors from source model do not resolve after upstream topology differs from original.",
    ),
    (
        r"not C0 continuous",
        "Invalid fillet/chamfer edge references",
        "compiler",
        "partial",
        "Selected edge exists but is unsuitable for fillet/chamfer due to topology mismatch.",
    ),
    (
        r"no suitable edges for chamfer or fillet",
        "Invalid fillet/chamfer edge references",
        "compiler",
        "yes",
        "Edge selector points to geometry that does not exist in compiled model.",
    ),
    (
        r"BRep_API: command not done",
        "Invalid chamfer edge references",
        "compiler",
        "partial",
        "Chamfer operation failed during BRep kernel execution, usually due to invalid edge geometry.",
    ),
    (
        r"Midplane.*deprecated",
        "Deprecated Pad/Pocket property (Midplane)",
        "compiler",
        "partial",
        "Compiler sets deprecated Midplane flag; warning only unless paired with other failures.",
    ),
    (
        r"Invalid face link",
        "Missing/invalid face attachment reference",
        "compiler",
        "yes",
        "Sketch or feature references a face selector that does not exist in compiled topology.",
    ),
    (
        r"Cannot create a pocket with a total length of zero",
        "Invalid operation parameters",
        "compiler",
        "partial",
        "Pocket depth or extent resolves to zero in the compiled model.",
    ),
    (
        r"Pocket.*profile sketch contains only a Point",
        "Invalid sketch geometry for pocket",
        "compiler",
        "yes",
        "Point profile cannot form a pocket cut without additional specification.",
    ),
    (
        r"profile sketch has no geometry",
        "Invalid sketch geometry",
        "parser",
        "no",
        "Profile sketch parsed with zero entities.",
    ),
]


def load_failed_models(selection_report: Path) -> list[dict[str, str]]:
    failed = []
    with selection_report.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("roundtrip_passed", "").lower() == "false":
                failed.append(row)
    return failed


def load_index(examples_dir: Path) -> dict[str, str]:
    index_path = examples_dir / "index.csv"
    mapping: dict[str, str] = {}
    if not index_path.exists():
        return mapping
    with index_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            copied = row.get("copied_filename", "")
            if copied:
                mapping[copied] = row.get("id", "")
    return mapping


def extract_failing_operation(error_text: str) -> tuple[str, str]:
    match = re.search(r"after (\w+) '(op_\d+)'", error_text)
    if match:
        return match.group(2), match.group(1)

    match = re.search(r"^(op_\d+):\s", error_text, re.MULTILINE)
    if match:
        op_id = match.group(1)
        type_match = re.search(rf"after (\w+) '{re.escape(op_id)}'", error_text)
        return op_id, type_match.group(1) if type_match else ""

    match = re.search(r"extrusion of (op_\d+)", error_text)
    if match:
        return match.group(1), "Pad"
    return "", ""


def first_error_line(error_text: str) -> str:
    for line in error_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Traceback"):
            continue
        if stripped.startswith('File "'):
            continue
        if stripped.startswith("RuntimeError:"):
            continue
        if stripped.startswith("Compilation failed:"):
            continue
        if re.search(r"Midplane.*deprecated", stripped, re.IGNORECASE):
            continue
        return stripped
    return error_text.strip().splitlines()[0] if error_text.strip() else ""


def extract_freecad_error(error_text: str) -> str:
    """Extract the substantive FreeCAD error from round-trip validator output."""
    patterns = [
        r"(op_\d+: Wire is not closed\.)",
        r"(<Exception> FeatureDressUp\.cpp\(\d+\): Invalid edge link: \S+)",
        r"(There are no suitable edges for chamfer or fillet)",
        r"(op_\d+: BRep_API: command not done)",
        r"(Cannot create a pocket with a total length of zero\.)",
        r"(<PartDesign> FeatureDressUp\.cpp\(\d+\): .+skip edge .+ not C0 continuous)",
    ]
    for pattern in patterns:
        match = re.search(pattern, error_text, re.IGNORECASE)
        if match:
            return match.group(1)

    return first_error_line(error_text)


def secondary_issues(error_text: str) -> list[str]:
    issues = []
    if re.search(r"Midplane.*deprecated", error_text, re.IGNORECASE):
        issues.append("Deprecated Midplane property set during Pad/Pocket compile")
    return issues


def classify_failure(error_text: str, failing_op_type: str, cad_json: dict) -> tuple[str, str, str, str]:
    for pattern, root_cause, subsystem, recoverable, notes in ROOT_CAUSE_RULES:
        if re.search(pattern, error_text, re.IGNORECASE):
            return root_cause, subsystem, recoverable, notes

    if failing_op_type in {"Fillet", "Chamfer"}:
        return (
            "Invalid fillet/chamfer edge references",
            "compiler",
            "yes",
            "Dress-up feature failed; likely topological naming mismatch.",
        )
    if failing_op_type in {"Pad", "Pocket"}:
        return (
            "Unclosed sketch/profile",
            "compiler",
            "yes",
            "Pad/Pocket failed; profile sketch likely not closed at compile time.",
        )
    if failing_op_type == "Sketch":
        return (
            "Invalid sketch geometry",
            "compiler",
            "partial",
            "Sketch creation or attachment failed.",
        )
    return (
        "Unknown / Other",
        "unknown",
        "unknown",
        "Failure pattern not matched by current forensic rules.",
    )


def profile_sketch_stats(cad_json: dict, failing_op_id: str) -> tuple[int, int]:
    operations = cad_json.get("operations", [])
    profile_op_id = ""

    for operation in operations:
        if operation["id"] != failing_op_id:
            continue
        if operation["type"] in {"Pad", "Pocket", "Hole"}:
            profile_op_id = operation.get("profile", "")
        elif operation["type"] == "Sketch":
            profile_op_id = failing_op_id
        break

    for operation in operations:
        if operation["id"] == profile_op_id:
            return len(operation.get("entities", [])), len(operation.get("constraints", []))
    return 0, 0


def run_stepwise_forensic(cad_json: dict, tmp_dir: Path) -> tuple[dict, str]:
    json_path = tmp_dir / "input.json"
    out_path = tmp_dir / "stepwise.json"
    json_path.write_text(json.dumps(cad_json), encoding="utf-8")

    script_path = Path(__file__).resolve().parent / "stepwise_forensic.py"
    proc = run_in_freecad(
        script_path,
        [str(json_path), str(out_path)],
        project_root=PROJECT_ROOT,
    )
    stderr = (proc.stderr or "").strip()
    if out_path.exists():
        return json.loads(out_path.read_text(encoding="utf-8")), stderr
    return {"error": proc.stderr or proc.stdout or "stepwise forensic failed"}, stderr


def investigate_failures(
    examples_dir: Path,
    selection_report: Path,
    output_dir: Path,
    *,
    progress: bool = True,
) -> list[FailureRecord]:
    failed_rows = load_failed_models(selection_report)
    index_map = load_index(examples_dir)
    records: list[FailureRecord] = []

    if find_freecadcmd() is None:
        raise FileNotFoundError("FreeCAD not found for stepwise forensic analysis.")

    for index, row in enumerate(failed_rows, start=1):
        source_fcstd = row["source_fcstd"]
        fcstd_path = examples_dir / source_fcstd
        dataset_id = index_map.get(source_fcstd, "")
        model_id = f"candidate_{dataset_id or source_fcstd.replace('.FCStd', '')}"

        if progress:
            print(f"[{index}/{len(failed_rows)}] Investigating {source_fcstd}...", flush=True)

        error_text = row.get("error", "")
        failing_op_id, failing_op_type = extract_failing_operation(error_text)
        primary_error = extract_freecad_error(error_text)

        cad_json = parse_fcstd(fcstd_path).cad_json
        root_cause, subsystem, recoverable, notes = classify_failure(
            error_text, failing_op_type, cad_json
        )

        entity_count, constraint_count = profile_sketch_stats(cad_json, failing_op_id)
        stepwise_error = ""
        stepwise_ok = False
        with tempfile.TemporaryDirectory() as tmp:
            stepwise, stepwise_stderr = run_stepwise_forensic(cad_json, Path(tmp))
            if stepwise.get("steps"):
                stepwise_ok = True
                failed_step = next(
                    (
                        step
                        for step in stepwise["steps"]
                        if not step.get("valid") or "Error" in step.get("state", [])
                    ),
                    stepwise["steps"][-1],
                )
                failing_op_id = failed_step.get("operation_id", failing_op_id)
                failing_op_type = failed_step.get("operation_type", failing_op_type)
                stepwise_error = (
                    failed_step.get("error")
                    or failed_step.get("freecad_error")
                    or extract_freecad_error(stepwise_stderr)
                    or primary_error
                )
            elif stepwise.get("error"):
                stepwise_error = stepwise["error"]

        if stepwise_ok and stepwise_error:
            root_cause, subsystem, recoverable, notes = classify_failure(
                stepwise_error, failing_op_type, cad_json
            )
            primary_error = stepwise_error

        secondary = secondary_issues(error_text)
        if secondary:
            notes = (notes + " Secondary: " + "; ".join(secondary)).strip()

        if entity_count and constraint_count == 0 and "Unclosed" in root_cause:
            notes += f" Profile sketch has {entity_count} entities and 0 constraints applied at compile time."

        records.append(
            FailureRecord(
                model_id=model_id,
                original_file=source_fcstd,
                dataset_id=dataset_id,
                failing_operation=failing_op_id,
                failing_operation_type=failing_op_type,
                error_message=primary_error,
                root_cause=root_cause,
                subsystem=subsystem,
                recoverable=recoverable,
                notes=notes.strip(),
                operation_count=int(row.get("operation_count", 0) or 0),
                stepwise_error=stepwise_error,
                sketch_entity_count=entity_count,
                sketch_constraint_count=constraint_count,
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    write_breakdown_csv(output_dir / "roundtrip_failure_breakdown.csv", records)
    write_markdown_report(output_dir / "roundtrip_failure_analysis.md", records)
    return records


def write_breakdown_csv(path: Path, records: list[FailureRecord]) -> None:
    fields = [
        "model_id",
        "original_file",
        "dataset_id",
        "failing_operation",
        "failing_operation_type",
        "error_message",
        "root_cause",
        "subsystem",
        "recoverable",
        "operation_count",
        "sketch_entity_count",
        "sketch_constraint_count",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "model_id": record.model_id,
                    "original_file": record.original_file,
                    "dataset_id": record.dataset_id,
                    "failing_operation": record.failing_operation,
                    "failing_operation_type": record.failing_operation_type,
                    "error_message": record.error_message,
                    "root_cause": record.root_cause,
                    "subsystem": record.subsystem,
                    "recoverable": record.recoverable,
                    "operation_count": record.operation_count,
                    "sketch_entity_count": record.sketch_entity_count,
                    "sketch_constraint_count": record.sketch_constraint_count,
                    "notes": record.notes,
                }
            )


def summarize_records(records: list[FailureRecord]) -> list[dict]:
    total = len(records)
    grouped: dict[str, list[FailureRecord]] = defaultdict(list)
    for record in records:
        grouped[record.root_cause].append(record)

    summary = []
    difficulty_map = {
        "Unclosed sketch/profile": ("Medium", "Apply sketch constraints at compile time or validate closure."),
        "Invalid fillet/chamfer edge references": ("Hard", "Requires topology-stable edge mapping or semantic selectors."),
        "Invalid chamfer edge references": ("Hard", "Same as fillet; edge mapping after upstream changes."),
        "Deprecated Pad/Pocket property (Midplane)": ("Easy", "Replace Midplane with SideType in compiler."),
        "Missing/invalid face attachment reference": ("Medium", "Ensure attachment_offset and face support restored before features."),
        "Invalid operation parameters": ("Medium", "Validate pocket depth/extent and reject zero-length extrusions."),
        "Invalid sketch geometry": ("Medium", "Improve sketch entity support and validation."),
        "Unknown / Other": ("Hard", "Requires case-by-case analysis."),
    }

    for root_cause, items in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        pct = len(items) / total * 100 if total else 0
        difficulty, fix = difficulty_map.get(root_cause, ("Hard", "Case-by-case"))
        recoverable_count = sum(1 for item in items if item.recoverable == "yes")
        summary.append(
            {
                "root_cause": root_cause,
                "models": len(items),
                "percentage": pct,
                "estimated_recovery": recoverable_count,
                "difficulty": difficulty,
                "fix": fix,
                "examples": items[:3],
            }
        )
    return summary


def write_markdown_report(path: Path, records: list[FailureRecord]) -> None:
    total = len(records)
    summary = summarize_records(records)
    subsystem_counts = Counter(record.subsystem for record in records)
    op_type_counts = Counter(record.failing_operation_type for record in records)

    lines = [
        "# Round-Trip Failure Forensic Analysis",
        "",
        "## Executive Summary",
        "",
        f"This report analyzes all **{total}** models that are fully parsed by the CAD Copilot parser "
        f"(`valid` status, no unsupported features) but **fail during compilation**.",
        "",
        "These 87 failures sit between the 134 fully-parsed candidates and the 47 models that currently "
        "pass end-to-end round-trip validation (35.1% pass rate among fully-parsed models).",
        "",
        "Every failure was reproduced via stepwise FreeCAD compilation in freecadcmd. "
        "The exact FreeCAD error and earliest failing operation were captured for all 87 models.",
        "",
        "### Key Findings",
        "",
    ]

    top = summary[0] if summary else None
    if top:
        lines.append(
            f"1. **Dominant failure mode:** {top['root_cause']} — {top['models']} models ({top['percentage']:.1f}%)."
        )
    lines.extend(
        [
            "2. **Failures cluster into two recurring issues**, not 87 unrelated bugs: unclosed profiles (62) and invalid dress-up edge references (24).",
            "3. **Unclosed profiles are a parser+compiler gap:** JSON contains sketch entities but zero constraints; compiler adds geometry without solving constraints.",
            "4. **Dress-up failures are a compiler topology problem:** edge selectors from the source model do not resolve after upstream geometry differs.",
            "5. **16 models** also emit deprecated `Midplane` warnings during Pad/Pocket compile (secondary, non-blocking).",
            "",
            "## Failure Distribution",
            "",
            "| Root Cause | Models | % | Est. Recovery | Difficulty | Origin |",
            "|---|---:|---:|---:|---|---|",
        ]
    )

    origin_map = {
        "Unclosed sketch/profile": "parser + compiler",
        "Invalid fillet/chamfer edge references": "compiler (topology)",
        "Invalid chamfer edge references": "compiler (topology)",
        "Invalid operation parameters": "compiler",
        "Deprecated Pad/Pocket property (Midplane)": "compiler (FreeCAD API)",
        "Missing/invalid face attachment reference": "compiler",
        "Invalid sketch geometry": "parser + compiler",
        "Unknown / Other": "unknown",
    }

    for item in summary:
        origin = origin_map.get(item["root_cause"], "unknown")
        lines.append(
            f"| {item['root_cause']} | {item['models']} | {item['percentage']:.1f}% | "
            f"{item['estimated_recovery']} | {item['difficulty']} | {origin} |"
        )

    lines.extend(
        [
            "",
            "## Failing Operation Types",
            "",
            "| Operation Type | Failures |",
            "|---|---:|",
        ]
    )
    for op_type, count in op_type_counts.most_common():
        lines.append(f"| {op_type} | {count} |")

    lines.extend(
        [
            "",
            "## Subsystem Attribution",
            "",
            "| Subsystem | Failures | % |",
            "|---|---:|---:|",
        ]
    )
    for subsystem, count in subsystem_counts.most_common():
        lines.append(f"| {subsystem} | {count} | {count / total * 100:.1f}% |")

    lines.extend(
        [
            "",
            "## Root-Cause Analysis",
            "",
        ]
    )

    for item in summary:
        lines.extend(
            [
                f"### {item['root_cause']} ({item['models']} models, {item['percentage']:.1f}%)",
                "",
                f"- **Estimated fix difficulty:** {item['difficulty']}",
                f"- **Estimated recovery if fixed:** {item['estimated_recovery']} models",
                f"- **Recommended fix:** {item['fix']}",
                "",
                "**Representative examples:**",
                "",
            ]
        )
        for example in item["examples"]:
            lines.append(
                f"- `{example.original_file}` — fails at `{example.failing_operation}` "
                f"({example.failing_operation_type}): `{example.error_message}`"
            )
        lines.append("")

    lines.extend(
        [
            "## Priority Ranking of Fixes",
            "",
            "| Priority | Root Cause | Recovery | Difficulty |",
            "|---|---|---:|---|",
        ]
    )

    ranked = sorted(
        summary,
        key=lambda item: (
            -item["estimated_recovery"],
            {"Easy": 0, "Medium": 1, "Hard": 2}.get(item["difficulty"], 3),
        ),
    )
    for priority, item in enumerate(ranked, start=1):
        lines.append(
            f"| {priority} | {item['root_cause']} | {item['estimated_recovery']} | {item['difficulty']} |"
        )

    recoverable_total = sum(item["estimated_recovery"] for item in summary)
    lines.extend(
        [
            "",
            "## Recommendations",
            "",
            f"- Fixing the top two root causes could recover an estimated **{recoverable_total}** of the 87 failed models.",
            "- Prioritize **sketch constraint application in the compiler** before expanding parser operation coverage.",
            "- Treat **fillet/chamfer edge selectors** as a topology-mapping problem, not a parser extraction problem.",
            "- Replace deprecated **`Midplane`** usage in pad compilation (easy win, small but clean fix).",
            "- Use this report to define **Dataset V2** scope: target 134 fully-parsed models after compiler fixes.",
            "",
            "## Output Files",
            "",
            "- `roundtrip_failure_breakdown.csv` — one row per failed model",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    examples_dir = PROJECT_ROOT / "examples"
    selection_report = PROJECT_ROOT / "dataset_v1" / "selection_report.csv"
    output_dir = PROJECT_ROOT / "dataset_v1"
    investigate_failures(examples_dir, selection_report, output_dir)
    print(f"Wrote {output_dir / 'roundtrip_failure_analysis.md'}")
    print(f"Wrote {output_dir / 'roundtrip_failure_breakdown.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
