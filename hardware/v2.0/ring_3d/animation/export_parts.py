"""Export v2 ring parts and the v1 Green Lantern emblem as assembled-pose STLs.

Run with FreeCAD's Python. Parts are written unlocked (lock angle 0); the
Blender animation applies the bayonet twist. Units stay in millimetres.
"""

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import FreeCAD  # noqa: E402,F401  (registers FreeCAD module paths)
import Mesh  # noqa: E402
import MeshPart  # noqa: E402

from design import load_parameters, pcb_interface, validate_parameters  # noqa: E402
from lantern_ring import COLORS, unrotated_geometry  # noqa: E402

EMBLEM = HERE.parents[2] / "v1.0" / "ring_3d" / "Lantern_Ring_Assembly-will_logo.stl"
# v1 emblem is modelled in the v1 assembly frame; this is the v1 body centre.
V1_BODY_CENTRE = (-3.43, -23.30)


def main(output=HERE / "build" / "meshes"):
    output.mkdir(parents=True, exist_ok=True)
    p, pcb = load_parameters(HERE.parent / "parameters.json"), pcb_interface()
    s = validate_parameters(p, pcb)
    parts = unrotated_geometry(p, pcb)
    for name in COLORS:
        mesh = MeshPart.meshFromShape(Shape=parts[name], LinearDeflection=0.02,
                                      AngularDeflection=0.15, Relative=False)
        mesh.write(str(output / (name + ".stl")))
    emblem = Mesh.Mesh(str(EMBLEM))
    bounds = emblem.BoundBox
    # Sit the emblem on the tallest LED so it covers the light without collision.
    emblem.translate(-V1_BODY_CENTRE[0], -V1_BODY_CENTRE[1],
                     s["highest_component"] - bounds.ZMin)
    emblem.write(str(output / "Emblem.stl"))
    info = {
        "units": "mm",
        "lock_angle": p["lock_angle"],
        "colors": COLORS,
        "stack": s,
        "leds": [c["xy"] for c in pcb["components"]],
        "emblem_source": EMBLEM.name,
        "emblem_size": [bounds.XLength, bounds.YLength, bounds.ZLength],
    }
    (output / "scene.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print("Exported {} meshes to {}".format(len(COLORS) + 1, output))


main()
