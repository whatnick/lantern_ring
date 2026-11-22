"""FreeCAD: datasheet-sized package envelopes; terminal details are illustrative."""

import json
from pathlib import Path

import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
doc = App.newDocument("RGBW_LED_Envelope")
body = doc.addObject("Part::Feature", "Package")
body.Shape = Part.makeBox(5.2, 5.0, 0.75, App.Vector(-2.6, -2.5, 0.3))
lens = doc.addObject("Part::Feature", "Lens")
lens.Shape = Part.makeBox(4.0, 4.0, 0.05, App.Vector(-2, -2, 1.05))
if App.GuiUp:
    body.ViewObject.ShapeColor = (0.87, 0.86, 0.79)
    lens.ViewObject.ShapeColor = (0.96, 0.96, 0.93)
leads = []
for x in (-2.4, 2.0):
    for y in (-1.9, -0.75, 0.4, 1.55):
        lead = doc.addObject("Part::Feature", "Terminal%d" % len(leads))
        lead.Shape = Part.makeBox(0.4, 0.55, 0.3, App.Vector(x, y, 0))
        leads.append(lead)
doc.recompute()
for obj in [body, lens] + leads:
    if not obj.Shape.isValid() or obj.Shape.Volume <= 0:
        raise ValueError("Invalid LED model part " + obj.Name)
out = HERE / "models" / "step"
out.mkdir(parents=True, exist_ok=True)
Part.export([body, lens] + leads, str(out / "CLQ6A_RGBW.step"))
doc.saveAs(str(out.parent / "CLQ6A_RGBW.FCStd"))
(out.parent / "led-envelope.json").write_text(json.dumps({
    "source": "Cree CLD-CT1387 Rev14 p11, 5.2 x 5.0 x 1.1 mm",
    "scope": "Nominal external envelope; lens and terminal details illustrative, not manufacturer CAD or physical fit qualification",
    "dimensions_mm": [5.2, 5.0, 1.1],
    "valid_solids": len(leads) + 2
}, indent=2) + "\n")
App.closeDocument(doc.Name)

for name, shapes in (
        ("ATtiny85_QFN20", [
            Part.makeBox(4, 4, 0.8, App.Vector(-2, -2, 0.1)),
            Part.makeBox(2.6, 2.6, 0.1, App.Vector(-1.3, -1.3, 0)),
        ] + [
            Part.makeBox(w, h, 0.1, App.Vector(x, y, 0))
            for k in range(5) for x, y, w, h in (
                (-2, -1.125 + k * 0.5, 0.4, 0.25),
                (1.6, -1.125 + k * 0.5, 0.4, 0.25),
                (-1.125 + k * 0.5, -2, 0.25, 0.4),
                (-1.125 + k * 0.5, 1.6, 0.25, 0.4))]),
        ("NTZD3154N_SOT563", [
            Part.makeBox(1.2, 1.6, 0.45, App.Vector(-0.6, -0.8, 0.1)),
        ] + [Part.makeBox(0.4, 0.25, 0.1, App.Vector(x, y, 0))
             for x in (-0.8, 0.4) for y in (-0.625, -0.125, 0.375)])):
    doc = App.newDocument(name)
    objs = []
    for i, shape in enumerate(shapes):
        if not shape.isValid() or shape.Volume <= 0:
            raise ValueError("Invalid generated package " + name)
        obj = doc.addObject("Part::Feature", "Body" if i == 0 else "Terminal%d" % i)
        obj.Shape = shape
        objs.append(obj)
    doc.recompute()
    Part.export(objs, str(out / (name + ".step")))
    doc.saveAs(str(out.parent / (name + ".FCStd")))
    App.closeDocument(doc.Name)
(out.parent / "package-models.json").write_text(json.dumps({
    "scope": "Datasheet-sized envelope models, not manufacturer CAD; terminal details illustrative",
    "ATtiny85_QFN20": {"body_mm": [4, 4, 0.9], "ep_mm": [2.6, 2.6], "pitch_mm": 0.5,
                       "source": "Microchip ATtiny25/45/85 20M QFN package"},
    "NTZD3154N_SOT563": {"body_mm": [1.2, 1.6, 0.55], "source": "onsemi NTZD3154N/D Rev5 case 463A"},
    "reason": "Explicit nominal package envelopes; no guessed model aliases used"
}, indent=2) + "\n")
