#!/usr/bin/env python3
"""Build a prompt + primitive shape dataset from generated .FCStd files."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from primitive_catalog import DEFAULT_FAMILY_ORDER, PRIMITIVE_FAMILIES, parse_shape_file


@dataclass
class ShapeRecord:
    shape_id: str
    shape_type: str
    index: int
    dimensions: dict[str, float]
    fcstd_path: str
    filename: str
    prompt: str
    prompt_index: int
    operations: list[dict] | None = None


def collect_shapes(primitives_dir: Path, project_root: Path, *, prompts_per_shape: int) -> list[ShapeRecord]:
    records: list[ShapeRecord] = []
    for path in sorted(primitives_dir.rglob("*.FCStd")):
        parsed = parse_shape_file(path, project_root=project_root)
        if parsed is None:
            continue
        prompts = parsed["prompts"][:prompts_per_shape]
        for prompt_index, prompt in enumerate(prompts):
            records.append(
                ShapeRecord(
                    shape_id=parsed["shape_id"],
                    shape_type=parsed["shape_type"],
                    index=parsed["index"],
                    dimensions=parsed["dimensions"],
                    fcstd_path=parsed["fcstd_path"],
                    filename=parsed["filename"],
                    prompt=prompt,
                    prompt_index=prompt_index,
                    operations=parsed["operations"],
                )
            )
    return records


def _group_records_by_shape(records: list[ShapeRecord]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for record in records:
        if record.shape_id not in grouped:
            grouped[record.shape_id] = {
                "shape_id": record.shape_id,
                "shape_type": record.shape_type,
                "index": record.index,
                "dimensions": record.dimensions,
                "fcstd_path": record.fcstd_path,
                "filename": record.filename,
                "operations": record.operations,
                "prompts": [],
            }
        grouped[record.shape_id]["prompts"].append(
            {"prompt_index": record.prompt_index, "prompt": record.prompt}
        )
    return [grouped[shape_id] for shape_id in sorted(grouped)]


def write_outputs(records: list[ShapeRecord], output_dir: Path, *, prompts_per_shape: int) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    shape_ids = {record.shape_id for record in records}
    by_type_shapes: dict[str, set[str]] = {family.shape_type: set() for family in PRIMITIVE_FAMILIES.values()}
    for record in records:
        by_type_shapes.setdefault(record.shape_type, set()).add(record.shape_id)
    by_type = {shape_type: len(shape_ids) for shape_type, shape_ids in by_type_shapes.items()}

    flat_examples = [
        {
            "shape_id": record.shape_id,
            "shape_type": record.shape_type,
            "index": record.index,
            "prompt_index": record.prompt_index,
            "dimensions": record.dimensions,
            "fcstd_path": record.fcstd_path,
            "filename": record.filename,
            "prompt": record.prompt,
            "operations": record.operations,
        }
        for record in records
    ]

    dataset = {
        "description": "Primitive shapes paired with multiple natural-language prompt variants",
        "shape_count": len(shape_ids),
        "prompt_count": len(records),
        "prompts_per_shape": prompts_per_shape,
        "by_type": by_type,
        "families": DEFAULT_FAMILY_ORDER,
        "shapes": _group_records_by_shape(records),
        "examples": flat_examples,
    }

    json_path = output_dir / "prompt_dataset.json"
    json_path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")

    jsonl_path = output_dir / "prompt_dataset.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for example in flat_examples:
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")

    training_path = output_dir / "primitive_training_data.jsonl"
    with training_path.open("w", encoding="utf-8") as handle:
        for record in records:
            if record.operations is None:
                continue
            handle.write(
                json.dumps(
                    {
                        "input": record.prompt,
                        "output": {"operations": record.operations},
                        "shape_id": record.shape_id,
                        "shape_type": record.shape_type,
                        "prompt_index": record.prompt_index,
                        "fcstd_path": record.fcstd_path,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    md_lines = [
        "# Primitive Shape Prompt Dataset",
        "",
        f"Total shapes: **{len(shape_ids)}**",
        f"Total prompt variants: **{len(records)}** ({prompts_per_shape} per shape)",
        "",
        "| Type | Shapes |",
        "|---|---:|",
    ]
    for family_key in DEFAULT_FAMILY_ORDER:
        shape_type = PRIMITIVE_FAMILIES[family_key].shape_type
        md_lines.append(f"| {shape_type} | {by_type.get(shape_type, 0)} |")
    md_lines.append("")

    for shape in dataset["shapes"]:
        md_lines.extend(
            [
                f"## {shape['shape_id']}",
                "",
                f"- **Type:** {shape['shape_type']}",
                f"- **File:** `{shape['fcstd_path']}`",
                f"- **Dimensions:** `{json.dumps(shape['dimensions'])}`",
                "- **Prompts:**",
            ]
        )
        for prompt_entry in shape["prompts"]:
            md_lines.append(f"  {prompt_entry['prompt_index'] + 1}. {prompt_entry['prompt']}")
        md_lines.append("")

    md_path = output_dir / "prompt_dataset.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return {
        "json": json_path,
        "jsonl": jsonl_path,
        "training_jsonl": training_path,
        "markdown": md_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate prompts for primitive shape files.")
    parser.add_argument(
        "--primitives-dir",
        type=Path,
        default=Path("output/primitives"),
        help="Directory containing primitive .FCStd files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Where to write dataset files (default: same as primitives-dir).",
    )
    parser.add_argument(
        "--prompts-per-shape",
        type=int,
        default=5,
        help="Number of prompt variants to emit per shape (default: 5).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    primitives_dir = args.primitives_dir.resolve()
    output_dir = (args.output_dir or primitives_dir).resolve()

    if not primitives_dir.exists():
        raise FileNotFoundError(f"Primitives directory not found: {primitives_dir}")

    if args.prompts_per_shape < 1:
        raise ValueError("--prompts-per-shape must be at least 1")

    records = collect_shapes(primitives_dir, project_root, prompts_per_shape=args.prompts_per_shape)
    if not records:
        raise RuntimeError(f"No .FCStd primitive files found under {primitives_dir}")

    written = write_outputs(records, output_dir, prompts_per_shape=args.prompts_per_shape)
    shape_count = len({record.shape_id for record in records})
    print(f"Wrote {len(records)} prompt variants for {shape_count} shapes:")
    for label, path in written.items():
        print(f"  {label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
