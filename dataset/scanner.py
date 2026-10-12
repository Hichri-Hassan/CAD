"""Scan repositories for .FCStd files."""

from __future__ import annotations

from pathlib import Path

from dataset.models import SourceFile


FCSTD_SUFFIXES = {".fcstd"}


def scan_fcstd_files(repository_path: Path, repository_name: str) -> list[SourceFile]:
    """Recursively find every .FCStd file under repository_path."""
    repository_path = repository_path.resolve()
    if not repository_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repository_path}")

    discovered: list[SourceFile] = []
    for path in sorted(repository_path.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.casefold() not in FCSTD_SUFFIXES:
            continue

        stat = path.stat()
        discovered.append(
            SourceFile(
                absolute_path=str(path),
                repository_name=repository_name,
                relative_path=path.relative_to(repository_path).as_posix(),
                original_filename=path.name,
                file_size_bytes=stat.st_size,
            )
        )

    return discovered
