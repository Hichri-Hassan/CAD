"""Inspect Hole properties in original vs compiled FCStd files."""
import FreeCAD as App


def inspect_hole(path, label):
    print("=" * 60)
    print(label, path)
    doc = App.openDocument(path)
    body = doc.Body
    print("Feature tree:", [(o.Name, o.TypeId) for o in body.Group])

    hole = None
    sketches = []
    pad = None
    for o in body.Group:
        if "Hole" in o.TypeId:
            hole = o
        elif o.TypeId == "Sketcher::SketchObject":
            sketches.append(o)
        elif o.TypeId == "PartDesign::Pad":
            pad = o

    placement_sketch = sketches[-1] if len(sketches) > 1 else (sketches[0] if sketches else None)

    if not hole:
        print("NO HOLE FOUND")
        App.closeDocument(doc.Name)
        return

    print("--- HOLE ---")
    print("Name:", hole.Name)
    print("TypeId:", hole.TypeId)
    print("Label:", hole.Label)

    props = [
        "Profile",
        "Diameter",
        "Depth",
        "DepthType",
        "Reversed",
        "Midplane",
        "BaseFeature",
        "DrillPoint",
        "DrillForDepth",
        "Tapered",
        "Threaded",
        "ModelThread",
        "HoleCutType",
        "BaseProfileType",
        "Placement",
    ]
    for prop in props:
        if hasattr(hole, prop):
            print(f"  {prop}: {repr(getattr(hole, prop))}")

    if placement_sketch:
        print("--- PLACEMENT SKETCH ---")
        print("Name:", placement_sketch.Name, "TypeId:", placement_sketch.TypeId)
        print("  MapMode:", placement_sketch.MapMode)
        print("  AttachmentSupport:", placement_sketch.AttachmentSupport)
        print("  AttachmentOffset:", placement_sketch.AttachmentOffset)
        print("  Placement:", placement_sketch.Placement)
        print("  Geometry count:", len(placement_sketch.Geometry))
        for index, geom in enumerate(placement_sketch.Geometry):
            detail = geom.TypeId
            if hasattr(geom, "Radius"):
                detail += f" R={geom.Radius} C=({geom.Center.x},{geom.Center.y},{geom.Center.z})"
            if hasattr(geom, "X"):
                detail += f" P=({geom.X},{geom.Y},{geom.Z})"
            print(f"    geom[{index}]: {detail}")
        print("  Hole.Profile:", hole.Profile)
        profile_obj = hole.Profile[0] if hole.Profile else None
        print("  Profile object match:", profile_obj.Name if profile_obj else None,
              "==", placement_sketch.Name, "?",
              profile_obj == placement_sketch if profile_obj else False)

    if pad:
        print("--- PAD ---")
        print("Name:", pad.Name, "Length:", pad.Length)

    App.closeDocument(doc.Name)


if __name__ == "__main__":
    inspect_hole("/Users/hassenhicheri/Desktop/cube.FCStd", "ORIGINAL")
    inspect_hole("/Users/hassenhicheri/Desktop/CAD/output/cube_compiled.FCStd", "COMPILED")
