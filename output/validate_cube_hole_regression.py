"""Regression validation: cube.FCStd and hole.FCStd round-trip."""
import json
import math
import sys

import FreeCAD as App

CASES = [
    {
        "name": "cube",
        "original": "/Users/hassenhicheri/Desktop/cube.FCStd",
        "rebuilt": "/Users/hassenhicheri/Desktop/CAD/output/cube_rebuilt.FCStd",
        "json": "/Users/hassenhicheri/Desktop/CAD/output/cube.json",
        "expected_features": ["SketchObject", "Pad", "SketchObject", "Hole"],
        "expected_ops": 4,
    },
    {
        "name": "hole",
        "original": "/Users/hassenhicheri/Desktop/hole.FCStd",
        "rebuilt": "/Users/hassenhicheri/Desktop/CAD/output/hole_rebuilt.FCStd",
        "json": "/Users/hassenhicheri/Desktop/CAD/output/hole.json",
        "expected_features": [
            "SketchObject",
            "Pad",
            "SketchObject",
            "Hole",
            "Chamfer",
            "Fillet",
        ],
        "expected_ops": 6,
    },
]

TOL = 0.02
REPORT = "/Users/hassenhicheri/Desktop/CAD/output/CUBE_HOLE_REGRESSION_REPORT.txt"


def close(doc_name):
    if App.ActiveDocument and App.ActiveDocument.Name == doc_name:
        App.closeDocument(doc_name)


def face_signature(face):
    normal = face.normalAt(0, 0)
    center = face.CenterOfMass
    return tuple(round(v, 2) for v in (normal.x, normal.y, normal.z, center.x, center.y, center.z))


def vec_close(a, b, tol=TOL):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3))) < tol


def load_body(path):
    doc = App.openDocument(path)
    body = doc.Body
    return doc.Name, body


def feature_types(body):
    return [o.TypeId.split("::")[-1] for o in body.Group]


def pad_face_sigs(body):
    pad = [o for o in body.Group if o.TypeId == "PartDesign::Pad"][0]
    return [face_signature(f) for f in pad.Shape.Faces]


def pad_bbox(body):
    pad = [o for o in body.Group if o.TypeId == "PartDesign::Pad"][0]
    bb = pad.Shape.BoundBox
    return (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)


def support_key(support):
    """Compare attachment semantically, ignoring FreeCAD object names."""
    if not support:
        return None
    ref_name, selector = support[0]
    if ref_name == "Origin":
        return ("origin", selector[0] if isinstance(selector, tuple) else selector)
    if isinstance(selector, tuple) and selector and str(selector[0]).startswith("Face"):
        return ("face", selector[0])
    return ("other", ref_name, selector)


def sketch_info(body):
    info = []
    for sketch in [o for o in body.Group if o.TypeId == "Sketcher::SketchObject"]:
        sup = [(s[0].Name, s[1]) for s in sketch.AttachmentSupport] if sketch.AttachmentSupport else []
        ao = sketch.AttachmentOffset.Base
        pl = sketch.Placement.Base
        entities = []
        for g in sketch.Geometry:
            if hasattr(g, "Center"):
                local = (g.Center.x, g.Center.y)
                global_pt = sketch.Placement.multVec(App.Vector(g.Center.x, g.Center.y, 0))
                entities.append(
                    {
                        "type": "Circle",
                        "local": local,
                        "global": (global_pt.x, global_pt.y, global_pt.z),
                        "radius": g.Radius,
                    }
                )
            elif hasattr(g, "X") and g.TypeId == "Part::GeomPoint":
                global_pt = sketch.Placement.multVec(App.Vector(g.X, g.Y, 0))
                entities.append(
                    {
                        "type": "Point",
                        "local": (g.X, g.Y),
                        "global": (global_pt.x, global_pt.y, global_pt.z),
                    }
                )
        info.append(
            {
                "name": sketch.Name,
                "support": sup,
                "map_mode": sketch.MapMode,
                "map_reversed": sketch.MapReversed,
                "attachment_offset": (ao.x, ao.y, ao.z),
                "placement_base": (pl.x, pl.y, pl.z),
                "entities": entities,
            }
        )
    return info


def hole_info(body):
    holes = []
    for h in [o for o in body.Group if o.TypeId == "PartDesign::Hole"]:
        holes.append(
            {
                "name": h.Name,
                "profile": h.Profile[0].Name,
                "diameter": float(h.Diameter),
                "depth": float(h.Depth),
                "reversed": bool(h.Reversed),
                "state": list(h.State),
            }
        )
    return holes


def fillet_chamfer_info(body):
    out = []
    for o in body.Group:
        if o.TypeId in ("PartDesign::Chamfer", "PartDesign::Fillet"):
            out.append(
                {
                    "name": o.Name,
                    "type": o.TypeId.split("::")[-1],
                    "base": (o.Base[0].Name, list(o.Base[1])),
                    "state": list(o.State),
                }
            )
    return out


def document_errors(body):
    return [
        o.Name
        for o in body.Document.Objects
        if hasattr(o, "State") and any("Error" in s for s in o.State)
    ]


def json_attachment_offsets(json_path):
    with open(json_path, encoding="utf-8") as handle:
        data = json.load(handle)
    offsets = {}
    for op in data["operations"]:
        if op["type"] == "Sketch":
            offsets[op["id"]] = op.get("attachment_offset")
    return offsets


