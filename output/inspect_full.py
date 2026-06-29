"""Deep comparison of sketch placements and 3D hole positions."""
import FreeCAD as App


def inspect_full(path, label):
    print("=" * 60)
    print(label)
    doc = App.openDocument(path)
    body = doc.Body

    for o in body.Group:
        print(f"\n--- {o.Name} ({o.TypeId.split('::')[-1]}) ---")
        if hasattr(o, "MapMode"):
            print("  MapMode:", o.MapMode)
        if hasattr(o, "AttachmentSupport"):
            sup = o.AttachmentSupport
            if sup:
                print("  AttachmentSupport:", [(s[0].Name, s[1]) for s in sup])
        if hasattr(o, "AttachmentOffset"):
            print("  AttachmentOffset:", o.AttachmentOffset)
        if hasattr(o, "Placement"):
            p = o.Placement
            print("  Placement:", p.Base, p.Rotation.toEuler())

        if o.TypeId == "Sketcher::SketchObject":
            for i, g in enumerate(o.Geometry):
                print(f"  geom[{i}]: {g.TypeId}", end="")
                if hasattr(g, "Radius"):
                    c = g.Center
                    print(f" local=({c.x:.3f},{c.y:.3f},{c.z:.3f}) R={g.Radius:.3f}", end="")
                    # global position of center
                    gp = o.Placement.multVec(App.Vector(c.x, c.y, c.z))
                    print(f" global=({gp.x:.3f},{gp.y:.3f},{gp.z:.3f})", end="")
                print()

        if o.TypeId == "PartDesign::Hole":
            print("  Diameter:", o.Diameter, "Depth:", o.Depth, "DepthType:", o.DepthType)
            print("  Profile:", o.Profile[0].Name if o.Profile else None)
            print("  BaseFeature:", o.BaseFeature.Name if o.BaseFeature else None)

    App.closeDocument(doc.Name)


inspect_full("/Users/hassenhicheri/Desktop/cube.FCStd", "ORIGINAL")
inspect_full("/Users/hassenhicheri/Desktop/CAD/output/cube_compiled.FCStd", "COMPILED")
