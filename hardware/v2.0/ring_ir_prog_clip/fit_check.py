"""Virtual mechanical fit of the ring_pcb_IR programming clip. Run with FreeCAD's Python.

    & 'C:\\Program Files\\FreeCAD 0.19\\bin\\python.exe' hardware\\v2.0\\ring_ir_prog_clip\\fit_check.py

Inputs are parameters.json (clip-kit estimates, pogo, riser) and
generated/geometry.json (board geometry written by generate.py).  The clip is a
simplified side-profile model of the AliExpress/Adafruit 5434 style clip built
from photo and datasheet estimates, so a pass here is a virtual check only.

Assembly frame: X runs from the lower-jaw tip toward the hinge, Y = probe u,
Z is up from the lower-jaw top at the tip.  X = v - lower_tip_v.
"""

import argparse
import hashlib
import json
import math
import os
import sys

import FreeCAD as App
import MeshPart
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
V = App.Vector
EPS_VOLUME = 1e-3
BOARD = 1.6

COLORS = {
    "LowerJaw": (0.10, 0.10, 0.11), "UpperJaw": (0.16, 0.16, 0.17), "HingePin": (0.70, 0.72, 0.75),
    "Spring": (0.75, 0.77, 0.80), "UBlock": (0.13, 0.13, 0.14),
    "Riser": (0.95, 0.55, 0.15), "Anvil": (0.36, 0.20, 0.52), "Fence": (0.42, 0.25, 0.60),
    "Ring": (0.08, 0.36, 0.20), "RingParts": (0.85, 0.85, 0.80), "Guide": (0.40, 0.22, 0.58),
    "Probe": (0.45, 0.25, 0.65), "Pins": (0.95, 0.76, 0.25), "Header": (0.12, 0.12, 0.12),
    "HeaderPins": (0.95, 0.80, 0.35), "Screws": (0.78, 0.80, 0.82), "Nuts": (0.70, 0.72, 0.74),
}
CLIP = ("LowerJaw", "UpperJaw", "HingePin", "Spring", "UBlock")
# Header pins pass through the header body by design.
ALLOWED = {("Header", "HeaderPins")}


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read().replace(b"\r\n", b"\n")).hexdigest()


def load():
    with open(os.path.join(HERE, "parameters.json"), encoding="utf-8") as handle:
        params = json.load(handle)
    with open(os.path.join(HERE, "generated", "geometry.json"), encoding="utf-8") as handle:
        geometry = json.load(handle)
    return params, geometry


# ------------------------------------------------------------------ primitives

def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, x, y, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))


def prism_xy(points, z0, z1):
    wire = Part.makePolygon([V(x, y, z0) for x, y in points] + [V(points[0][0], points[0][1], z0)])
    return Part.Face(wire).extrude(V(0, 0, z1 - z0))


def profile_xz(points, y0, y1):
    wire = Part.makePolygon([V(x, y0, z) for x, z in points] + [V(points[0][0], y0, points[0][1])])
    return Part.Face(wire).extrude(V(0, y1 - y0, 0))


def slot(cx, cy, length, width, z0, z1):
    r = width / 2
    half = (length - width) / 2
    shape = box(cx - r, cx + r, cy - half, cy + half, z0, z1)
    for dy in (-half, half):
        shape = shape.fuse(cyl(r, cx, cy + dy, z0, z1))
    return shape.removeSplitter()


def rounded_rect(x0, x1, y0, y1, r, z0, z1):
    core = box(x0 + r, x1 - r, y0, y1, z0, z1).fuse(box(x0, x1, y0 + r, y1 - r, z0, z1))
    for x in (x0 + r, x1 - r):
        for y in (y0 + r, y1 - r):
            core = core.fuse(cyl(r, x, y, z0, z1))
    return core.removeSplitter()


def hexagon(cx, cy, across_flats, z0, z1):
    r = across_flats / math.sqrt(3)
    pts = [(cx + r * math.cos(math.radians(30 + 60 * i)), cy + r * math.sin(math.radians(30 + 60 * i)))
           for i in range(6)]
    return prism_xy(pts, z0, z1)


def compound(shapes):
    return Part.makeCompound(shapes)


# ------------------------------------------------------------------- assembly

