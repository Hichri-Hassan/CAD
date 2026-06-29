"""Test whether Origin vs direct plane attachment affects Pad orientation."""
import FreeCAD as App
import Part


def build(use_origin_link):
    label = "via_origin" if use_origin_link else "direct_plane"
    doc = App.newDocument(label)
    body = doc.addObject("PartDesign::Body", "Body")
    doc.recompute()

    sketch = body.newObject("Sketcher::SketchObject", "Sketch")
    if use_origin_link:
        sketch.AttachmentSupport = [(body.Origin, "XZ_Plane")]
    else:
        plane = body.Origin.getObject("XZ_Plane")
        sketch.AttachmentSupport = [(plane, "")]
    sketch.MapMode = "FlatFace"
    doc.recompute()

    # Rectangle similar to cube
    x0, y0, w, h = -30.604, 0.0, 30.604, 30.891
    pts = [
        App.Vector(x0, y0, 0), App.Vector(x0 + w, y0, 0),
        App.Vector(x0 + w, y0 + h, 0), App.Vector(x0, y0 + h, 0),
    ]
    for i in range(4):
        sketch.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]), False)

    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = (sketch, [""])
    pad.Length = 32.0
    doc.recompute()

    print(f"\n=== {label} ===")
    print("Sketch AttachmentSupport:", [(s[0].Name, s[1]) for s in sketch.AttachmentSupport])
    print("Sketch Placement:", sketch.Placement.Base, sketch.Placement.Rotation.toEuler())
    print("Pad Placement:", pad.Placement.Base, pad.Placement.Rotation.toEuler())
    if len(pad.Shape.Faces) >= 4:
        c = pad.Shape.Faces[3].CenterOfMass
        print(f"Face4 center: ({c.x:.3f}, {c.y:.3f}, {c.z:.3f})")

    App.closeDocument(doc.Name)


build(True)
build(False)
