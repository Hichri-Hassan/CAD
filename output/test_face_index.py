import FreeCAD as App
import Part

for use_origin in [True, False]:
    doc = App.newDocument("t")
    body = doc.addObject("PartDesign::Body", "Body")
    doc.recompute()
    sketch = body.newObject("Sketcher::SketchObject", "Sketch")
    if use_origin:
        sketch.AttachmentSupport = [(body.Origin, "XZ_Plane")]
    else:
        sketch.AttachmentSupport = [(body.Origin.getObject("XZ_Plane"), "")]
    sketch.MapMode = "FlatFace"
    doc.recompute()
    x0, y0, w, h = -30.604, 0, 30.604, 30.891
    pts = [
        App.Vector(x0, y0, 0),
        App.Vector(x0 + w, y0, 0),
        App.Vector(x0 + w, y0 + h, 0),
        App.Vector(x0, y0 + h, 0),
    ]
    for i in range(4):
        sketch.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]), False)
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = (sketch, [""])
    pad.Length = 32
    doc.recompute()
    label = "ORIGIN_LINK" if use_origin else "DIRECT"
    print(label, "Pad rot", pad.Placement.Rotation.toEuler())
    for i, face in enumerate(pad.Shape.Faces):
        normal = face.normalAt(0, 0)
        center = face.CenterOfMass
        print(
            f"  Face{i + 1} n=({normal.x:.0f},{normal.y:.0f},{normal.z:.0f}) "
            f"c=({center.x:.1f},{center.y:.1f},{center.z:.1f})"
        )
    App.closeDocument(doc.Name)
    print()