def frame(params, geometry):
    """Derived stack heights and the uv -> XY map."""
    fi = geometry["fit_inputs"]
    g = params["clip_kit"]["geometry"]
    probe = fi["probe"]
    t_ring = fi["ring"]["thickness"]
    riser = g["parallel_gap_tip"] - (BOARD + t_ring + BOARD)
    lt = probe["lower_tip_v"]
    z = {"riser_top": riser, "anvil_top": riser + BOARD, "ring_top": riser + BOARD + t_ring}
    z["guide_top"] = z["ring_top"] + BOARD
    z["upper_bottom"] = z["guide_top"]
    z["upper_top"] = z["upper_bottom"] + g["upper_tip_thickness"]
    z["probe_top"] = z["upper_top"] + BOARD
    return {"lt": lt, "z": z, "riser": riser, "t_ring": t_ring,
            "xy": lambda u, v: (v - lt, u)}


def board_with_holes(fi, f, z0):
    probe = fi["probe"]
    xy = f["xy"]
    x0, y0 = xy(probe["u_min"], probe["v_min"])
    x1, y1 = xy(probe["u_max"], probe["v_max"])
    shape = rounded_rect(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), probe["corner_radius"], z0, z0 + BOARD)
    cuts = []
    for hole in probe["holes"]:
        x, y = xy(*hole["uv"])
        cuts.append(cyl(hole["d"] / 2, x, y, z0 - 1, z0 + BOARD + 1))
    length, width = probe["slot_size"]
    for u, v in probe["slots"]:
        x, y = xy(u, v)
        cuts.append(slot(x, y, length, width, z0 - 1, z0 + BOARD + 1))
    return shape.cut(compound(cuts))


def clip_parts(params, f):
    g = params["clip_kit"]["geometry"]
    w = g["width"] / 2
    lower_t = g["lower_tip_thickness"]
    throat_rise = g["lower_throat_thickness"] - lower_t
    tip_x, sec_end, ramp = g["upper_tip_setback"], g["upper_tip_section_end"], g["ramp_length"]
    hinge = g["hinge_x"]
    L = g["length"]
    zb = f["z"]["upper_bottom"]
    mid_bottom = throat_rise + g["throat_gap"]
    mid_top = mid_bottom + g["upper_mid_thickness"]
    handle_bottom = mid_bottom + 2.7
    lower = profile_xz([(0, -lower_t), (L, -lower_t), (L, throat_rise), (g["lower_tip_length"] + ramp, throat_rise),
                        (g["lower_tip_length"], 0), (0, 0)], -w, w)
    # Hinge cheeks on the lower jaw carry the pin.
    for side in (-1, 1):
        y0 = side * w - (1.2 if side > 0 else 0)
        lower = lower.fuse(box(hinge - 4, hinge + 4, y0, y0 + 1.2, throat_rise, mid_bottom + 3.5))
    upper = profile_xz([(tip_x, zb), (sec_end, zb), (sec_end + ramp, mid_bottom), (g["upper_mid_end"], mid_bottom),
                        (hinge + 4, mid_bottom), (hinge + 6, handle_bottom), (L, handle_bottom),
                        (L, handle_bottom + 4.4), (hinge + 6, handle_bottom + 4.4), (g["upper_mid_end"], mid_top),
                        (sec_end + ramp, mid_top), (sec_end, zb + g["upper_tip_thickness"]),
                        (tip_x, zb + g["upper_tip_thickness"])], -w + 1.3, w - 1.3)
    upper = upper.fuse(box(tip_x, sec_end, -w, w, zb, zb + g["upper_tip_thickness"])).removeSplitter()
    hole_x = tip_x + g["hole_setback_from_upper_tip"]
    for y in (-g["hole_spacing"] / 2, g["hole_spacing"] / 2):
        upper = upper.cut(cyl(g["hole_drill"] / 2, hole_x, y, zb - 1, zb + g["upper_tip_thickness"] + 1))
    pin_z = (throat_rise + mid_bottom + 2.5) / 2
    hinge_pin = Part.makeCylinder(1.0, 2 * w, V(hinge, -w, pin_z), V(0, 1, 0))
    upper = upper.cut(Part.makeCylinder(1.05, 2 * w, V(hinge, -w, pin_z), V(0, 1, 0)))
    sx = g["spring_x"]
    spring = Part.makeCylinder(2.2, handle_bottom - throat_rise, V(sx, 0, throat_rise)).cut(
        Part.makeCylinder(1.6, handle_bottom - throat_rise, V(sx, 0, throat_rise)))
    ux0, ux1 = g["u_block_x"]
    top = handle_bottom + 4.4
    ublock = box(ux0, ux1, -w, w, top, top + 1.0).fuse(box(ux0, ux1, -w, -w + 1.2, top + 1.0, top + 4.0)).fuse(
        box(ux0, ux1, w - 1.2, w, top + 1.0, top + 4.0))
    return {"LowerJaw": lower.removeSplitter(), "UpperJaw": upper, "HingePin": hinge_pin,
            "Spring": spring, "UBlock": ublock}


