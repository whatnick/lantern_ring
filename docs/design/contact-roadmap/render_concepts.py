"""Local FreeCAD roadmap illustrations, NOT Nano Banana or engineering exports."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CAD = HERE.parents[2] / "hardware" / "v2.0" / "ring_3d"
sys.path.insert(0, str(CAD))

import lantern_ring as L


def shifted(shape, lift=0, x=0, y=0):
    result = shape.copy()
    result.translate(L.App.Vector(x, y, lift))
    return result


def label_image(path, title):
    import importlib.util
    if importlib.util.find_spec("PySide6"):
        from PySide6 import QtGui
    else:
        from PySide2 import QtGui
    source = QtGui.QImage(str(path))
    if source.isNull():
        raise ValueError("Cannot read rendered image")
    image = QtGui.QImage(source.width(), source.height() + 82, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor("#f4f6f8"))
    painter = QtGui.QPainter(image)
    painter.drawImage(0, 82, source)
    painter.setPen(QtGui.QColor("#203040"))
    painter.setFont(QtGui.QFont("Arial", 16))
    painter.drawText(24, 32, title)
    painter.setFont(QtGui.QFont("Arial", 11))
    painter.drawText(24, 64,
                     "LOCAL FREECAD CONCEPT | NOT NANO BANANA | NOT QUALIFIED HARDWARE")
    painter.end()
    if not any(image.pixelColor(x, y).name() != "#f4f6f8"
               for y in range(8, 72) for x in range(24, image.width() - 24)):
        raise ValueError("Concept provenance label did not render")
    if not image.save(str(path)):
        raise ValueError("Cannot save labelled concept")


def contact_scene(p, pcb, raw, spring=False, metal=False):
    s = L.validate_parameters(p, pcb)
    parts = {name: shape.copy() for name, shape in raw.items()
             if name not in ("PositiveLead", "NegativeLead")}
    # Exploded layers reveal pad-side contact topology, not assembly motion.
    lifts = {"Carrier": 8, "Battery": 8, "NegativePogo": 8,
             "ContactDeck": 18, "PositivePogo": 18, "PCB": 25,
             "LEDs": 25, "Bezel": 35}
    for name in list(parts):
        parts[name] = shifted(parts[name], lifts.get(name, 0))
    px, py = pcb["positive"]
    gx, gy = pcb["ground"]
    bottom = p["pcb_bottom"] + 25
    top = s["pcb_top"] + 25
    if spring:
        # Stylised leaf profiles show opposing preload; not fatigue/force geometry.
        upward = L.polygon_solid([
            (-2.4, bottom - 2.4), (-0.4, bottom - 0.7), (0.4, bottom - 0.7),
            (0.4, bottom - 0.5), (-0.5, bottom - 0.5), (-2.4, bottom - 2.2),
        ], -0.9, 0.9)
        # polygon_solid is XY extruded along Z; rotate into the XZ section.
        upward.rotate(L.App.Vector(), L.App.Vector(1, 0, 0), 90)
        parts["PositiveLeaf"] = shifted(upward, 0, px, py)
        downward = L.polygon_solid([
            (gy - 0.6, top + 0.7), (gy + 1.0, top + 1.4),
            (p["wire_channel_y"], top + 1.4), (p["wire_channel_y"], top + 1.6),
            (gy + 0.95, top + 1.6), (gy - 0.6, top + 0.9),
        ], -0.8, 0.8)
        downward.rotate(L.App.Vector(), L.App.Vector(1, 0, 0), 90)
        downward.rotate(L.App.Vector(), L.Z, 90)
        parts["GroundLeaf"] = shifted(downward, 0, gx, 0)
        parts["PositiveCapture"] = L.box(2.0, 3.0, bottom - 3.0, bottom - 2.0, px - 3.0, py - 1.5)
        parts["GroundCapture"] = L.box(2.8, 1.8, top + 0.9, top + 2.4, gx - 1.4, p["wire_channel_y"] - 0.5)
    else:
        parts["PositiveFoil"] = L.box(3.2, 3.2, bottom - 0.6, bottom - 0.5, px - 1.6, py - 1.6)
        parts["GroundFoil"] = L.box(1.2, 5.5, top + 0.5, top + 0.6, gx - 0.6, gy - 0.6)
        parts["PositiveBacking"] = L.box(3.2, 3.2, bottom - 2.0, bottom - 0.6, px - 1.6, py - 1.6)
        parts["GroundBacking"] = L.box(1.8, 2.2, top + 0.6, top + 1.8, gx - 0.9, gy - 0.8)
    # Demonstrative separate copper paths with insulating channel boundaries.
    parts["PositiveTrace"] = L.box(1.2, 3.2, s["positive_flange"] + 18 + 1.0,
                                   s["positive_flange"] + 18 + 1.15, px - 0.6, py - 0.6)
    parts["GroundTrace"] = L.box(1.2, 5.0, s["pcb_top"] + 8 - 1.4,
                                 s["pcb_top"] + 8 - 1.25, gx - 0.6, gy - 0.3)
    colors = dict(L.COLORS)
    for name in parts:
        if any(term in name for term in ("Foil", "Trace")):
            colors[name] = (0.86, 0.44, 0.19)
        elif "Leaf" in name:
            colors[name] = (0.90, 0.74, 0.28)
        elif any(term in name for term in ("Backing", "Capture")):
            colors[name] = (0.26, 0.62, 0.85)
    if metal:
        colors["RingBase"] = (0.72, 0.76, 0.81)
        # Green sleeve explicitly separates the decorative shell and cassette.
        parts["InsulatingLiner"] = L.cylinder(p["socket_radius"] - 0.1, 2.0, 8.0).cut(
            L.cylinder(p["carrier_radius"] - 0.4, 1.9, 8.1))
        colors["InsulatingLiner"] = (0.23, 0.62, 0.44)
    return parts, colors


def generate(output=HERE / "images" / "local-freecad"):
    import importlib.util
    if importlib.util.find_spec("PySide6"):
        from PySide6 import QtGui
    else:
        from PySide2 import QtGui
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication(["contact-roadmap"])
    font_database = QtGui.QFontDatabase()
    if not font_database.families() and os.name == "nt":
        # Windows' offscreen Qt plugin does not discover installed fonts itself.
        font = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf"
        if QtGui.QFontDatabase.addApplicationFont(str(font)) < 0:
            raise ValueError("Cannot load font for required concept provenance labels")
    if not font_database.families():
        raise ValueError("No font available for required concept provenance labels")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    p, pcb = L.load_parameters(), L.pcb_interface()
    raw = L.unrotated_geometry(p, pcb)
    original_colors = L.COLORS
    records = []
    specs = [
        ("01-serviceable-pogo", "01  Serviceable pogo baseline", False, False),
        ("02-copper-pressure", "02  Copper foil + silicone preload", False, False),
        ("03-plated-springs", "03  Replaceable plated leaf contacts", True, False),
        ("04-floating-metal", "04  Floating metal shell + insulating insert", True, True),
    ]
    try:
        for name, title, spring, metal in specs:
            if name == "01-serviceable-pogo":
                parts = {n: shifted(shape, {"Bezel": 28, "PCB": 21, "LEDs": 21,
                                            "ContactDeck": 14, "PositivePogo": 14,
                                            "PositiveLead": 14, "Carrier": 6, "Battery": 6,
                                            "NegativePogo": 6, "NegativeLead": 6}.get(n, 0))
                         for n, shape in raw.items()}
                colors = dict(original_colors)
            else:
                parts, colors = contact_scene(p, pcb, raw, spring, metal)
            L.COLORS = {part: colors[part] for part in parts}
            path = output / (name + ".png")
            L.preview_png(parts, p, path)
            label_image(path, title)
            records.append({
                "file": path.name,
                "stage": name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "status": "Local FreeCAD illustrative geometry; NOT Nano Banana; NOT validated assembly",
            })
    finally:
        L.COLORS = original_colors
    manifest = {
        "generator": "Local FreeCAD concept renderer",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nano_banana_status": "BLOCKED: no Gemini API authentication available",
        "geometry_status": "Stage 1 references the existing CAD; later stages are illustrative overlays only",
        "images": records,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Rendered {} local concept images; no Nano Banana requests made.".format(len(records)))


if __name__ == "__main__":
    generate()
