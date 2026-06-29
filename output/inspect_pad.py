"""Compare Pad and sketch attachment details."""
import FreeCAD as App


def inspect_pad(path, label):
    print("=" * 60, label)
    doc = App.openDocument(path)
    body = doc.Body
    pad = [o for o in body.Group if o.TypeId == "PartDesign::Pad"][0]
    sketches = [o for o in body.Group if o.TypeId == "Sketcher::SketchObject"]
    hole = [o for o in body.Group if "Hole" in o.TypeId][0]

    print("PAD:", pad.Name)
    for prop in ["Length", "Reversed", "Midplane", "Direction", "AlongSketchNormal", "Type", "Profile"]:
        if hasattr(pad, prop):
            print(f"  {prop}: {getattr(pad, prop)}")
    print("  Placement:", pad.Placement.Base, pad.Placement.Rotation.toEuler())

    print("\nSKETCHES:")
    for s in sketches:
        print(f"  {s.Name}:")
        print(f"    AttachmentSupport: {[(x[0].Name, x[1]) for x in s.AttachmentSupport]}")
        print(f"    Placement:", s.Placement.Base, s.Placement.Rotation.toEuler())
        if s.Geometry:
            g = s.Geometry[0]
            if hasattr(g, "Center"):
                local = g.Center
                global_p = s.Placement.multVec(App.Vector(local.x, local.y, local.z))
                print(f"    circle local={local} global={global_p}")

    print("\nHOLE:", hole.Name, hole.TypeId)
    print("  Placement:", hole.Placement.Base, hole.Placement.Rotation.toEuler())

    # List pad faces count and Face4 center for debugging
    shape = pad.Shape
    print(f"\nPAD faces: {len(shape.Faces)}")
    if len(shape.Faces) >= 4:
        face4 = shape.Faces[3]  # Face4 is 1-indexed in subnames, index 3 in 0-based
        c = face4.CenterOfMass
        print(f"  Face4 (index 3) center of mass: ({c.x:.3f}, {c.y:.3f}, {c.z:.3f})")

    App.closeDocument(doc.Name)


inspect_pad("/Users/hassenhicheri/Desktop/cube.FCStd", "ORIGINAL")
inspect_pad("/Users/hassenhicheri/Desktop/CAD/output/cube_compiled.FCStd", "COMPILED")
