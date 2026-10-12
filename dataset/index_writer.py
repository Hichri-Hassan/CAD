"""Write dataset index and duplicate reports."""

from __future__ import annotations

import csv
from pathlib import Path

from dataset.models import DatasetEntry, DuplicateGroup

INDEX_FIELDS = [
    "id",
    "original_filename",
    "repository_name",
    "original_relative_path",
    "copied_filename",
    "file_size_bytes",
    "sha256_hash",
    "is_canonical",
]

DUPLICATES_FIELDS = [
    "sha256_hash",
    "canonical_id",
    "copied_filename",
    "duplicate_count",
    "original_relative_paths",
]


def write_index_csv(path: Path, entries: list[DatasetEntry]) -> None:
    """Write the main dataset index."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_FIELDS)
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "id": entry.id,
                    "original_filename": entry.original_filename,
                    "repository_name": entry.repository_name,
                    "original_relative_path": entry.original_relative_path,
                    "copied_filename": entry.copied_filename,
                    "file_size_bytes": entry.file_size_bytes,
                    "sha256_hash": entry.sha256_hash,
                    "is_canonical": str(entry.is_canonical).lower(),
                }
            )


def write_duplicates_csv(path: Path, groups: list[DuplicateGroup]) -> None:
    """Write duplicate groups (only groups with more than one source file)."""
    duplicate_groups = [group for group in groups if group.duplicate_count > 0]
    if not duplicate_groups:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DUPLICATES_FIELDS)
        writer.writeheader()
        for group in duplicate_groups:
            paths = ";".join(entry.original_relative_path for entry in group.entries)
            writer.writerow(
                {
                    "sha256_hash": group.sha256_hash,
                    "canonical_id": group.canonical_id,
                    "copied_filename": group.copied_filename,
                    "duplicate_count": group.duplicate_count,
                    "original_relative_paths": paths,
                }
            )
