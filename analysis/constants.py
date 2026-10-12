"""FreeCAD type ID to human-readable operation labels."""

from __future__ import annotations

# Maps PartDesign / Sketcher TypeId suffix or full id to analysis label.
OPERATION_TYPE_MAP: dict[str, str] = {
    "Sketcher::SketchObject": "Sketch",
    "PartDesign::Pad": "Pad",
    "PartDesign::Pocket": "Pocket",
    "PartDesign::Hole": "Hole",
    "PartDesign::Fillet": "Fillet",
    "PartDesign::Chamfer": "Chamfer",
    "PartDesign::Revolution": "Revolution",
    "PartDesign::Groove": "Groove",
    "PartDesign::Loft": "Loft",
    "PartDesign::AdditiveLoft": "Loft",
    "PartDesign::SubtractiveLoft": "Loft",
    "PartDesign::Sweep": "Sweep",
    "PartDesign::AdditivePipe": "Sweep",
    "PartDesign::SubtractivePipe": "Sweep",
    "PartDesign::Mirrored": "Mirror",
    "PartDesign::LinearPattern": "Linear Pattern",
    "PartDesign::PolarPattern": "Polar Pattern",
    "PartDesign::MultiTransform": "MultiTransform",
    "PartDesign::Plane": "Datum Plane",
    "PartDesign::Line": "Datum Axis",
    "PartDesign::ShapeBinder": "Shape Binder",
    "PartDesign::SubShapeBinder": "Shape Binder",
    "PartDesign::Boolean": "Boolean",
    "PartDesign::Thickness": "Thickness",
    "PartDesign::Draft": "Draft",
    "PartDesign::Scaled": "Scaled",
    "PartDesign::Transformed": "Transformed",
}

PARSER_SUPPORTED_TYPES = {
    "Sketcher::SketchObject",
    "PartDesign::Pad",
    "PartDesign::Pocket",
    "PartDesign::Hole",
    "PartDesign::Fillet",
    "PartDesign::Chamfer",
}

# FreeCAD Part:: geometry type -> analysis label.
GEOMETRY_TYPE_MAP: dict[str, str] = {
    "Part::GeomLineSegment": "Line",
    "Part::GeomCircle": "Circle",
    "Part::GeomArcOfCircle": "Arc",
    "Part::GeomPoint": "Point",
    "Part::GeomEllipse": "Ellipse",
    "Part::GeomBSplineCurve": "BSpline",
    "Part::GeomBezierCurve": "Spline",
    "Part::GeomBSpline": "BSpline",
    "Part::GeomArcOfEllipse": "Arc",
    "Part::GeomArcOfParabola": "Arc",
    "Part::GeomArcOfHyperbola": "Arc",
    "Part::GeomPolygon": "Polyline",
    "Part::GeomLine": "Line",
}

# Sketcher constraint enumeration (extended beyond parser subset).
CONSTRAINT_TYPE_MAP: dict[int, str] = {
    0: "Invalid",
    1: "Coincident",
    2: "Horizontal",
    3: "Vertical",
    4: "Parallel",
    5: "Perpendicular",
    6: "Tangent",
    7: "Equal",
    8: "Symmetric",
    9: "Block",
    10: "Distance",
    11: "DistanceX",
    12: "DistanceY",
    13: "Radius",
    14: "Diameter",
    15: "Angle",
    16: "SnellsLaw",
    17: "InternalAlignment",
    18: "Symmetric",
    19: "Symmetric",
    20: "Symmetric",
    21: "Diameter",
    22: "Weight",
}

KNOWN_OPERATION_LABELS = sorted(set(OPERATION_TYPE_MAP.values()))
