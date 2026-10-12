"""Document category classification rules.

Classification is applied in priority order. A document may match multiple
categories; all matches are recorded in ``categories``. The first match
becomes ``primary_category``.

Category definitions
--------------------

PartDesign Part
    Exactly one ``PartDesign::Body`` object.

Multi-body PartDesign
    Two or more ``PartDesign::Body`` objects.

Assembly
    Contains ``App::Part`` or ``App::LinkGroup``/``App::Link`` assembly-style
    containers with multiple child solids/bodies.

Part Workbench Model
    No ``PartDesign::Body`` and significant Part workbench geometry
    (``Part::Feature``, ``Part::Extrusion``, ``Part::FeaturePython``, etc.).

Imported STEP/BREP
    Contains ``Part::Feature``/compound import results without PartDesign body
    and without a meaningful PartDesign feature tree.

Mesh-only Model
    Contains mesh objects and no PartDesign body and no Part solid features.

Draft Document
    Contains any ``Draft::`` object.

TechDraw Document
    Contains any ``TechDraw::`` object.

FEM Document
    Contains any ``Fem::`` object.

Empty Document
    No meaningful objects beyond default origin/planes.

Reference Document
    Dominated by links, binders, or groups without solid PartDesign content.

Unknown
    Does not clearly match any rule above.
"""

from __future__ import annotations

from analysis.forensics.models import DocumentForensics


def classify_document(doc: DocumentForensics) -> DocumentForensics:
    """Assign document categories based on raw structure."""
    flags = doc.flags
    categories: list[str] = []

    if doc.read_error:
        doc.categories = ["Corrupted Archive"]
        doc.primary_category = "Corrupted Archive"
        return doc

    if flags.get("is_empty"):
        categories.append("Empty Document")

    if doc.body_count == 1:
        categories.append("PartDesign Part")
    elif doc.body_count > 1:
        categories.append("Multi-body PartDesign")

    if flags.get("has_assembly_link"):
        categories.append("Assembly")
    elif flags.get("has_app_part") and doc.body_count > 1:
        categories.append("Assembly")

    if not flags.get("has_partdesign_body"):
        part_wb_signals = (
            flags.get("has_part_feature")
            or flags.get("has_part_extrusion")
            or doc.type_counts.get("Part::FeaturePython", 0) > 0
            or doc.type_counts.get("Part::Part2DObjectPython", 0) > 0
        )
        if part_wb_signals:
            categories.append("Part Workbench Model")

    if (
        flags.get("has_imported_part")
        and not flags.get("has_partdesign_body")
        and doc.sketch_count == 0
        and doc.type_counts.get("Part::Feature", 0) > 0
    ):
        categories.append("Imported STEP/BREP")

    if (
        flags.get("has_mesh")
        and not flags.get("has_partdesign_body")
        and not flags.get("has_part_feature")
    ):
        categories.append("Mesh-only Model")

    if flags.get("has_draft"):
        categories.append("Draft Document")

    if flags.get("has_techdraw"):
        categories.append("TechDraw Document")

    if flags.get("has_fem"):
        categories.append("FEM Document")

    if (
        flags.get("has_document_group")
        and not flags.get("has_partdesign_body")
        and doc.partdesign_feature_count == 0
        and categories == []
    ):
        categories.append("Reference Document")

    if not categories:
        categories.append("Unknown")

    doc.categories = categories
    doc.primary_category = categories[0]
    return doc
