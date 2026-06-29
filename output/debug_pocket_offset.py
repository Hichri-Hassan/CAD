"""Compare pocket sketch global bounds original vs compiled."""
import FreeCAD as App


def pocket_center(path):
    doc = App.openDocument(path)
    pocket_sk = None
    for o in doc.Body.Group:
        if o.TypeId == "Sketcher::SketchObject" and o.Name in ("Sketch001", "op_003"):
            pocket_sk = o
            break
    if not pocket_sk:
        App.closeDocument(doc.Name)
        return None
    pts = []
    for g in pocket_sk.Geometry:
        if hasattr(g, "StartPoint"):
            for p in (g.StartPoint, g.EndPoint):
                pts.append(pocket_sk.Placement.multVec(App.Vector(p.x, p.y, 0)))
    cx = sum(p.x for p in pts) / len(pts)
    cy = sum(p.y for p in pts) / len(pts)
    cz = sum(p.z for p in pts) / len(pts)
    ao = pocket_sk.AttachmentOffset.Base
    info = {
        "name": pocket_sk.Name,
        "attachment_offset": (ao.x, ao.y, ao.z),
        "placement_base": (pocket_sk.Placement.Base.x, pocket_sk.Placement.Base.y, pocket_sk.Placement.Base.z),
        "centroid": (cx, cy, cz),
    }
    App.closeDocument(doc.Name)
    return info


for label, path in [
    ("ORIGINAL", "/Users/hassenhicheri/Desktop/test.FCStd"),
    ("COMPILED", "/Users/hassenhicheri/Desktop/CAD/output/test_compiled.FCStd"),
]:
    info = pocket_center(path)
    print(f"{label}: sketch={info['name']}")
    print(f"  AttachmentOffset: {info['attachment_offset']}")
    print(f"  Placement base:   {info['placement_base']}")
    print(f"  Profile centroid: ({info['centroid'][0]:.3f},{info['centroid'][1]:.3f},{info['centroid'][2]:.3f})")
