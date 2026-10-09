"""Low-profile Lantern Corps top pieces ("crowns") for the v2 cassette.

Run with FreeCAD's Python:
    python crowns.py              build every crown from logos/logos.json
    python crowns.py --extract    re-trace logos from the v1 FreeCAD sketches first

Each crown is the v2 bezel (same PCB-edge clamp, M1 screw clearances and
ground-lead relief) extended by a skirt that clears the LEDs, a diffuser lens
that ties floating logo islands together, and a shallow logo relief.
"""

import argparse
import json
import math
from pathlib import Path
import sys

import FreeCAD as App
import Mesh
import MeshPart
import Part

from design import (HERE, PCB_PATH, artifact_hash, load_parameters, offset_polygon,
                    pcb_interface, source_hash, validate_parameters)
from lantern_ring import (Z, bop_check, box, cylinder, geometry, mesh_for, polygon_solid,
                          screw_positions, unrotated_geometry)

LOGOS = HERE / "logos" / "logos.json"
V1_DOCUMENT = HERE.parents[1] / "v1.0" / "ring_3d" / "Lantern_Ring_Assembly.FCStd"
# v1 logo sketches are drawn about the v1 setting centre in the v1 assembly frame.
V1_SETTING_CENTRE = (-3.4, -23.3)
V1_SKIP = ("riser", "support", "slot", "fric")

CROWN = {
    "led_clearance": 0.2,   # lens underside above the tallest LED
    "lens": 0.4,            # two 0.2 mm layers of translucent diffuser
    "relief": 0.6,          # raised logo strokes
    "counterbore": 2.2,     # M1 head (OD <= 2 mm) seats at the original bezel top
    "logo_rotation": 0.0,   # degrees, relative to the v1 orientation when locked
}

# key: (v1 group prefix, corps, emotional-spectrum light, render colour)
CORPS = {
    "will": ("will", "Green Lantern Corps", "willpower", (0.05, 0.75, 0.20)),
    "fear": ("fear", "Sinestro Corps", "fear", (1.00, 0.82, 0.05)),
    "rage": ("rage", "Red Lantern Corps", "rage", (0.85, 0.04, 0.04)),
    "avarice": ("avarice", "Orange Lantern (Agent Orange)", "avarice", (1.00, 0.42, 0.00)),
    "hope": ("hope", "Blue Lantern Corps", "hope", (0.10, 0.35, 1.00)),
    "compassion": ("empathy", "Indigo Tribe", "compassion", (0.28, 0.08, 0.62)),
    "love": ("love", "Star Sapphires", "love", (0.62, 0.15, 0.88)),
    "life": ("rebirth", "White / Black Lantern", "life and death", (0.92, 0.93, 0.96)),
}


def extract_logos(path=V1_DOCUMENT):
    """Trace each corps logo layer from the v1 assembly into tool-neutral polylines."""
    doc = App.openDocument(str(path))
    logos = {}
    for key, (prefix, corps, light, _) in CORPS.items():
        group = doc.getObjectsByLabel(prefix + "_logo")[0]
        members = [o for o in group.Group if hasattr(o, "Shape") and o.Shape.Solids
                   and not any(word in o.Label for word in V1_SKIP)]
        extrude = next(o for o in members if o.Label.endswith("_extrude"))
        z = extrude.Shape.BoundBox.ZMin + 0.5
        shapes = [o.Shape for o in members]
        fused = shapes[0].fuse(shapes[1:]) if len(shapes) > 1 else shapes[0]
        face = Part.makeFace(fused.slice(Z, z), "Part::FaceMakerBullseye")
        face.translate(App.Vector(-V1_SETTING_CENTRE[0], -V1_SETTING_CENTRE[1], -z))
        loops = []
        for wire in (w for f in face.Faces for w in f.Wires):
            points = [(round(v.x, 4), round(v.y, 4)) for v in wire.discretize(Deflection=0.01)]
            if points[0] != points[-1]:
                points.append(points[0])
            loops.append(points)
        logos[key] = {"corps": corps, "light": light, "v1_group": prefix + "_logo",
                      "area_mm2": round(face.Area, 3), "loops": loops}
    App.closeDocument(doc.Name)
    LOGOS.parent.mkdir(exist_ok=True)
    LOGOS.write_text(json.dumps({"units": "mm", "source": V1_DOCUMENT.name,
                                 "frame": "centred on the ring axis; finger axis is +Y",
                                 "fill_rule": "evenodd", "logos": logos}, indent=1) + "\n",
                     encoding="utf-8")
    for key, logo in logos.items():
        write_svg(key, logo)
    return logos


