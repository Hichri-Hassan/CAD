"""Test whether sketch line order affects Face4 indexing."""
import FreeCAD as App
import Part

x0, y0, w, h = -30.604, 0.0, 30.604, 30.891

# Original FreeCAD line order from cube.FCStd Document.xml
ORIGINAL_LINES = [
    (App.Vector(x0, y0 + h, 0), App.Vector(x0, y0, 0)),
    (App.Vector(x0, y0, 0), App.Vector(x0 + w, y0, 0)),
    (App.Vector(x0 + w, y0, 0), App.Vector(x0 + w, y0 + h, 0)),
    (App.Vector(x0 + w, y0 + h, 0), App.Vector(x0, y0 + h, 0)),
]

# Compiler rectangle order (bottom-first)
COMPILER_LINES = [
    (App.Vector(x0, y0, 0), App.Vector(x0 + w, y0, 0)),
    (App.Vector(x0 + w, y0, 0), App.Vector(x0 + w, y0 + h, 0)),
    (App.Vector(x0 + w, y0 + h, 0), App.Vector(x0, y0 + h, 0)),
    (App.Vector(x0, y0 + h, 0), App.Vector(x0, y0, 0)),
]


def build(label, lines):
    doc = App.newDocument(label)
    body = doc.addObject("PartDesign::Body", "Body")
    doc.recompute()
    sketch = body.newObject("Sketcher::SketchObject", "Sketch")
    sketch.AttachmentSupport = [(body.Origin, "XZ_Plane")]
    sketch.MapMode = "FlatFace"
    doc.recompute()
    for start, end in lines:
        sketch.addGeometry(Part.LineSegment(start, end), False)
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = (sketch, [""])
    pad.Length = 32
    doc.recompute()
    print(f"\n{label} Pad rot={pad.Placement.Rotation.toEuler()}")
    for i, face in enumerate(pad.Shape.Faces):
        n = face.normalAt(0, 0)
        c = face.CenterOfMass
        print(f"  Face{i + 1} n=({n.x:.0f},{n.y:.0f},{n.z:.0f}) c=({c.x:.1f},{c.y:.1f},{c.z:.1f})")
    App.closeDocument(doc.Name)


build("ORIGINAL_LINE_ORDER", ORIGINAL_LINES)
build("COMPILER_LINE_ORDER", COMPILER_LINES)
