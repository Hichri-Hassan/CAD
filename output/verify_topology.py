"""Verify topology fidelity: face mapping, hole location, feature trees."""
import FreeCAD as App


def face_signature(face):
    normal = face.normalAt(0, 0)
    center = face.CenterOfMass
    return (
        round(normal.x, 2),
        round(normal.y, 2),
        round(normal.z, 2),
        round(center.x, 2),
        round(center.y, 2),
        round(center.z, 2),
    )


def inspect(path, label):
    print("=" * 60)
    print(label)
    doc = App.openDocument(path)
    body = doc.Body
    print("Feature tree:", [(o.Name, o.TypeId.split("::")[-1]) for o in body.Group])

    pad = [o for o in body.Group if o.TypeId == "PartDesign::Pad"][0]
    print(f"Pad Placement rot: {pad.Placement.Rotation.toEuler()}")
    print("Pad faces:")
    for i, face in enumerate(pad.Shape.Faces):
        sig = face_signature(face)
        print(f"  Face{i + 1}: n=({sig[0]},{sig[1]},{sig[2]}) c=({sig[3]},{sig[4]},{sig[5]})")

    sketches = [o for o in body.Group if o.TypeId == "Sketcher::SketchObject"]
    for sketch in sketches:
        sup = [(s[0].Name, s[1]) for s in sketch.AttachmentSupport] if sketch.AttachmentSupport else []
        print(f"Sketch {sketch.Name}: support={sup} placement={sketch.Placement.Base}")
        for g in sketch.Geometry:
            if hasattr(g, "Center"):
                gp = sketch.Placement.multVec(App.Vector(g.Center.x, g.Center.y, g.Center.z))
                print(f"  circle global=({gp.x:.3f},{gp.y:.3f},{gp.z:.3f}) R={g.Radius:.3f}")
            if hasattr(g, "X") and g.TypeId == "Part::GeomPoint":
                gp = sketch.Placement.multVec(App.Vector(g.X, g.Y, g.Z))
                print(f"  point global=({gp.x:.3f},{gp.y:.3f},{gp.z:.3f})")

    hole = [o for o in body.Group if "Hole" in o.TypeId]
    if hole:
        h = hole[0]
        print(f"Hole: D={h.Diameter} depth={h.Depth} profile={h.Profile[0].Name} TypeId={h.TypeId}")

    for o in body.Group:
        if o.TypeId in ("PartDesign::Chamfer", "PartDesign::Fillet"):
            base = o.Base if hasattr(o, "Base") else None
            print(f"{o.TypeId.split('::')[-1]} {o.Name}: base={base} state={o.State}")

    errors = [o.Name for o in doc.Objects if hasattr(o, "State") and "Error" in o.State]
    print("Errors:", errors or "none")
    App.closeDocument(doc.Name)


def compare_face_maps(orig_path, comp_path):
    print("\n" + "=" * 60)
    print("FACE MAP COMPARISON")
    for path, label in [(orig_path, "orig"), (comp_path, "comp")]:
        doc = App.openDocument(path)
        pad = [o for o in doc.Body.Group if o.TypeId == "PartDesign::Pad"][0]
        sigs = {f"Face{i+1}": face_signature(pad.Shape.Faces[i]) for i in range(len(pad.Shape.Faces))}
        App.closeDocument(doc.Name)
        print(label, sigs)

    doc_o = App.openDocument(orig_path)
    doc_c = App.openDocument(comp_path)
    pad_o = [o for o in doc_o.Body.Group if o.TypeId == "PartDesign::Pad"][0]
    pad_c = [o for o in doc_c.Body.Group if o.TypeId == "PartDesign::Pad"][0]
    match = all(
        face_signature(pad_o.Shape.Faces[i]) == face_signature(pad_c.Shape.Faces[i])
        for i in range(len(pad_o.Shape.Faces))
    )
    print("Face-by-face signatures match:", match)
    App.closeDocument(doc_o.Name)
    App.closeDocument(doc_c.Name)


inspect("/Users/hassenhicheri/Desktop/cube.FCStd", "ORIGINAL cube")
inspect("/Users/hassenhicheri/Desktop/CAD/output/cube_compiled.FCStd", "COMPILED cube")
compare_face_maps("/Users/hassenhicheri/Desktop/cube.FCStd", "/Users/hassenhicheri/Desktop/CAD/output/cube_compiled.FCStd")

inspect("/Users/hassenhicheri/Desktop/hole.FCStd", "ORIGINAL hole")
inspect("/Users/hassenhicheri/Desktop/CAD/output/hole_compiled.FCStd", "COMPILED hole")
compare_face_maps("/Users/hassenhicheri/Desktop/hole.FCStd", "/Users/hassenhicheri/Desktop/CAD/output/hole_compiled.FCStd")
