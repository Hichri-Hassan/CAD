"""Orchestrate repository extraction into a flat dataset folder."""

from __future__ import annotations

import shutil
from collections import defaultdict
from pathlib import Path

from dataset.hasher import attach_hashes
from dataset.index_writer import write_duplicates_csv, write_index_csv
from dataset.models import DatasetEntry, DuplicateGroup, ExtractionSummary, SourceFile
from dataset.scanner import scan_fcstd_files


def format_dataset_id(sequence_number: int, width: int = 6) -> str:
    """Format a sequential dataset ID such as 000001."""
    return f"{sequence_number:0{width}d}"


def format_copied_filename(sequence_number: int, width: int = 6) -> str:
    """Format a copied FCStd filename such as 000001.FCStd."""
    return f"{format_dataset_id(sequence_number, width)}.FCStd"


def build_dataset_entries(
    files: list[SourceFile],
    id_width: int = 6,
) -> tuple[list[DatasetEntry], list[DuplicateGroup]]:
    """Assign dataset IDs, group duplicates, and build index rows."""
    by_hash: dict[str, list[SourceFile]] = defaultdict(list)
    for source in files:
        by_hash[source.sha256_hash].append(source)

    # Deterministic ordering: canonical file is first by relative path per hash group.
    hash_groups: list[tuple[str, list[SourceFile]]] = sorted(
        by_hash.items(),
        key=lambda item: sorted(item[1], key=lambda f: f.relative_path)[0].relative_path,
    )

    entries: list[DatasetEntry] = []
    duplicate_groups: list[DuplicateGroup] = []

    for sequence_number, (file_hash, group_files) in enumerate(hash_groups, start=1):
        ordered = sorted(group_files, key=lambda f: f.relative_path)
        dataset_id = format_dataset_id(sequence_number, id_width)
        copied_filename = format_copied_filename(sequence_number, id_width)

        group_entries: list[DatasetEntry] = []
        for index, source in enumerate(ordered):
            entry = DatasetEntry(
                id=dataset_id,
                original_filename=source.original_filename,
                repository_name=source.repository_name,
                original_relative_path=source.relative_path,
                copied_filename=copied_filename,
                file_size_bytes=source.file_size_bytes,
                sha256_hash=file_hash,
                is_canonical=index == 0,
            )
            group_entries.append(entry)
            entries.append(entry)

        duplicate_groups.append(
            DuplicateGroup(
                sha256_hash=file_hash,
                canonical_id=dataset_id,
                copied_filename=copied_filename,
                entries=group_entries,
            )
        )

    # Stable index order: repository path order of every discovered file.
    entries.sort(key=lambda e: (e.repository_name, e.original_relative_path))
    return entries, duplicate_groups


def copy_canonical_files(
    files: list[SourceFile],
    entries: list[DatasetEntry],
    output_dir: Path,
) -> int:
    """Copy one file per unique hash into output_dir. Returns copy count."""
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical_by_hash = {
        entry.sha256_hash: entry
        for entry in entries
        if entry.is_canonical
    }
    source_by_path = {source.relative_path: source for source in files}

    copied = 0
    for entry in canonical_by_hash.values():
        source = source_by_path[entry.original_relative_path]
        destination = output_dir / entry.copied_filename
        shutil.copy2(source.absolute_path, destination)
        copied += 1

    return copied


def print_summary(summary: ExtractionSummary) -> None:
    """Print a human-readable extraction summary."""
    print("----------------------------------------")
    print(f"Repository scanned : {summary.repository_name}")
    print(f"Repository path    : {summary.repository_path}")
    print(f"Output directory   : {summary.output_dir}")
    print(f"FCStd files found  : {summary.files_found}")
    print(f"Unique models      : {summary.unique_models}")
    print(f"Duplicate models   : {summary.duplicate_models}")
    print(f"Copied             : {summary.copied}")
    print(f"Index generated    : {summary.index_path}")
    if summary.duplicates_path:
        print(f"Duplicates report  : {summary.duplicates_path}")
    print("----------------------------------------")


def extract_repository(
    repository_path: Path | str,
    output_dir: Path | str,
    repository_name: str | None = None,
    id_width: int = 6,
    progress: bool = True,
) -> ExtractionSummary:
    """Extract all .FCStd files from a repository into a flat dataset folder."""
    repository_path = Path(repository_path).resolve()
    output_dir = Path(output_dir).resolve()
    repository_name = repository_name or repository_path.name

    if progress:
        print(f"Scanning repository: {repository_path}")

    files = scan_fcstd_files(repository_path, repository_name)
    if not files:
        raise FileNotFoundError(f"No .FCStd files found under {repository_path}")

    if progress:
        print(f"Found {len(files)} .FCStd files. Computing SHA-256 hashes...")

    files = attach_hashes(files, progress=progress)

    if progress:
        print("Building dataset index and resolving duplicates...")

    entries, duplicate_groups = build_dataset_entries(files, id_width=id_width)

    if progress:
        print(f"Copying {sum(1 for e in entries if e.is_canonical)} unique files to {output_dir}...")

    copied = copy_canonical_files(files, entries, output_dir)

    index_path = output_dir / "index.csv"
    duplicates_path = output_dir / "duplicates.csv"
    write_index_csv(index_path, entries)
    write_duplicates_csv(duplicates_path, duplicate_groups)

    unique_models = sum(1 for group in duplicate_groups if group.entries)
    duplicate_models = len(files) - unique_models
    has_duplicates = any(group.duplicate_count > 0 for group in duplicate_groups)

    summary = ExtractionSummary(
        repository_name=repository_name,
        repository_path=str(repository_path),
        output_dir=str(output_dir),
        files_found=len(files),
        unique_models=unique_models,
        duplicate_models=duplicate_models,
        copied=copied,
        index_path=str(index_path),
        duplicates_path=str(duplicates_path) if has_duplicates else None,
    )

    print_summary(summary)
    return summary
