"""Export forensic analysis CSV outputs."""

from __future__ import annotations

import csv
from pathlib import Path

from analysis.forensics.models import DocumentForensics, ForensicDataset


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_document_classification(path: Path, documents: list[DocumentForensics]) -> None:
    fields = [
        "filename",
        "dataset_id",
        "repository",
        "file_size_bytes",
        "category",
        "categories",
        "number_of_bodies",
        "number_of_sketches",
        "number_of_partdesign_features",
        "top_level_object_types",
        "parser_status",
        "parse_success",
        "failure_reason",
        "has_partdesign_body",
        "has_body_named_body",
    ]
    rows = []
    for doc in documents:
        rows.append(
            {
                "filename": doc.filename,
                "dataset_id": doc.dataset_id,
                "repository": doc.repository,
                "file_size_bytes": doc.file_size_bytes,
                "category": doc.primary_category,
                "categories": "|".join(doc.categories),
                "number_of_bodies": doc.body_count,
                "number_of_sketches": doc.sketch_count,
                "number_of_partdesign_features": doc.partdesign_feature_count,
                "top_level_object_types": ";".join(doc.top_level_object_types[:20]),
                "parser_status": doc.parser_status,
                "parse_success": str(doc.parse_success).lower(),
                "failure_reason": doc.failure_reason,
                "has_partdesign_body": str(doc.has_partdesign_body).lower(),
                "has_body_named_body": str(doc.has_body_named_body).lower(),
            }
        )
    _write_csv(path, fields, rows)


def export_failure_reason_distribution(path: Path, dataset: ForensicDataset) -> None:
    total = sum(dataset.failure_reason_counts.values())
    rows = []
    for reason, count in sorted(
        dataset.failure_reason_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        pct = count / total * 100 if total else 0
        rows.append({"failure_reason": reason, "count": count, "percentage": round(pct, 4)})
    _write_csv(path, ["failure_reason", "count", "percentage"], rows)


def export_object_type_distribution(path: Path, dataset: ForensicDataset) -> None:
    total = sum(dataset.type_id_counts.values())
    rows = []
    for type_id, count in sorted(
        dataset.type_id_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        pct = count / total * 100 if total else 0
        rows.append({"type_id": type_id, "count": count, "percentage": round(pct, 4)})
    _write_csv(path, ["type_id", "count", "percentage"], rows)


def export_body_statistics(path: Path, documents: list[DocumentForensics]) -> None:
    fields = [
        "filename",
        "dataset_id",
        "body_name",
        "body_label",
        "feature_count",
        "feature_tree_depth",
        "sketch_count",
        "tip",
        "feature_types",
    ]
    rows = []
    for doc in documents:
        if not doc.bodies:
            rows.append(
                {
                    "filename": doc.filename,
                    "dataset_id": doc.dataset_id,
                    "body_name": "",
                    "body_label": "",
                    "feature_count": 0,
                    "feature_tree_depth": 0,
                    "sketch_count": 0,
                    "tip": "",
                    "feature_types": "",
                }
            )
            continue
        for body in doc.bodies:
            type_summary = ";".join(f"{k}:{v}" for k, v in sorted(body.feature_types.items()))
            rows.append(
                {
                    "filename": doc.filename,
                    "dataset_id": doc.dataset_id,
                    "body_name": body.name,
                    "body_label": body.label,
                    "feature_count": body.feature_count,
                    "feature_tree_depth": body.depth,
                    "sketch_count": body.sketch_count,
                    "tip": body.tip,
                    "feature_types": type_summary,
                }
            )
    _write_csv(path, fields, rows)


def export_all_forensic_csv(output_dir: Path, dataset: ForensicDataset) -> None:
    export_document_classification(output_dir / "document_classification.csv", dataset.documents)
    export_failure_reason_distribution(output_dir / "failure_reason_distribution.csv", dataset)
    export_object_type_distribution(output_dir / "object_type_distribution.csv", dataset)
    export_body_statistics(output_dir / "body_statistics.csv", dataset.documents)
