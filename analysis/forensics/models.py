"""Data models for FCStd forensic document classification."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ObjectRecord:
    """One FreeCAD document object."""

    name: str
    label: str
    type_id: str
    parent: str = ""


@dataclass
class BodyRecord:
    """One PartDesign body and its feature tree."""

    name: str
    label: str
    feature_count: int
    feature_types: dict[str, int] = field(default_factory=dict)
    feature_names: list[str] = field(default_factory=list)
    tip: str = ""
    depth: int = 0
    sketch_count: int = 0


@dataclass
class DocumentForensics:
    """Forensic inspection result for one FCStd file."""

    filename: str
    dataset_id: str = ""
    repository: str = ""
    original_relative_path: str = ""
    file_size_bytes: int = 0

    read_error: str = ""
    object_count: int = 0
    objects: list[ObjectRecord] = field(default_factory=list)
    type_counts: dict[str, int] = field(default_factory=dict)

    bodies: list[BodyRecord] = field(default_factory=list)
    body_count: int = 0
    sketch_count: int = 0
    partdesign_feature_count: int = 0
    has_partdesign_body: bool = False
    has_body_named_body: bool = False

    flags: dict[str, bool] = field(default_factory=dict)
    categories: list[str] = field(default_factory=list)
    primary_category: str = ""

    parser_status: str = ""
    parse_success: bool = False
    parsed_operation_count: int = 0
    parser_error: str = ""
    unsupported_features: list[str] = field(default_factory=list)
    failure_reason: str = ""

    top_level_object_types: list[str] = field(default_factory=list)


@dataclass
class ForensicDataset:
    """Aggregated forensic results."""

    documents: list[DocumentForensics] = field(default_factory=list)
    category_counts: dict[str, int] = field(default_factory=dict)
    failure_reason_counts: dict[str, int] = field(default_factory=dict)
    type_id_counts: dict[str, int] = field(default_factory=dict)