def fixture_parts(params, geometry, f):
    fi = geometry["fit_inputs"]
    g = params["clip_kit"]["geometry"]
    xy, z = f["xy"], f["z"]
    ring = fi["ring"]
    parts = {}
    anvil_pts = [xy(*q) for q in fi["anvil"]["outline"]]
    wu0, wv0, wu1, wv1 = fi["anvil"]["window"]
    window = box(wv0 - f["lt"], wv1 - f["lt"], wu0, wu1, z["riser_top"] - 1, z["anvil_top"] + 1)
    parts["Anvil"] = prism_xy(anvil_pts, z["riser_top"], z["anvil_top"]).cut(window)
    ring_pts = [xy(*q) for q in ring["outline"]]
    parts["Ring"] = prism_xy(ring_pts, z["anvil_top"], z["ring_top"])
    heights = params["component_heights_mm"]
    comps = []
    for c in ring["components"]:
        u0, v0, u1, v1 = c["uv"]
        h = heights[c["footprint"]]
        comps.append(box(v0 - f["lt"], v1 - f["lt"], u0, u1, z["anvil_top"] - h, z["anvil_top"]))
    parts["RingParts"] = compound(comps)
    fu0, fv0, fu1, fv1 = fi["fence"]["frame"]
    parts["Fence"] = box(fv0 - f["lt"], fv1 - f["lt"], fu0, fu1, z["anvil_top"], z["ring_top"]).cut(
        prism_xy([xy(*q) for q in fi["fence"]["pocket"]], z["anvil_top"] - 1, z["ring_top"] + 1))
    parts["Guide"] = board_with_holes(fi, f, z["ring_top"])
    parts["Probe"] = board_with_holes(fi, f, z["upper_top"])
    # Printed riser: under the anvil up to the throat, hooked over the lower-jaw tip.
    rp = params["riser"]
    xs = [p[0] for p in anvil_pts]
    ys = [p[1] for p in anvil_pts]
    x_end = g["lower_tip_length"] - rp["throat_margin"]
    riser = box(min(xs), x_end, min(ys), max(ys), 0, z["riser_top"])
    hook = box(-rp["hook_thickness"], 0, -g["width"] / 2 - rp["margin"], g["width"] / 2 + rp["margin"],
               -rp["hook_depth"], 0)
    parts["Riser"] = riser.fuse(hook).removeSplitter()
    # Pogo pins at working compression.
    pogo = params["pogo"]
    c = pogo["working_travel_fraction"] * pogo["rated_travel"]
    pins, pin_report = [], {}
    barrel_bottom = z["ring_top"] + pogo["plunger_exposed_free"] - c
    top_end = barrel_bottom + pogo["length"] - pogo["plunger_exposed_free"]
    for hole in fi["probe"]["holes"]:
        if hole["kind"] != "pogo":
            continue
        x, y = xy(*hole["uv"])
        head = cyl(pogo["head_diameter"] / 2, x, y, z["ring_top"], z["ring_top"] + 0.6)
        plunger = cyl(pogo["plunger_diameter"] / 2, x, y, z["ring_top"] + 0.6, barrel_bottom)
        barrel = cyl(pogo["barrel_diameter"] / 2, x, y, barrel_bottom, top_end)
        pins.append(head.fuse([plunger, barrel]).removeSplitter())
        pad = ring["pads"][hole["ref"]]
        pin_report[hole["ref"]] = {"net": pad["net"], "offset_mm": round(math.hypot(hole["uv"][0] - pad["uv"][0],
                                                                                     hole["uv"][1] - pad["uv"][1]), 4),
                                   "pad_half_width_mm": min(pad["size"]) / 2}
    parts["Pins"] = compound(pins)
    # 2x3 header on the probe, tails into the gap in front of the jaw.
    isp = params["isp_header"]
    hdr = [h for h in fi["probe"]["holes"] if h["kind"] == "header"]
    us = [h["uv"][0] for h in hdr]
    vs = [h["uv"][1] for h in hdr]
    parts["Header"] = box(min(vs) - 1.27 - f["lt"], max(vs) + 1.27 - f["lt"], min(us) - 1.27, max(us) + 1.27,
                          z["probe_top"], z["probe_top"] + isp["body_height"])
    hpins = []
    for h in hdr:
        x, y = xy(*h["uv"])
        hpins.append(box(x - 0.32, x + 0.32, y - 0.32, y + 0.32, z["upper_top"] - isp["tail_below_board"],
                         z["probe_top"] + isp["body_height"] + 6.0))
    parts["HeaderPins"] = compound(hpins)
    # M2 screws through the jaw holes (nominal positions) with nuts under the guide.
    kit = params["clip_kit"]
    head_d, head_h = kit["screw_head"]
    nut_af, nut_h = kit["nut"]
    screws, nuts = [], []
    hole_x = g["upper_tip_setback"] + g["hole_setback_from_upper_tip"]
    for y in (-g["hole_spacing"] / 2, g["hole_spacing"] / 2):
        screws.append(cyl(head_d / 2, hole_x, y, z["probe_top"], z["probe_top"] + head_h).fuse(
            cyl(0.95, hole_x, y, z["probe_top"] - kit["screw_length"], z["probe_top"])))
        nuts.append(hexagon(hole_x, y, nut_af, z["ring_top"] - nut_h, z["ring_top"]).cut(
            cyl(1.0, hole_x, y, z["ring_top"] - nut_h - 1, z["ring_top"] + 1)))
    parts["Screws"] = compound(screws)
    parts["Nuts"] = compound(nuts)
    stack = {"compression_mm": round(c, 3), "barrel_bottom_z": round(barrel_bottom, 3), "pin_top_z": round(top_end, 3),
             "screw_tip_z": round(z["probe_top"] - kit["screw_length"], 3), "hole_x": hole_x}
    return parts, pin_report, stack


