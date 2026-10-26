"""FreeCAD reconstruction of the photographed kit, separate from production PCBs."""
import copy
import json
import math
from pathlib import Path

import FreeCAD as App
import MeshPart
import Part

import assembly_interface as interface
import fit_check as fit

HERE = Path(__file__).resolve().parent
OUT = HERE / "generated" / "assembly"
V = App.Vector
EPS = 1e-3
COLORS = dict(fit.COLORS, UpperJaw=(0.13, 0.17, 0.21), LowerJaw=(0.08, 0.11, 0.15),
              Grip=(0.18, 0.22, 0.26), Hinge=(0.65, 0.68, 0.72),
              Spring=(0.70, 0.73, 0.78), Probe=(0.42, 0.12, 0.54),
              Guide=(0.32, 0.10, 0.43), Pads=(0.95, 0.72, 0.22))


def cylinder(radius, length, origin, direction=(0, 0, 1)):
    return Part.makeCylinder(radius, length, V(*origin), V(*direction))


def hinge_bore(shape, cfg):
    e = cfg["estimated"]
    return shape.cut(cylinder(e["hinge_radius"] + 0.1, 30,
                             (e["hinge_x"], -15, e["hinge_z"]), (0, 1, 0)))


def spring_height(e, angle):
    a = math.radians(angle)
    seat_z = e["hinge_z"] + (
        e["working_gap"] + e["spring_wire_radius"] * 2 - e["hinge_z"]
        - math.sin(a) * (e["spring_x"] - e["hinge_x"])) / math.cos(a)
    seat_z -= e["spring_radius"] * abs(math.tan(a))
    return seat_z - e["spring_wire_radius"] * 2


def helix_spring(e, angle=0):
    height = spring_height(e, angle)
    path = Part.makeHelix(height / e["spring_turns"], height, e["spring_radius"])
    start = path.Vertexes[0].Point
    wire = Part.Wire([Part.makeCircle(e["spring_wire_radius"], start,
                                     path.Edges[0].tangentAt(0))])
    shape = Part.Wire(path.Edges).makePipeShell([wire], True, False)
    shape.translate(V(e["spring_x"], 0, e["spring_wire_radius"]))
    return shape


def kit(cfg):
    e = cfg["estimated"]
    length = cfg["measurements"]["body_length"]["mm"]
    width = cfg["measurements"]["body_width"]["mm"]
    w, thick, gap = width / 2, e["jaw_tip_thickness"], e["working_gap"]
    hx, hz = e["hinge_x"], e["hinge_z"]
    lower = fit.box(0, length, -w, w, -thick, 0)
    for y in (-w, w - 1.5):
        lug = cylinder(4, 1.5, (hx, y, hz), (0, 1, 0))
        web = fit.box(hx - 4, hx + 4, y, y + 1.5, -0.1, hz)
        lower = lower.fuse(web).fuse(lug)
    lower = hinge_bore(lower, cfg)
    upper = fit.box(e["upper_tip_x"], length, -w, w, gap, gap + thick)
    tongue = cylinder(3.9, width - 3.4, (hx, -w + 1.7, hz), (0, 1, 0))
    web = fit.box(hx - 3.9, hx + 3.9, -w + 1.7, w - 1.7, hz, gap + 0.1)
    upper = hinge_bore(upper.fuse(web).fuse(tongue), cfg)
    for y in (-e["mount_hole_pitch"] / 2, e["mount_hole_pitch"] / 2):
        upper = upper.cut(fit.cyl(1.1, e["mount_x"], y, gap - 1, gap + thick + 1))
    # Spring endpoints sit in shallow seats, not intersecting solid jaw material.
    lower = lower.cut(fit.cyl(3.3, e["spring_x"], 0, -0.8, 1))
    upper = upper.cut(fit.cyl(3.3, e["spring_x"], 0, gap - 1, gap + 0.9))
    grip = fit.box(47, length, -w, w, gap + thick, gap + thick + 6)
    grip = grip.cut(fit.box(46, length + 1, -w + 1.5, w - 1.5,
                           gap + thick - 1, gap + thick + 4.5))
    return {"LowerJaw": lower.removeSplitter(), "UpperJaw": upper.removeSplitter(),
            "Grip": grip, "Hinge": cylinder(e["hinge_radius"], width,
                                           (hx, -w, hz), (0, 1, 0)),
            "Spring": helix_spring(e)}