def write_svg(key, logo, radius=11.7):
    paths = " ".join("M" + " L".join("{:.4f},{:.4f}".format(x, -y) for x, y in loop) + " Z"
                     for loop in logo["loops"])
    size = 2 * radius
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="{0}mm" height="{0}mm" '
           'viewBox="{1} {1} {0} {0}">\n<title>{2} ({3}) - Lantern Ring v2 crown logo</title>\n'
           '<circle r="{4}" fill="none" stroke="#999" stroke-width="0.05"/>\n'
           '<path fill-rule="evenodd" fill="#000" d="{5}"/>\n</svg>\n').format(
               size, -radius, logo["corps"], logo["light"], radius, paths)
    (LOGOS.parent / (key + ".svg")).write_text(svg, encoding="utf-8")


def clean_loop(loop, min_edge=0.01, max_dev=0.002):
    """Drop duplicate/near-collinear vertices; sliver edges break STEP round-trips."""
    pts = []
    for pt in loop:
        if not pts or math.dist(pt, pts[-1]) >= min_edge:
            pts.append(pt)
    while len(pts) > 3 and math.dist(pts[0], pts[-1]) < min_edge:
        pts.pop()
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            ac = math.dist(a, c)
            cross = abs((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0]))
            if ac < min_edge or cross / ac < max_dev:
                del pts[i]
                changed = True
                break
    return pts


def logo_face(loops, rotation):
    wires = []
    for loop in loops:
        pts = [App.Vector(x, y, 0) for x, y in clean_loop(loop)]
        wires.append(Part.makePolygon(pts + pts[:1]))
    face = Part.makeFace(wires, "Part::FaceMakerBullseye")
    face.rotate(App.Vector(), Z, rotation)
    return face


def build_crown(p, pcb, loops):
    """Crown in the unlocked cassette frame (same frame as unrotated_geometry)."""
    s = validate_parameters(p, pcb)
    radius = p["screw_radius"] + p["screw_post_radius"]
    lens_bottom = s["highest_component"] + CROWN["led_clearance"]
    relief_bottom = lens_bottom + CROWN["lens"]
    top = relief_bottom + CROWN["relief"]
    window = offset_polygon(pcb["outline"], -0.45)
    skirt = cylinder(radius, s["assembly_top"] - 0.05, lens_bottom).cut(
        polygon_solid(window, s["assembly_top"] - 0.1, lens_bottom + 0.1))
    lens = cylinder(radius, lens_bottom, relief_bottom)
    # Pre-rotate so the emblem reads in the v1 orientation once the cassette is locked.
    face = logo_face(loops, CROWN["logo_rotation"] - p["lock_angle"])
    # Embed the relief 0.05 mm: a coplanar polygon-on-cylinder fuse is invalid in OCC 7.5.
    face.translate(App.Vector(0, 0, relief_bottom - 0.05))
    relief = face.extrude(Z * (CROWN["relief"] + 0.05)).common(
        cylinder(radius, relief_bottom - 0.1, top + 0.1))
    crown = unrotated_geometry(p, pcb)["Bezel"].fuse(skirt)
    # Fuse each relief island separately; a compound fuse inverts a solid in OCC 7.5.
    crown = crown.fuse(lens.multiFuse(relief.Solids).removeSplitter()).removeSplitter()
    for x, y in screw_positions(p):
        crown = crown.cut(cylinder(CROWN["counterbore"] / 2, s["assembly_top"], top + 1, x, y))
    wire_x, wire_y, wire_r = pcb["ground"][0], p["wire_channel_y"], p["wire_channel_diameter"] / 2
    crown = crown.cut(box(p["wire_channel_diameter"], wire_y - pcb["ground"][1] + 0.8,
                          s["pcb_top"] - 0.01, s["pcb_top"] + 0.9, wire_x - wire_r,
                          pcb["ground"][1] - 0.4))
    levels = {"lens_bottom": lens_bottom, "relief_bottom": relief_bottom, "top": top}
    return crown.removeSplitter(), levels


