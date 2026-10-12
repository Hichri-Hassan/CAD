"""Data models for dataset extraction."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceFile:
    """A discovered .FCStd file inside a repository."""

    absolute_path: str
    repository_name: str
    relative_path: str
    original_filename: str
    file_size_bytes: int
    sha256_hash: str = ""


@dataclass
class DatasetEntry:
    """One row in the dataset index (one per discovered source file)."""

    id: str
    original_filename: str
    repository_name: str
    original_relative_path: str
    copied_filename: str
    file_size_bytes: int
    sha256_hash: str
    is_canonical: bool


@dataclass
class DuplicateGroup:
    """A set of source files sharing identical content."""

    sha256_hash: str
    canonical_id: str
    copied_filename: str
    entries: list[DatasetEntry] = field(default_factory=list)

    @property
    def duplicate_count(self) -> int:
        return max(0, len(self.entries) - 1)


@dataclass
class ExtractionSummary:
    """High-level statistics from an extraction run."""

    repository_name: str
    repository_path: str
    output_dir: str
    files_found: int
    unique_models: int
    duplicate_models: int
    copied: int
    index_path: str
    duplicates_path: str | None = None
