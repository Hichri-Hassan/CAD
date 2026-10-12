"""File hashing utilities."""

from __future__ import annotations

import hashlib
from pathlib import Path

from dataset.models import SourceFile

CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path | str) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def attach_hashes(files: list[SourceFile], progress: bool = True) -> list[SourceFile]:
    """Compute SHA-256 for each source file and return updated records."""
    total = len(files)
    hashed: list[SourceFile] = []

    for index, source in enumerate(files, start=1):
        file_hash = sha256_file(source.absolute_path)
        hashed.append(
            SourceFile(
                absolute_path=source.absolute_path,
                repository_name=source.repository_name,
                relative_path=source.relative_path,
                original_filename=source.original_filename,
                file_size_bytes=source.file_size_bytes,
                sha256_hash=file_hash,
            )
        )
        if progress and (index == 1 or index % 100 == 0 or index == total):
            print(f"  Hashing: {index}/{total}", flush=True)

    return hashed