# --------------------------------------------------------------------- checks

def interference(parts):
    names = sorted(parts)
    hits, checked = [], 0
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (a in CLIP and b in CLIP) or (a, b) in ALLOWED:
                continue  # clip internals are a visual model
            sa, sb = parts[a], parts[b]
            if not sa.BoundBox.intersect(sb.BoundBox):
                continue
            checked += 1
            volume = sa.common(sb).Volume
            if volume > EPS_VOLUME:
                hits.append({"a": a, "b": b, "volume_mm3": round(volume, 4)})
    return hits, checked


def min_gap(a, b):
    return round(a.distToShape(b)[0], 3)


def margins(params, geometry, f, stack, nominal=None):
    """Analytic clearances, reused by the uncertainty sweep.

    The boards are screwed through the jaw holes, so the jaw is located by the
    slot line: every jaw feature moves relative to the boards when an estimate
    changes.  The printed riser keeps its nominal length (nominal geometry).
    """
    fi = geometry["fit_inputs"]
    g = params["clip_kit"]["geometry"]
    g0 = (nominal or params)["clip_kit"]["geometry"]
    kit = params["clip_kit"]
    probe = fi["probe"]
    pogo = params["pogo"]
    slot_v = probe["slots"][0][1]
    upper_tip_v = slot_v - g["hole_setback_from_upper_tip"]
    lt = upper_tip_v - g["upper_tip_setback"]
    pin_v = [h["uv"][1] for h in probe["holes"] if h["kind"] == "pogo"]
    slot = kit["mount_slot"]
    nut_r = kit["nut"][0] / math.sqrt(3)
    ring_v_max = max(q[1] for q in fi["ring"]["outline"])
    stack_height = f["riser"] + BOARD + f["t_ring"] + BOARD
    tilt = math.degrees(math.atan2(g["parallel_gap_tip"] - stack_height, g["hinge_x"] - g["upper_tip_setback"]))
    riser_end = g0["lower_tip_length"] - params["riser"]["throat_margin"]
    return {
        "lower_tip_v": round(lt, 3),
        "barrel_to_upper_jaw_tip": round(upper_tip_v - max(pin_v) - pogo["barrel_diameter"] / 2, 3),
        "board_end_to_upper_jaw_step": round(upper_tip_v + g["upper_tip_section_end"] - g["upper_tip_setback"]
                                             - probe["v_max"], 3),
        "jaw_hole_inside_slot_along_u": round(min(g["hole_spacing"] / 2 - slot["u_inner"],
                                                  slot["u_outer"] - g["hole_spacing"] / 2), 3),
        "nut_to_fence_and_anvil": round(slot_v - nut_r - fi["fence"]["frame"][3], 3),
        "nut_to_anvil_tail": round(g["hole_spacing"] / 2 - nut_r - params["anvil"]["tail_half_width"], 3),
        "screw_tip_above_riser": round(stack["screw_tip_z"] - f["z"]["riser_top"], 3),
        "riser_end_before_throat": round(g["lower_tip_length"] - riser_end, 3),
        "ring_edge_to_throat": round(g["lower_tip_length"] - (ring_v_max - lt), 3),
        "vcc_pin_over_lower_jaw": round((min(pin_v) - lt), 3),
        "barrel_above_guide": round(stack["barrel_bottom_z"] - f["z"]["guide_top"], 3),
        "head_through_guide_hole": round(pogo["drill"] - pogo["head_diameter"], 3),
        "header_tail_above_guide": round(f["z"]["upper_top"] - params["isp_header"]["tail_below_board"]
                                         - f["z"]["guide_top"], 3),
        "jaw_tilt_deg": round(tilt, 3),
    }


