"""Validate test.FCStd round-trip after attachment_offset fix."""
import math
import sys

import FreeCAD as App


ORIGINAL = "/Users/hassenhicheri/Desktop/test.FCStd"
REBUILT = "/Users/hassenhicheri/Desktop/CAD/output/rebuilt.FCStd"


def hole_global_positions(path):
    doc = App.openDocument(path)
    positions = []
    for sketch in [o for o in doc.Body.Group if o.TypeId == "Sketcher::SketchObject"]:
        for g in sketch.Geometry:
            if hasattr(g, "Center"):
                gp = sketch.Placement.multVec(App.Vector(g.Center.x, g.Center.y, 0))
                positions.append((gp.x, gp.y, gp.z))
    App.closeDocument(doc.Name)
    return positions


def pocket_centroid(path):
    doc = App.openDocument(path)
    pocket_sk = None
    for o in doc.Body.Group:
        if o.TypeId == "Sketcher::SketchObject" and o.Name in ("Sketch001", "op_003"):
            pocket_sk = o
            break
    pts = []
    for g in pocket_sk.Geometry:
        if hasattr(g, "StartPoint"):
            for p in (g.StartPoint, g.EndPoint):
                pts.append(pocket_sk.Placement.multVec(App.Vector(p.x, p.y, 0)))
    cx = sum(p.x for p in pts) / len(pts)
    cy = sum(p.y for p in pts) / len(pts)
    cz = sum(p.z for p in pts) / len(pts)
    App.closeDocument(doc.Name)
    return cx, cy, cz


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


orig_holes = hole_global_positions(ORIGINAL)
rebuilt_holes = hole_global_positions(REBUILT)
orig_pocket = pocket_centroid(ORIGINAL)
rebuilt_pocket = pocket_centroid(REBUILT)

hole_distance_orig = dist(orig_holes[0], orig_holes[1])
hole_distance_rebuilt = dist(rebuilt_holes[0], rebuilt_holes[1])

print("Hole 1 global:")
print(f"  original: ({orig_holes[0][0]:.3f}, {orig_holes[0][1]:.3f}, {orig_holes[0][2]:.3f})")
print(f"  rebuilt:  ({rebuilt_holes[0][0]:.3f}, {rebuilt_holes[0][1]:.3f}, {rebuilt_holes[0][2]:.3f})")
print("Hole 2 global:")
print(f"  original: ({orig_holes[1][0]:.3f}, {orig_holes[1][1]:.3f}, {orig_holes[1][2]:.3f})")
print(f"  rebuilt:  ({rebuilt_holes[1][0]:.3f}, {rebuilt_holes[1][1]:.3f}, {rebuilt_holes[1][2]:.3f})")
print(f"Hole distance: original={hole_distance_orig:.3f} rebuilt={hole_distance_rebuilt:.3f}")
print(
    f"Pocket centroid: original=({orig_pocket[0]:.3f},{orig_pocket[1]:.3f},{orig_pocket[2]:.3f}) "
    f"rebuilt=({rebuilt_pocket[0]:.3f},{rebuilt_pocket[1]:.3f},{rebuilt_pocket[2]:.3f})"
)

tol = 0.01
checks = [
    ("hole distance", abs(hole_distance_rebuilt - 16.766) < 0.05),
    ("hole 1 match", dist(orig_holes[0], rebuilt_holes[0]) < tol),
    ("hole 2 match", dist(orig_holes[1], rebuilt_holes[1]) < tol),
    ("pocket Y", abs(rebuilt_pocket[1] - 7.0) < tol),
    ("pocket Z", abs(rebuilt_pocket[2] - 19.0) < tol),
]

report_path = "/Users/hassenhicheri/Desktop/CAD/output/validate_test_results.txt"
with open(report_path, "w", encoding="utf-8") as handle:
    handle.write(f"hole_distance_original={hole_distance_orig:.3f}\n")
    handle.write(f"hole_distance_rebuilt={hole_distance_rebuilt:.3f}\n")
    handle.write(f"pocket_centroid_original={orig_pocket[0]:.3f},{orig_pocket[1]:.3f},{orig_pocket[2]:.3f}\n")
    handle.write(f"pocket_centroid_rebuilt={rebuilt_pocket[0]:.3f},{rebuilt_pocket[1]:.3f},{rebuilt_pocket[2]:.3f}\n")
    for name, ok in checks:
        handle.write(f"{name}={'PASS' if ok else 'FAIL'}\n")

print("\nValidation:")
all_ok = True
for name, ok in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  {name}: {status}")
    all_ok = all_ok and ok

sys.exit(0 if all_ok else 1)
