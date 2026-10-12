"""Run forensic classification over the dataset."""

from __future__ import annotations

from pathlib import Path

from analysis.forensics.aggregator import aggregate_forensics
from analysis.forensics.classifier import classify_document
from analysis.forensics.document_inspector import inspect_document
from analysis.forensics.exporters import export_all_forensic_csv
from analysis.forensics.failure_analyzer import attach_parser_status
from analysis.forensics.report import generate_classification_summary
from analysis.runner import discover_models, load_index_metadata


def run_forensic_analysis(
    examples_dir: Path | str,
    output_dir: Path | str,
    *,
    limit: int | None = None,
    progress: bool = True,
) -> None:
    """Classify every FCStd file and explain parser coverage."""
    examples_dir = Path(examples_dir).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model_paths = discover_models(examples_dir)
    if limit is not None:
        model_paths = model_paths[:limit]

    if not model_paths:
        raise FileNotFoundError(f"No .FCStd files found in {examples_dir}")

    index_meta = load_index_metadata(examples_dir)
    documents = []
    total = len(model_paths)

    if progress:
        print(f"Forensic inspection of {total} models from {examples_dir}")

    for index, path in enumerate(model_paths, start=1):
        meta = index_meta.get(path.name, {})
        doc = inspect_document(
            path,
            dataset_id=meta.get("dataset_id", ""),
            repository=meta.get("repository", ""),
            original_relative_path=meta.get("original_relative_path", ""),
        )
        doc = classify_document(doc)
        doc = attach_parser_status(doc, str(path))
        documents.append(doc)

        if progress and (index == 1 or index % 100 == 0 or index == total):
            print(f"  Progress: {index}/{total}", flush=True)

    if progress:
        print("Aggregating forensic statistics...")

    dataset = aggregate_forensics(documents)

    if progress:
        print("Writing CSV outputs...")

    export_all_forensic_csv(output_dir, dataset)

    if progress:
        print("Writing classification summary...")

    report_path = generate_classification_summary(output_dir, dataset)

    parsed = sum(1 for doc in documents if doc.parse_success)
    if progress:
        print("----------------------------------------")
        print(f"Models inspected      : {total}")
        print(f"Parser success          : {parsed} ({parsed / total * 100:.1f}%)")
        print(f"With PartDesign::Body   : {sum(1 for d in documents if d.has_partdesign_body)}")
        print(f"Body named 'Body'       : {sum(1 for d in documents if d.has_body_named_body)}")
        print(f"Output directory        : {output_dir}")
        print(f"Classification report   : {report_path}")
        print("----------------------------------------")