LIMITS = {
    "barrel_to_upper_jaw_tip": 0.2, "board_end_to_upper_jaw_step": 0.0, "jaw_hole_inside_slot_along_u": 0.0,
    "nut_to_fence_and_anvil": 0.1, "nut_to_anvil_tail": 0.1, "screw_tip_above_riser": 0.2,
    "riser_end_before_throat": 0.1, "ring_edge_to_throat": 0.5, "barrel_above_guide": 0.2,
    "head_through_guide_hole": 0.1, "header_tail_above_guide": 0.3,
}


def margin_failures(m):
    out = [k for k, limit in LIMITS.items() if m[k] < limit]
    if abs(m["jaw_tilt_deg"]) > 3.0:
        out.append("jaw_tilt_deg")
    return out


SWEEP = ("upper_tip_setback", "hole_setback_from_upper_tip", "hole_spacing", "parallel_gap_tip",
         "upper_tip_section_end", "lower_tip_length")


def sweep(params, geometry, f, stack):
    """Vary each clip estimate by +/- uncertainty with the boards and riser fixed."""
    du = params["clip_kit"]["uncertainty"]
    results = []
    for key in SWEEP:
        for sign in (-1, 1):
            p = json.loads(json.dumps(params))
            p["clip_kit"]["geometry"][key] += sign * du
            m = margins(p, geometry, f, stack, nominal=params)
            results.append({"dimension": key, "delta_mm": sign * du, "failures": margin_failures(m), "margins": m})
    return results


# --------------------------------------------------------------------- render

def mesh(shape):
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.04, AngularDeflection=0.35, Relative=False)
    m.removeDuplicatedPoints()
    return m


