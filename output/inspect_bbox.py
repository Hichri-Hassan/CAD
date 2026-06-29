"""Compare pad bounding boxes and face normals."""
import FreeCAD as App


def bbox(path, label):
    doc = App.openDocument(path)
    pad = [o for o in doc.Body.Group if o.TypeId == "PartDesign::Pad"][0]
    bb = pad.Shape.BoundBox
    print(f"\n{label} PAD bbox:")
    print(f"  X: [{bb.XMin:.3f}, {bb.XMax:.3f}]")
    print(f"  Y: [{bb.YMin:.3f}, {bb.YMax:.3f}]")
    print(f"  Z: [{bb.ZMin:.3f}, {bb.ZMax:.3f}]")
    print(f"  Placement:", pad.Placement.Base, pad.Placement.Rotation.toEuler())
    print(f"  Direction:", pad.Direction if hasattr(pad, "Direction") else "N/A")
    f4 = pad.Shape.Faces[3]
    print(f"  Face4 normal:", f4.normalAt(0, 0))
    print(f"  Face4 center:", f4.CenterOfMass)
    App.closeDocument(doc.Name)


bbox("/Users/hassenhicheri/Desktop/cube.FCStd", "ORIGINAL")
bbox("/Users/hassenhicheri/Desktop/CAD/output/cube_compiled.FCStd", "COMPILED")
