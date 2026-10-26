"""Portable pitch/contact checks; FreeCAD geometry is in assembly_model.py."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    return json.loads((HERE / "assembly_parameters.json").read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def artifact_sha256(path):
    path = Path(path)
    data = path.read_bytes()
    if path.suffix in (".step", ".json"):
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def stock_grid(pitch, columns=6, rows=2):
    return [(1.5 + row * pitch, (column - (columns - 1) / 2) * pitch)
            for row in range(rows) for column in range(columns)]


def ir_contacts():
    geometry = json.loads((HERE / "generated" / "geometry.json").read_text())
    board = HERE / geometry["target_board"]
    if sha256(board) != geometry["target_sha256"]:
        raise ValueError("IR geometry is stale: regenerate the clip from the current PCB")
    return geometry["fit_inputs"]["ring"]["pads"]


def compatibility(pitch, tip_diameter, uncertainty):
    """Best centre-aligned 3x2 grid, optimistically ignoring the extra stock pins.

    Offsets use actual square pad boundaries, not a circular proxy. Full tip
    containment must survive the specified XY registration uncertainty.
    """
    pads = ir_contacts()
    refs = ["TP1", "TP2", "TP3", "TP4", "TP5", "TP6"]
    cx = sum(pads[r]["uv"][0] for r in refs) / 6
    cy = sum(pads[r]["uv"][1] for r in refs) / 6
    us = sorted({round(pads[r]["uv"][0], 6) for r in refs})
    vs = sorted({round(pads[r]["uv"][1], 6) for r in refs})
    pitch_u = us[1] - us[0]
    pitch_v = vs[1] - vs[0]
    results = []
    for ref in refs:
        p = pads[ref]
        u, v = p["uv"]
        point = (cx + (u - cx) * pitch / pitch_u,
                 cy + (v - cy) * pitch / pitch_v)
        delta = [point[0] - u, point[1] - v]
        margin = min(size / 2 - abs(d) - tip_diameter / 2 - uncertainty
                     for size, d in zip(p["size"], delta))
        results.append({"ref": ref, "net": p["net"], "pad_uv": p["uv"],
                        "pin_uv": list(point), "offset_mm": round(math.hypot(*delta), 4),
                        "containment_margin_mm": round(margin, 4)})
    return {"pitch_mm": pitch, "tip_diameter_mm": tip_diameter,
            "registration_uncertainty_mm": uncertainty, "signal_contacts": results,
            "signals_fully_contained": all(p["containment_margin_mm"] >= 0 for p in results),
            "direct_isp_compatible": False,
            "reason": "VCC TP9 is off-grid; GND TP8 is on the front face. "
                      "Stock header wiring is not the AVR ISP pinout."}