def render(parts, output, eye, width=1000, light=(0.35, -0.45, 0.82), crop=None):
    import importlib.util
    import numpy as np
    if importlib.util.find_spec("PySide6"):
        from PySide6 import QtGui
    else:
        from PySide2 import QtGui
    e = np.array(eye, dtype=float)
    e /= np.linalg.norm(e)
    up = np.array([0.0, 0.0, 1.0]) if abs(e[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
    right = np.cross(up, e)
    right /= np.linalg.norm(right)
    upv = np.cross(e, right)
    lv = np.array(light) / np.linalg.norm(light)
    tris = []
    for name, shape in parts.items():
        base = COLORS[name]
        m = mesh(shape)
        for facet in m.Facets:
            n = np.array([facet.Normal.x, facet.Normal.y, facet.Normal.z])
            if n.dot(e) <= 0:
                continue
            k = 0.45 + 0.55 * max(0.0, n.dot(lv))
            color = tuple(int(min(255, c * k * 255 + 18)) for c in base)
            pts = [np.array(p) for p in facet.Points]
            tris.append(([(p.dot(right), -p.dot(upv), p.dot(e)) for p in pts], color))
    xs = [p[0] for t, _ in tris for p in t]
    ys = [p[1] for t, _ in tris for p in t]
    min_x, max_x, min_y, max_y = min(xs) - 3, max(xs) + 3, min(ys) - 3, max(ys) + 3
    if crop:
        min_x, max_x, min_y, max_y = crop
    scale = width / (max_x - min_x)
    height = int(math.ceil((max_y - min_y) * scale))
    rgb = np.full((height, width, 3), 246, dtype=np.uint8)
    depth = np.full((height, width), -np.inf)
    for pts, color in tris:
        v = np.array([((x - min_x) * scale, (y - min_y) * scale, d) for x, y, d in pts])
        left, right_ = max(0, int(math.floor(v[:, 0].min()))), min(width, int(math.ceil(v[:, 0].max())) + 1)
        top, bottom = max(0, int(math.floor(v[:, 1].min()))), min(height, int(math.ceil(v[:, 1].max())) + 1)
        if left >= right_ or top >= bottom:
            continue
        (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = v
        det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(det) < 1e-10:
            continue
        gy, gx = np.mgrid[top:bottom, left:right_] + 0.5
        a = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / det
        b = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / det
        c = 1 - a - b
        d = a * z0 + b * z1 + c * z2
        region = depth[top:bottom, left:right_]
        visible = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6) & (d > region)
        region[visible] = d[visible]
        rgb[top:bottom, left:right_][visible] = color
    image = QtGui.QImage(rgb.data, width, height, width * 3, QtGui.QImage.Format_RGB888).copy()
    if not image.save(output):
        raise SystemExit("could not save " + output)


def section(parts, y_cut):
    out = {}
    keep = box(-100, 120, y_cut, 100, -100, 100)
    for name, shape in parts.items():
        cut = shape.common(keep)
        if cut.Volume > EPS_VOLUME:
            out[name] = cut
    return out


# ----------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=os.path.join(HERE, "generated", "fit"))
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)
    params, geometry = load()
    f = frame(params, geometry)
    clip = clip_parts(params, f)
    fixture, pins, stack = fixture_parts(params, geometry, f)
    parts = dict(clip, **fixture)
    for name, shape in parts.items():
        if not shape.isValid():
            raise SystemExit("invalid solid " + name)
    hits, checked = interference(parts)
    m = margins(params, geometry, f, stack)
    gaps = {
        "pins_to_upper_jaw": min_gap(parts["Pins"], parts["UpperJaw"]),
        "ring_parts_to_riser": min_gap(parts["RingParts"], parts["Riser"]),
        "nuts_to_fence": min_gap(parts["Nuts"], parts["Fence"]),
        "nuts_to_anvil": min_gap(parts["Nuts"], parts["Anvil"]),
        "screws_to_riser": min_gap(parts["Screws"], parts["Riser"]),
        "header_pins_to_guide": min_gap(parts["HeaderPins"], parts["Guide"]),
    }
    contacts = {
        "riser_on_lower_jaw": min_gap(parts["Riser"], parts["LowerJaw"]),
        "guide_on_ring": min_gap(parts["Guide"], parts["Ring"]),
        "upper_jaw_on_guide": min_gap(parts["UpperJaw"], parts["Guide"]),
        "pins_on_ring": min_gap(parts["Pins"], parts["Ring"]),
        "probe_on_upper_jaw": min_gap(parts["Probe"], parts["UpperJaw"]),
    }
    sweep_results = sweep(params, geometry, f, stack)
    pogo = params["pogo"]
    failures = margin_failures(m)
    failures += ["interference %s/%s" % (h["a"], h["b"]) for h in hits]
    failures += ["pin %s off pad" % ref for ref, r in pins.items() if r["offset_mm"] > 0.05]
    failures += ["contact %s" % k for k, v in contacts.items() if v > 1e-3]
    compression = stack["compression_mm"] / pogo["rated_travel"]
    if not 0.3 <= compression <= 0.8:
        failures.append("pin compression %.2f of travel" % compression)
    report = {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "scope": "Virtual FreeCAD fit against photo/datasheet estimates of the clip; no physical fit, contact or programming test",
        "clip_dimensions_measured": params["clip_kit"]["measured"],
        "freecad_version": ".".join(App.Version()[:3]),
        "riser_thickness_mm": round(f["riser"], 3),
        "stack_z_mm": {k: round(v, 3) for k, v in f["z"].items()},
        "pin_compression_mm": stack["compression_mm"],
        "pin_compression_fraction": round(compression, 3),
        "pins": pins,
        "interference_pairs_checked": checked,
        "interference": hits,
        "contacts_mm": contacts,
        "min_gaps_mm": gaps,
        "margins_mm": m,
        "margin_limits_mm": LIMITS,
        "uncertainty_mm": params["clip_kit"]["uncertainty"],
        "sweep": sweep_results,
        "sweep_sensitive": sorted({"%s %+.1f: %s" % (r["dimension"], r["delta_mm"], ", ".join(r["failures"]))
                                   for r in sweep_results if r["failures"]}),
        "inputs_sha256": {name: sha256(os.path.join(HERE, *name.split("/")))
                          for name in ("parameters.json", "generated/geometry.json", "fit_check.py")},
    }
    doc = App.newDocument("ring_ir_prog_clip_fit")
    for name, shape in parts.items():
        doc.addObject("Part::Feature", name).Shape = shape
    doc.recompute()
    for stale in ("clip_fit.FCStd", "clip_fit.FCStd1"):
        if os.path.exists(os.path.join(args.output, stale)):
            os.remove(os.path.join(args.output, stale))
    doc.saveAs(os.path.join(args.output, "clip_fit.FCStd"))
    Part.makeCompound([parts[n] for n in sorted(parts)]).exportStep(os.path.join(args.output, "clip_fit.step"))
    riser_mesh = mesh(parts["Riser"])
    if not riser_mesh.isSolid():
        raise SystemExit("riser mesh is not watertight")
    riser_mesh.write(os.path.join(args.output, "Riser.stl"))
    parts["Riser"].exportStep(os.path.join(args.output, "Riser.step"))
    if not args.no_render:
        render(parts, os.path.join(args.output, "clipped_iso.png"), (-0.9, -1.25, 0.95), 1100)
        near = {k: v for k, v in parts.items() if k not in ("Spring", "UBlock")}
        # Keep the +Y half and look from -Y so X (toward the hinge) runs left to right.
        sec = section(near, 0.0)
        render(sec, os.path.join(args.output, "clipped_section.png"), (0.0, -1.0, 0.0), 1100,
               light=(0.3, -0.9, 0.4), crop=(-17.0, 34.0, -26.0, 6.0))
        lift = {"Riser": 0, "LowerJaw": -14, "Anvil": 8, "Ring": 16, "RingParts": 16, "Fence": 24, "Guide": 32,
                "Nuts": 30, "UpperJaw": 40, "HingePin": 40, "Spring": 40, "UBlock": 40, "Probe": 48,
                "Header": 48, "HeaderPins": 48, "Pins": 56, "Screws": 64}
        exploded = {}
        for name, shape in parts.items():
            s = shape.copy()
            s.translate(V(0, 0, lift[name]))
            exploded[name] = s
        render(exploded, os.path.join(args.output, "clipped_exploded.png"), (-0.9, -1.25, 0.55), 1100)
    report["outputs"] = sorted(os.listdir(args.output))
    with open(os.path.join(args.output, "fit_validation.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({k: report[k] for k in ("status", "failures", "riser_thickness_mm", "pin_compression_mm",
                                             "margins_mm", "min_gaps_mm", "sweep_sensitive")}, indent=1))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