def validate_crown(key, crown, levels, p, pcb, s, locked_parts):
    if not crown.isValid() or len(crown.Solids) != 1:
        raise ValueError("{} crown must be one valid solid".format(key))
    bop_check(crown)
    locked = crown.copy()
    locked.rotate(App.Vector(), Z, p["lock_angle"])
    for name, part in locked_parts.items():
        if name == "Bezel":
            continue
        overlap = locked.common(part).Volume
        if overlap > 1e-6:
            raise ValueError("{} crown interferes with {} ({:.4f} mm3)".format(key, name, overlap))
    led_gap = locked.distToShape(locked_parts["LEDs"])[0]
    if led_gap < CROWN["led_clearance"] - 1e-6:
        raise ValueError("{} crown is {:.3f} mm from an LED".format(key, led_gap))
    radius = p["screw_radius"] + p["screw_post_radius"]
    if crown.common(cylinder(radius, -50, 50)).Volume < crown.Volume - 1e-6:
        raise ValueError("{} crown exceeds the bezel diameter".format(key))
    return {
        "volume_mm3": round(crown.Volume, 3),
        "top_above_pcb_mm": round(levels["top"] - s["pcb_top"], 3),
        "top_above_leds_mm": round(levels["top"] - s["highest_component"], 3),
        "profile_above_finger_mm": round(s["profile_above_finger"]
                                         + levels["top"] - s["highest_component"], 3),
        "led_clearance_mm": round(led_gap, 3),
        "diameter_mm": round(2 * radius, 3),
    }


def generate(output=HERE / "generated" / "crowns", extract=False):
    output.mkdir(parents=True, exist_ok=True)
    p, pcb = load_parameters(HERE / "parameters.json"), pcb_interface()
    s = validate_parameters(p, pcb)
    logos = extract_logos() if extract else json.loads(LOGOS.read_text(encoding="utf-8"))["logos"]
    locked_parts = geometry(json.dumps(p, sort_keys=True), json.dumps(pcb, sort_keys=True))
    report = {}
    for key in CORPS:
        crown, levels = build_crown(p, pcb, logos[key]["loops"])
        checks = validate_crown(key, crown, levels, p, pcb, s, locked_parts)
        # OCC 7.5 cannot round-trip these faceted crowns through STEP after an
        # off-axis rotation, so STEP stays in the cassette (insertion) frame.
        step = output / "Crown_{}.step".format(key)
        crown.exportStep(str(step))
        loaded = Part.read(str(step))
        if not loaded.isValid() or abs(loaded.Volume - crown.Volume) > 0.01:
            raise ValueError("{} crown STEP reload failed".format(key))
        # Print logo-face down: the relief is the first layers and the lens bridges it.
        printed = crown.copy()
        printed.rotate(App.Vector(), App.Vector(1, 0, 0), 180)
        printed.translate(App.Vector(0, 0, -printed.BoundBox.ZMin))
        mesh = mesh_for(printed, p)
        if not mesh.isSolid():
            raise ValueError("{} crown mesh is not watertight".format(key))
        mesh.write(str(output / "Crown_{}.stl".format(key)))
        checks.update(corps=logos[key]["corps"], light=logos[key]["light"],
                      logo_area_mm2=logos[key]["area_mm2"])
        report[key] = checks
        print("{:10s} top {:.2f} mm above PCB, {:.0f} mm3".format(
            key, checks["top_above_pcb_mm"], checks["volume_mm3"]))
    result = {
        "freecad_version": ".".join(App.Version()[:3]),
        "pcb_sha256": source_hash(PCB_PATH),
        "source_sha256": {name: source_hash(HERE / name)
                          for name in ("crowns.py", "design.py", "lantern_ring.py")},
        "logos_sha256": source_hash(LOGOS),
        "parameters": p,
        "crown": CROWN,
        "step_frame": "cassette insertion pose; rotate +lock_angle about Z for the locked pose",
        "levels": {"pcb_top": s["pcb_top"], "bezel_top": s["assembly_top"],
                   "led_top": s["highest_component"], **levels},
        "v1_logo_reference_mm": {"setting_top_to_logo_top": 5.0, "v1_logo_cap_height": 6.5},
        "crowns": report,
        "artifact_sha256": {path.name: artifact_hash(path) for path in sorted(output.iterdir())
                            if path.suffix.lower() in (".step", ".stl")},
        "physical_test_status": "NOT PRINTED: lens light, relief legibility and M1 counterbores need a test print",
    }
    (output / "crowns.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Generated {} crowns in {}".format(len(report), output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", action="store_true", help="re-trace logos from the v1 FCStd")
    parser.add_argument("--output", type=Path, default=HERE / "generated" / "crowns")
    args = parser.parse_args()
    try:
        generate(args.output, args.extract)
    except Exception as error:
        print("Crown generation FAILED: {}".format(error), file=sys.stderr)
        raise