def compare_case(case):
    results = []
    name = case["name"]

    json_offsets = json_attachment_offsets(case["json"])
    identity_only = all(v is None for v in json_offsets.values())
    results.append(("json_attachment_offset_identity_or_absent", identity_only, json_offsets))

    doc_o, body_o = load_body(case["original"])
    doc_r, body_r = load_body(case["rebuilt"])

    ft_o, ft_r = feature_types(body_o), feature_types(body_r)
    results.append(("feature_order", ft_o == ft_r == case["expected_features"], (ft_o, ft_r)))

    pf_o, pf_r = pad_face_sigs(body_o), pad_face_sigs(body_r)
    results.append(("pad_face_signatures", pf_o == pf_r, (len(pf_o), len(pf_r))))

    bb_o, bb_r = pad_bbox(body_o), pad_bbox(body_r)
    results.append(
        (
            "pad_bbox",
            all(abs(bb_o[i] - bb_r[i]) < TOL for i in range(6)),
            (bb_o, bb_r),
        )
    )

    sk_o, sk_r = sketch_info(body_o), sketch_info(body_r)
    sketch_support_match = all(
        support_key(s_o["support"]) == support_key(s_r["support"])
        and s_o["map_mode"] == s_r["map_mode"]
        for s_o, s_r in zip(sk_o, sk_r)
    )
    results.append(("sketch_plane_support", sketch_support_match, None))

    offset_match = all(
        vec_close(s_o["attachment_offset"], s_r["attachment_offset"])
        for s_o, s_r in zip(sk_o, sk_r)
    )
    results.append(("sketch_attachment_offset", offset_match, [(s["attachment_offset"]) for s in sk_o]))

    placement_match = all(
        vec_close(s_o["placement_base"], s_r["placement_base"]) for s_o, s_r in zip(sk_o, sk_r)
    )
    results.append(("sketch_placement_base", placement_match, None))

    entity_global_match = True
    entity_details = []
    for s_o, s_r in zip(sk_o, sk_r):
        for e_o, e_r in zip(s_o["entities"], s_r["entities"]):
            ok = vec_close(e_o["global"], e_r["global"])
            entity_global_match = entity_global_match and ok
            entity_details.append((s_o["name"], e_o["type"], e_o["global"], e_r["global"], ok))
    results.append(("hole_marker_global_position", entity_global_match, entity_details))

    holes_o, holes_r = hole_info(body_o), hole_info(body_r)
    hole_params_match = holes_o == holes_r or (
        len(holes_o) == len(holes_r)
        and all(
            abs(h_o["diameter"] - h_r["diameter"]) < TOL
            and abs(h_o["depth"] - h_r["depth"]) < TOL
            and h_o["reversed"] == h_r["reversed"]
            for h_o, h_r in zip(holes_o, holes_r)
        )
    )
    results.append(("hole_diameter_depth_reversed", hole_params_match, (holes_o, holes_r)))

    fc_o, fc_r = fillet_chamfer_info(body_o), fillet_chamfer_info(body_r)
    if fc_o or fc_r:
        fc_match = len(fc_o) == len(fc_r) and all(
            f_o["type"] == f_r["type"] and f_o["base"][1] == f_r["base"][1] and "Error" not in f_r["state"]
            for f_o, f_r in zip(fc_o, fc_r)
        )
        results.append(("chamfer_fillet_edges", fc_match, (fc_o, fc_r)))

    err_o, err_r = document_errors(body_o), document_errors(body_r)
    results.append(("document_errors", not err_o and not err_r, (err_o, err_r)))

    # Final body solid after all features
    tip_o = body_o.Group[-1].Shape
    tip_r = body_r.Group[-1].Shape
    bb_tip_o = (
        tip_o.BoundBox.XMin,
        tip_o.BoundBox.YMin,
        tip_o.BoundBox.ZMin,
        tip_o.BoundBox.XMax,
        tip_o.BoundBox.YMax,
        tip_o.BoundBox.ZMax,
    )
    bb_tip_r = (
        tip_r.BoundBox.XMin,
        tip_r.BoundBox.YMin,
        tip_r.BoundBox.ZMin,
        tip_r.BoundBox.XMax,
        tip_r.BoundBox.YMax,
        tip_r.BoundBox.ZMax,
    )
    results.append(
        (
            "final_body_bbox",
            all(abs(bb_tip_o[i] - bb_tip_r[i]) < TOL for i in range(6)),
            (bb_tip_o, bb_tip_r),
        )
    )
    results.append(
        (
            "final_body_volume",
            abs(tip_o.Volume - tip_r.Volume) < 1.0,
            (tip_o.Volume, tip_r.Volume),
        )
    )

    close(doc_o)
    close(doc_r)
    return results


lines = ["CUBE / HOLE REGRESSION REPORT", "=" * 50, ""]
all_pass = True

for case in CASES:
    lines.append(f"## {case['name'].upper()}")
    lines.append(f"original: {case['original']}")
    lines.append(f"rebuilt:  {case['rebuilt']}")
    lines.append("")
    case_pass = True
    for check_name, ok, detail in compare_case(case):
        status = "PASS" if ok else "FAIL"
        lines.append(f"  {check_name}: {status}")
        if not ok:
            lines.append(f"    detail: {detail}")
            case_pass = False
    lines.append(f"  OVERALL: {'PASS' if case_pass else 'FAIL'}")
    lines.append("")
    all_pass = all_pass and case_pass

lines.append("=" * 50)
lines.append(f"TOTAL: {'PASS' if all_pass else 'FAIL'}")

with open(REPORT, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")

print("\n".join(lines))
sys.exit(0 if all_pass else 1)
