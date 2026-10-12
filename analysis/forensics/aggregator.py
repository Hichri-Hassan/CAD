"""Aggregate forensic dataset statistics."""

from __future__ import annotations

from collections import Counter

from analysis.forensics.models import DocumentForensics, ForensicDataset


def aggregate_forensics(documents: list[DocumentForensics]) -> ForensicDataset:
    dataset = ForensicDataset(documents=documents)

    for doc in documents:
        dataset.category_counts[doc.primary_category] = (
            dataset.category_counts.get(doc.primary_category, 0) + 1
        )

        if doc.parse_success:
            dataset.failure_reason_counts["Parsed successfully"] = (
                dataset.failure_reason_counts.get("Parsed successfully", 0) + 1
            )
        else:
            reason = doc.failure_reason or "Unknown"
            dataset.failure_reason_counts[reason] = dataset.failure_reason_counts.get(reason, 0) + 1

        for type_id, count in doc.type_counts.items():
            dataset.type_id_counts[type_id] = dataset.type_id_counts.get(type_id, 0) + count

    return dataset


def top_counts(counter: dict[str, int], limit: int = 20) -> list[tuple[str, int]]:
    return Counter(counter).most_common(limit)
