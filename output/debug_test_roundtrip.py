"""Debug sketch frames and hole global positions for test.FCStd round-trip."""
import FreeCAD as App
import math


def placement_str(pl):
    b = pl.Base
    r = pl.Rotation.toEuler()
    return f"base=({b.x:.3f},{b.y:.3f},{b.z:.3f}) euler=({r[0]:.3f},{r[1]:.3f},{r[2]:.3f})"


def attachment_offset_str(sketch):
    ao = sketch.AttachmentOffset
    b = ao.Base
    return f"({b.x:.3f},{b.y:.3f},{b.z:.3f})"


def inspect_doc(path, label):
    print("=" * 70)
    print(label, path)
    doc = App.openDocument(path)
    body = doc.Body
    print("Feature order:", [(o.Name, o.TypeId.split("::")[-1]) for o in body.Group])

    for sketch in [o for o in body.Group if o.TypeId == "Sketcher::SketchObject"]:
        sup = [(s[0].Name, s[1]) for s in sketch.AttachmentSupport] if sketch.AttachmentSupport else []
        print(f"\n  Sketch {sketch.Name}:")
        print(f"    AttachmentSupport: {sup}")
        print(f"    MapMode: {sketch.MapMode}  MapReversed: {sketch.MapReversed}")
        print(f"    AttachmentOffset: {attachment_offset_str(sketch)}")
        print(f"    Placement: {placement_str(sketch.Placement)}")
        for i, g in enumerate(sketch.Geometry):
            if hasattr(g, "Center"):
                local = App.Vector(g.Center.x, g.Center.y, 0)
                global_pt = sketch.Placement.multVec(local)
                print(
                    f"    geom[{i}] Circle local=({g.Center.x:.3f},{g.Center.y:.3f}) "
                    f"global=({global_pt.x:.3f},{global_pt.y:.3f},{global_pt.z:.3f}) R={g.Radius:.3f}"
                )
            elif hasattr(g, "X") and g.TypeId == "Part::GeomPoint":
                local = App.Vector(g.X, g.Y, 0)
                global_pt = sketch.Placement.multVec(local)
                print(
                    f"    geom[{i}] Point local=({g.X:.3f},{g.Y:.3f}) "
                    f"global=({global_pt.x:.3f},{global_pt.y:.3f},{global_pt.z:.3f})"
                )

    holes = [o for o in body.Group if o.TypeId == "PartDesign::Hole"]
    for h in holes:
        prof = h.Profile[0]
        print(f"\n  Hole {h.Name}: profile={prof.Name} D={h.Diameter} depth={h.Depth} reversed={h.Reversed}")

    App.closeDocument(doc.Name)


def hole_global_positions(path):
    doc = App.openDocument(path)
    positions = []
    for sketch in [o for o in doc.Body.Group if o.TypeId == "Sketcher::SketchObject"]:
        for g in sketch.Geometry:
            if hasattr(g, "Center"):
                gp = sketch.Placement.multVec(App.Vector(g.Center.x, g.Center.y, 0))
                positions.append((sketch.Name, gp.x, gp.y, gp.z))
    App.closeDocument(doc.Name)
    return positions


inspect_doc("/Users/hassenhicheri/Desktop/test.FCStd", "ORIGINAL")
inspect_doc("/Users/hassenhicheri/Desktop/CAD/output/test_compiled.FCStd", "COMPILED")

orig = hole_global_positions("/Users/hassenhicheri/Desktop/test.FCStd")
comp = hole_global_positions("/Users/hassenhicheri/Desktop/CAD/output/test_compiled.FCStd")

print("\n" + "=" * 70)
print("HOLE GLOBAL POSITION COMPARISON")
for i, ((n1, x1, y1, z1), (n2, x2, y2, z2)) in enumerate(zip(orig, comp)):
    dist_orig = math.sqrt(x1 * x1 + y1 * y1 + z1 * z1)
    dist_between_orig = 0
    if i == 1 and len(orig) >= 2:
        dist_between_orig = math.sqrt(
            (orig[1][1] - orig[0][1]) ** 2
            + (orig[1][2] - orig[0][2]) ** 2
            + (orig[1][3] - orig[0][3]) ** 2
        )
    print(f"  Hole {i+1}: orig=({x1:.3f},{y1:.3f},{z1:.3f}) comp=({x2:.3f},{y2:.3f},{z2:.3f})")
    if i == 0:
        print(f"    delta comp-orig: ({x2-x1:.3f},{y2-y1:.3f},{z2-z1:.3f})")

if len(orig) >= 2 and len(comp) >= 2:
    d_orig = math.sqrt(sum((orig[1][j] - orig[0][j]) ** 2 for j in (1, 2, 3)))
    d_comp = math.sqrt(sum((comp[1][j] - comp[0][j]) ** 2 for j in (1, 2, 3)))
    print(f"\n  Distance between holes: original={d_orig:.3f} mm  compiled={d_comp:.3f} mm")