def grid_fixture(cfg, variant):
    e = cfg["estimated"]
    t, gap = e["board_thickness"], e["working_gap"]
    fine = variant["pins"] == "fine"
    barrel_d = e["fine_pogo_barrel_diameter"] if fine else e["pogo_barrel_diameter"]
    tip_d = e["fine_pogo_tip_diameter"] if fine else e["pogo_tip_diameter"]
    plunger_d = e["fine_pogo_plunger_diameter"] if fine else e["pogo_plunger_diameter"]
    extension = e["fine_pogo_free_extension"] if fine else e["pogo_free_extension"]
    compression = e["fine_pogo_working_compression"] if fine else e["pogo_working_compression"]
    length = cfg["measurements"]["long_pogo_length" if fine else "short_pogo_length"]["mm"]
    centres = interface.stock_grid(variant["pitch_mm"])
    board_top = gap + e["jaw_tip_thickness"]
    barrel_bottom = gap + 0.4
    tip_z = barrel_bottom - extension
    shapes = {}
    for name, z in (("Probe", board_top), ("Guide", gap - t)):
        board = fit.box(-1, 24 if name == "Probe" else 18, -8.15, 8.15, z, z + t)
        for x, y in centres:
            board = board.cut(fit.cyl((barrel_d + e["guide_hole_clearance"]) / 2,
                                     x, y, z - 1, z + t + 1))
        for y in (-e["mount_hole_pitch"] / 2, e["mount_hole_pitch"] / 2):
            board = board.cut(fit.cyl(1.1, e["mount_x"], y, z - 1, z + t + 1))
        shapes[name] = board
    for i, (x, y) in enumerate(centres):
        shapes["Barrel_%02d" % i] = fit.cyl(barrel_d / 2, x, y, barrel_bottom,
                                           barrel_bottom + length - extension)
        shapes["Plunger_%02d" % i] = fit.cyl(plunger_d / 2, x, y, tip_z,
                                            barrel_bottom).fuse(
                                                fit.cyl(tip_d / 2, x, y, tip_z, tip_z + 0.4))
    for i, y in enumerate((-e["mount_hole_pitch"] / 2, e["mount_hole_pitch"] / 2)):
        z = board_top + t
        shapes["Screw_%d" % i] = fit.cyl(1.9, e["mount_x"], y, z, z + 1.3).fuse(
            fit.cyl(0.95, e["mount_x"], y, z - e["mount_screw_length"], z))
        shapes["Nut_%d" % i] = fit.hexagon(e["mount_x"], y, 4, gap - t - 1.6, gap - t).cut(
            fit.cyl(1.0, e["mount_x"], y, gap - t - 2, gap))
    shapes["Header"] = fit.box(16, 21.1, -7.62, 7.62, board_top + t, board_top + t + 2.5)
    header_pins = []
    for x in (17.27, 19.81):
        for i in range(6):
            y = (i - 2.5) * 2.54
            header_pins.append(fit.box(x - 0.25, x + 0.25, y - 0.25, y + 0.25,
                                      board_top + t, board_top + t + 9))
    shapes["HeaderPins"] = fit.compound(header_pins)
    # Copper rings are separate non-overlapping solids on the substrate faces.
    pads = [fit.cyl(barrel_d / 2 + 0.22, x, y, board_top + t, board_top + t + 0.035).cut(
        fit.cyl((barrel_d + e["guide_hole_clearance"]) / 2, x, y,
                 board_top + t - 0.1, board_top + t + 0.1)) for x, y in centres]
    shapes["Pads"] = fit.compound(pads)
    return shapes, {"tip_z": tip_z, "working_compression_mm": compression,
                    "target_z": tip_z + compression,
                    "travel_mm": e["fine_pogo_travel"] if fine else e["pogo_travel"],
                    "fine_pin_geometry_estimated": fine}


def ir_fixture(cfg):
    params, geometry = fit.load()
    params = copy.deepcopy(params)
    params["clip_kit"]["geometry"]["length"] = cfg["measurements"]["body_length"]["mm"]
    params["clip_kit"]["geometry"]["width"] = cfg["measurements"]["body_width"]["mm"]
    f = fit.frame(params, geometry)
    parts, pins, stack = fit.fixture_parts(params, geometry, f)
    return parts, {"pin_contacts": pins, "stack": stack, "frame": f["z"],
                   "working_compression_mm": stack["compression_mm"],
                   "travel_mm": params["pogo"]["rated_travel"]}


