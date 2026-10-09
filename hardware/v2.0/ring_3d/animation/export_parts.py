"""Export v2 ring parts and the Lantern Corps crowns as assembled-pose STLs.

Run with FreeCAD's Python after crowns.py. Parts are written unlocked (lock
angle 0); the Blender animation applies the bayonet twist. Units stay in mm.
"""

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import FreeCAD  # noqa: E402,F401  (registers FreeCAD module paths)
import MeshPart  # noqa: E402
import Part  # noqa: E402

from design import load_parameters, pcb_interface, validate_parameters  # noqa: E402
from lantern_ring import COLORS, unrotated_geometry  # noqa: E402

CROWNS = HERE.parent / "generated" / "crowns"


def main(output=HERE / "build" / "meshes"):
    output.mkdir(parents=True, exist_ok=True)
    p, pcb = load_parameters(HERE.parent / "parameters.json"), pcb_interface()
    s = validate_parameters(p, pcb)
    parts = unrotated_geometry(p, pcb)
    # The crown replaces the plain bezel: it is the bezel plus skirt, lens and logo.
    shapes = {name: parts[name] for name in COLORS if name != "Bezel"}
    report = json.loads((CROWNS / "crowns.json").read_text(encoding="utf-8"))
    for key in report["crowns"]:
        # Crown STEPs are in the cassette insertion frame, like unrotated_geometry.
        shapes["Crown_" + key] = Part.read(str(CROWNS / "Crown_{}.step".format(key)))
    for name, shape in shapes.items():
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02,
                                      AngularDeflection=0.15, Relative=False)
        mesh.write(str(output / (name + ".stl")))
    info = {
        "units": "mm",
        "lock_angle": p["lock_angle"],
        "colors": COLORS,
        "stack": s,
        "leds": [c["xy"] for c in pcb["components"]],
        "crowns": {key: {"corps": c["corps"], "light": c["light"]}
                   for key, c in report["crowns"].items()},
    }
    (output / "scene.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print("Exported {} meshes to {}".format(len(shapes), output))


main()
