"""FreeCAD: validate the actual populated STEP and conservative window envelopes."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import FreeCAD as App
import Import
import Part

HERE = Path(__file__).resolve().parent
GEN = HERE / "generated"
spec = importlib.util.spec_from_file_location(
    "_saved_interface", HERE.parent / "ring_ir_prog_clip" / "test_prog_clip.py")
saved = importlib.util.module_from_spec(spec)
spec.loader.exec_module(saved)
fps = saved.footprints(HERE / "ring_pcb_RGBW.kicad_pcb")
geometry = json.loads((HERE.parent / "ring_ir_prog_clip" / "generated" / "geometry.json").read_text())
window = geometry["fit_inputs"]["anvil"]["window"]
origin = fps["TP3"]["pads"]["1"][0]
limits = {"D": (5.3, 5.1, 1.2), "U": (4.1, 4.1, 1.0),
          "Q": (1.7, 1.7, 1.0), "R": (1.1, 0.6, 0.5),
          "C1": (1.1, 0.6, 0.6), "C2": (2.1, 1.35, 1.4)}
screens = {}
for ref, fp in fps.items():
    if ref.startswith("TP") or ref == "JP1":
        continue
    width, length, height = limits[ref if ref in limits else ref[0]]
    corners = []
    angle = math.radians(fp["rot"])
    for dx in (-width / 2, width / 2):
        for dy in (-length / 2, length / 2):
            x = fp["at"][0] + dx * math.cos(angle) + dy * math.sin(angle)
            y = fp["at"][1] - dx * math.sin(angle) + dy * math.cos(angle)
            u, v = origin[0] - x, y - origin[1]
            if not (window[0] < u < window[2] and window[1] < v < window[3]):
                raise ValueError("Component envelope outside anvil opening: " + ref)
            corners.append((u, v))
    screens[ref] = {"screen_envelope_mm": [width, length, height],
                    "window_edge_margin_mm": min(min(u - window[0], window[2] - u,
                         v - window[1], window[3] - v) for u, v in corners)}
step = GEN / "populated.step"
doc = App.newDocument("RGBW_checked")
Import.insert(str(step), doc.Name)
doc.recompute()
features = [o for o in doc.RootObjects if hasattr(o, "Shape") and not o.Shape.isNull()]
if not features or any(not o.Shape.isValid() for o in features):
    raise ValueError("Invalid/empty populated STEP")
if len(features) != 1 or not hasattr(features[0], "Group"):
    raise ValueError("Expected one populated STEP assembly")
members = features[0].Group
if len(members) != len(screens) + 1:
    raise ValueError("Missing or unexpected populated STEP instances: %d" % len(members))
for ref in screens:
    x, y = fps[ref]["at"]
    matches = [o for o in members if
               abs(o.getGlobalPlacement().Base.x - (x - 150)) < 0.001 and
               abs(o.getGlobalPlacement().Base.y - (100 - y)) < 0.001]
    if len(matches) != 1 or matches[0].Shape.isNull() or not matches[0].Shape.isValid():
        raise ValueError("Missing/invalid placed STEP model: " + ref)
    screens[ref]["step_instance"] = matches[0].Name
solid_count = sum(len(o.Shape.Solids) for o in features)
if solid_count < len(screens) + 1:
    raise ValueError("Missing populated STEP bodies")
shape = Part.makeCompound([o.Shape for o in features])
box = shape.BoundBox
if abs(box.XLength - 17.526) > 0.05 or abs(box.YLength - 19.05) > 0.05:
    raise ValueError("STEP outline/envelope changed: " + str(box))
doc.saveAs(str(GEN / "RGBW_checked.FCStd"))
inputs = [HERE / name for name in ("ring_pcb_RGBW.kicad_pcb", "ring_pcb_RGBW.kicad_sch",
                                   "create_led_model.py", "check_cad.py", "build.ps1")]
inputs += list((HERE / "models" / "step").glob("*.step"))
report = {"valid_solids": solid_count, "feature_count": len(features),
          "inputs_sha256": {p.relative_to(HERE).as_posix():
                            hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                            for p in inputs},
          "clip_geometry_sha256": hashlib.sha256(
              (HERE.parent / "ring_ir_prog_clip" / "generated" / "geometry.json")
              .read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
          "step_sha256": hashlib.sha256(step.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
          "component_window_screen_passed": True, "component_screens": screens,
          "overall_bounds_mm": [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax],
          "scope": "Nominal package CAD plus conservative size screens, not physical clip fit, solder allowance or jaw/pin qualification",
          "model_scope": "LED/QFN/SOT are local nominal envelopes with illustrative terminal details; passives use KiCad STEP models",
          "clip_geometry_measured": False}
(GEN / "cad-validation.json").write_text(json.dumps(report, indent=2) + "\n")
App.closeDocument(doc.Name)
print("Valid populated STEP solids: %d; 22 component envelopes inside the anvil window." % solid_count)