def ir_visual():
    data = json.loads((OUT / "ir_board_layers.json").read_text())
    if data["board_sha256"] != interface.sha256(HERE / ".." / "ring_pcb_IR" / "ring_pcb_IR.kicad_pcb"):
        raise ValueError("Stale actual-board layers; run export_ir_visual.py with KiCad Python")
    params, geometry = fit.load()
    f = fit.frame(params, geometry)
    ox, oy = data["origin_xy_mm"]
    bottom, top = f["z"]["anvil_top"], f["z"]["ring_top"]

    def face(poly, z):
        def wire(points):
            pts = [V(y - oy - f["lt"], ox - x, z) for x, y in points]
            return Part.makePolygon(pts + [pts[0]])
        result = Part.Face(wire(poly["outer"]))
        for hole in poly["holes"]:
            result = result.cut(Part.Face(wire(hole)))
        return result

    visuals = {}
    for side, z, direction in (("front", bottom - 0.003, -1), ("rear", top + 0.003, 1)):
        board_face = Part.Face(Part.makePolygon(
            [V(*f["xy"](*p), z) for p in geometry["fit_inputs"]["ring"]["outline"]] +
            [V(*f["xy"](*geometry["fit_inputs"]["ring"]["outline"][0]), z)]))
        openings = [face(p, z) for p in data["layers"][side + "_openings"]]
        mask = board_face
        for opening in openings:
            mask = mask.cut(opening)
        copper = []
        for p in data["layers"][side + "_copper"]:
            exposed = face(p, z).common(board_face)
            # Cu intersects the actual mask openings, including battery/front bars.
            exposed = exposed.common(fit.compound(openings))
            if exposed.Area > 0:
                exposed.translate(V(0, 0, direction * 0.001))
                copper.append(exposed)
        silk = [face(p, z + direction * 0.002)
                for p in data["layers"][side + "_silk"]]
        for suffix, shape, color in (
                ("Mask", mask, (0.025, 0.24, 0.08)),
                ("Copper", fit.compound(copper), (0.88, 0.76, 0.42)),
                ("Silk", fit.compound(silk), (0.92, 0.94, 0.87))):
            if not shape.isValid() or shape.Area <= 0:
                raise ValueError("Invalid actual PCB visual: " + side + suffix)
            visuals["PCB_" + side + suffix] = (shape, color)
    return visuals


def collision_report(parts):
    hits = []
    for i, a in enumerate(sorted(parts)):
        for b in sorted(parts)[i + 1:]:
            if (a, b) == ("Header", "HeaderPins"):
                continue
            if not parts[a].BoundBox.intersect(parts[b].BoundBox):
                continue
            volume = parts[a].common(parts[b]).Volume
            if volume > EPS:
                hits.append({"a": a, "b": b, "volume_mm3": round(volume, 6)})
    return hits


def contact_check(pitch, tip_diameter, uncertainty):
    result = interface.compatibility(pitch, tip_diameter, uncertainty)
    pads = interface.ir_contacts()
    for row in result["signal_contacts"]:
        pad = pads[row["ref"]]
        u, v = pad["uv"]
        sx, sy = pad["size"]
        target = fit.box(u - sx / 2, u + sx / 2, v - sy / 2, v + sy / 2, 0, 0.1)
        x, y = row["pin_uv"]
        tip = fit.cyl(tip_diameter / 2, x, y, 0, 0.1)
        row["freecad_tip_overlap_fraction"] = round(tip.common(target).Volume / tip.Volume, 5)
        row["freecad_axis_on_pad"] = target.isInside(V(x, y, 0.05), 1e-7, True)
    return result


def moved(shape, cfg, angle):
    e = cfg["estimated"]
    result = shape.copy()
    result.rotate(V(e["hinge_x"], 0, e["hinge_z"]), V(0, 1, 0), angle)
    return result


def sweep(parts, cfg, custom):
    """Rigid hinge opening, not a force or spring-life simulation."""
    stationary = {"LowerJaw", "Hinge"}
    if custom:
        stationary |= {"Anvil", "Fence", "Riser", "Ring", "RingParts"}
    moving = set(parts) - stationary - {"Spring"}
    failures = []
    samples = []
    for step in range(13):
        angle = cfg["estimated"]["open_angle_deg"] * step / 12
        worst = 0.0
        for a in moving:
            shape = moved(parts[a], cfg, angle)
            for b in stationary - {"Hinge"}:
                if shape.BoundBox.intersect(parts[b].BoundBox):
                    volume = shape.common(parts[b]).Volume
                    worst = max(worst, volume)
                    if volume > EPS:
                        failures.append({"angle": angle, "a": a, "b": b,
                                         "volume_mm3": round(volume, 6)})
        spring = helix_spring(cfg["estimated"], angle)
        for jaw in ("LowerJaw", "UpperJaw"):
            target = parts[jaw] if jaw == "LowerJaw" else moved(parts[jaw], cfg, angle)
            volume = spring.common(target).Volume
            worst = max(worst, volume)
            if volume > EPS:
                failures.append({"angle": angle, "a": "Spring", "b": jaw,
                                 "volume_mm3": round(volume, 6)})
        wire_d = cfg["estimated"]["spring_wire_radius"] * 2
        coil_gap = spring_height(cfg["estimated"], angle) / cfg["estimated"]["spring_turns"] - wire_d
        if coil_gap <= 0:
            raise ValueError("Estimated spring coils bind")
        samples.append({"angle_deg": angle, "max_interference_mm3": round(worst, 6),
                        "estimated_coil_gap_mm": round(coil_gap, 4)})
    return {"samples": samples, "collisions": failures,
            "note": "Rigid hinge plus estimated helical spring compression/coil spacing. "
                    "No force, spring-end seating, fatigue or measured spring qualification."}


def export(cfg, variant, parts):
    dest = OUT / variant["id"]
    dest.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument(variant["id"])
    meshes = []
    for name, shape in parts.items():
        if not shape.isValid() or not shape.Solids or shape.Volume <= 0:
            raise ValueError("Invalid CAD part: " + name)
        obj = doc.addObject("PartDesign::Feature", name)
        obj.Shape = shape
        color = COLORS.get(name, (0.92, 0.72, 0.25) if name.startswith(("Barrel", "Plunger"))
                           else (0.68, 0.71, 0.76))
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.08,
                                      AngularDeflection=0.2, Relative=False)
        mesh.write(str(dest / (name + ".stl")))
        meshes.append({"name": name, "file": name + ".stl", "color": color,
                       "volume_mm3": round(shape.Volume, 4)})
    if variant["id"] == "ir_custom":
        for name, (shape, color) in ir_visual().items():
            obj = doc.addObject("PartDesign::Feature", name)
            obj.Shape = shape
            mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02,
                                          AngularDeflection=0.15, Relative=False)
            mesh.write(str(dest / (name + ".stl")))
            meshes.append({"name": name, "file": name + ".stl", "color": color,
                           "visual_surface_only": True, "area_mm2": round(shape.Area, 4)})
    doc.recompute()
    doc.saveAs(str(dest / "clip.FCStd"))
    Part.export([obj for obj in doc.Objects if obj.Name in parts], str(dest / "clip.step"))
    imported = Part.Shape()
    imported.read(str(dest / "clip.step"))
    expected = sum(shape.Volume for shape in parts.values())
    if not imported.isValid() or abs(imported.Volume - expected) > 0.01:
        raise ValueError("STEP round trip failed: " + variant["id"])
    (dest / "meshes.json").write_text(json.dumps(meshes, indent=2) + "\n")
    App.closeDocument(doc.Name)


def main():
    cfg = interface.load()
    OUT.mkdir(parents=True, exist_ok=True)
    reports = {}
    for variant in cfg["variants"]:
        parts = kit(cfg)
        custom = variant["id"] == "ir_custom"
        fixture, details = ir_fixture(cfg) if custom else grid_fixture(cfg, variant)
        parts.update(fixture)
        hits = collision_report(parts)
        motion = sweep(parts, cfg, custom)
        if hits or motion["collisions"]:
            raise ValueError(json.dumps({"variant": variant["id"], "collisions": hits,
                                         "motion": motion["collisions"]}, indent=2))
        export(cfg, variant, parts)
        reports[variant["id"]] = {"static_collisions": hits, "opening": motion,
                                  "details": details, "solid_count": len(parts)}
        print(variant["id"], "valid solids; static and opening checks PASS")
    compat = [contact_check(v["pitch_mm"],
              cfg["estimated"]["fine_pogo_tip_diameter"] if v["pins"] == "fine"
              else cfg["estimated"]["pogo_tip_diameter"],
              cfg["estimated"]["registration_uncertainty"])
              for v in cfg["variants"] if v["id"] != "ir_custom"]
    report = {"scope": cfg["status"], "album": cfg["album"], "variants": reports,
              "stock_ir_compatibility": compat,
              "custom_ir_contact": contact_check(3.05, cfg["estimated"]["pogo_tip_diameter"], 0),
              "source_sha256": {name: interface.sha256(HERE / name) for name in (
                  "assembly_parameters.json", "assembly_interface.py", "assembly_model.py",
                  "fit_check.py", "parameters.json", "generated/geometry.json",
                  "export_ir_visual.py", "generated/assembly/ir_board_layers.json")},
              "artifact_sha256": {path.relative_to(OUT).as_posix(): interface.artifact_sha256(path)
                                  for path in sorted(OUT.glob("*/*"))
                                  if path.is_file() and path.suffix in (".stl", ".step", ".FCStd", ".json")},
              "pcb_sha256": interface.sha256(HERE / ".." / "ring_pcb_IR" / "ring_pcb_IR.kicad_pcb")}
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
