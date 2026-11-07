"""Generate experimental battery-free bayonet and dual-board fit prototypes."""

import json
from pathlib import Path

import FreeCAD as App
import Part

from design import (HERE, PCB_PATH, artifact_hash, child, children, load_parameters,
                    offset_polygon, parse_sexpr, pcb_interface, source_hash, xy)
from lantern_ring import (bop_check, cylinder, mesh_for, polygon_solid, posed,
                          screw_positions, sector, unrotated_geometry)
from printcheck import check_stl

IR_PATH = HERE.parent / "ring_pcb_IR" / "ring_pcb_IR.kicad_pcb"
OUTPUT = HERE / "generated" / "fit_gauges"
SKIRT_RADIUS = 10.75
LUG_OUTER_RADIUS = 12.20
GAUGE_RADIUS = 12.8
GAUGE_HEIGHT = 1.2
CR1632_RADIUS = 8.0
CR1632_CLEARANCE = 0.15


def ir_interface():
    board = parse_sexpr(IR_PATH.read_text(encoding="utf-8"))
    polygons = [node for node in children(board, "gr_poly")
                if child(node, "layer")[1] == "Edge.Cuts"]
    if len(polygons) != 1:
        raise ValueError("IR board must have one polygon Edge.Cuts outline")
    points = [xy(node) for node in child(polygons[0], "pts")[1:]]
    xs, ys = zip(*points)
    origin = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
    return ([(x - origin[0], origin[1] - y) for x, y in points],
            float(child(child(board, "general"), "thickness")[1]))


def build():
    p = load_parameters()
    mono = pcb_interface()
    ir, ir_thickness = ir_interface()
    raw = unrotated_geometry(p, mono)
    bottom = p["carrier_bottom"]
    top = p["lug_bottom"] + p["lug_height"]
    bayonet = cylinder(SKIRT_RADIUS, bottom, top)
    for angle, width in zip(p["lug_angles"], p["lug_widths"]):
        bayonet = bayonet.fuse(sector(SKIRT_RADIUS - 0.25, LUG_OUTER_RADIUS,
                                     p["lug_bottom"], top, angle - width / 2, width))
    bayonet = bayonet.removeSplitter()

    gauge = cylinder(GAUGE_RADIUS, 0, GAUGE_HEIGHT)
    for outline in (mono["outline"], ir):
        opening = polygon_solid(offset_polygon(outline, p["pcb_clearance"]),
                                -0.1, GAUGE_HEIGHT + 0.1)
        gauge = gauge.cut(opening)
    gauge = gauge.removeSplitter()

    # The CR1632 candidate uses the existing 3.2 mm cell height and pin datums.
    # This geometry is only for battery-free mechanical evaluation.
    candidate = raw["Carrier"]
    insert = cylinder(10.2, p["battery_bottom"], p["deck_bottom"]).cut(
        cylinder(CR1632_RADIUS + CR1632_CLEARANCE, p["battery_bottom"] - 0.1,
                 p["deck_bottom"] + 0.1))
    candidate = candidate.fuse(insert)
    outer = cylinder(13, bottom - 0.1, p["socket_top"]).cut(
        cylinder(SKIRT_RADIUS, bottom - 0.2, p["socket_top"] + 0.1))
    candidate = candidate.cut(outer)
    for angle, width in zip(p["lug_angles"], p["lug_widths"]):
        candidate = candidate.fuse(sector(SKIRT_RADIUS - 0.25, LUG_OUTER_RADIUS,
                                          p["lug_bottom"], top, angle - width / 2, width))
    deck = raw["ContactDeck"].cut(
        polygon_solid(offset_polygon(ir, p["pcb_clearance"]),
                      p["pcb_bottom"], p["pcb_bottom"] + 2.0))
    # Separate clamp for the IR substrate; its screw feet bridge the extra height.
    ir_top = p["pcb_bottom"] + ir_thickness
    ir_bezel = cylinder(p["bezel_radius"], ir_top, ir_top + p["bezel_height"])
    ir_bezel = ir_bezel.cut(polygon_solid(offset_polygon(ir, -0.45),
                                          ir_top - 0.1, ir_top + p["bezel_height"] + 0.1))
    for x, y in screw_positions(p):
        foot = cylinder(p["screw_clearance_diameter"] / 2 + 1.08,
                        p["pcb_bottom"] + mono["thickness"],
                        ir_top + 0.1, x, y)
        ir_bezel = ir_bezel.fuse(foot)
        ir_bezel = ir_bezel.cut(cylinder(p["screw_clearance_diameter"] / 2,
                                         p["pcb_bottom"] + mono["thickness"] - 0.1,
                                         ir_top + p["bezel_height"] + 0.1, x, y))
    # The wire relief is deliberately not finalized without the IR routing.

    # This checks the existing nominal CAD socket, not the measured printed socket.
    base = raw["RingBase"]
    for lift in (i * 0.5 for i in range(41)):
        for name, shape in (("Gauge", bayonet), ("Candidate", candidate)):
            if base.common(posed(shape, 0, lift)).Volume > 1e-5:
                raise ValueError("{} insertion interferes at {}".format(name, lift))
    for angle in range(31):
        for name, shape in (("Gauge", bayonet), ("Candidate", candidate)):
            if base.common(posed(shape, angle)).Volume > 1e-5:
                raise ValueError("{} twist interferes at {}".format(name, angle))
    for angle in (120, 240):
        entry_lift = p["socket_top"] - p["lug_bottom"] - p["lug_height"] / 2
        for name, shape in (("Gauge", bayonet), ("Candidate", candidate)):
            if base.common(posed(shape, angle, entry_lift)).Volume < 1e-3:
                raise ValueError("{} does not reject incorrect key orientation".format(name))
    for name, shape in (("Gauge", bayonet), ("Candidate", candidate)):
        if base.common(posed(shape, p["lock_angle"], 1)).Volume < 1e-3:
            raise ValueError("{} cannot engage the nominal retaining shelf".format(name))
    for outline, thickness in ((mono["outline"], mono["thickness"]), (ir, ir_thickness)):
        board = polygon_solid(outline, -0.1, GAUGE_HEIGHT + 0.1)
        if gauge.common(board).Volume > 1e-5:
            raise ValueError("Board outline intersects the gauge")
        if gauge.distToShape(board)[0] < p["pcb_clearance"] - 1e-5:
            raise ValueError("Board outline clearance is below the requested margin")
        board = polygon_solid(outline, p["pcb_bottom"], p["pcb_bottom"] + thickness)
        if board.common(deck).Volume > 1e-5 or board.common(candidate).Volume > 1e-5:
            raise ValueError("Board substrate intersects the candidate cassette")
    cell = cylinder(CR1632_RADIUS, p["battery_bottom"], p["battery_bottom"] + 3.2)
    if cell.common(candidate).Volume > 1e-5 or candidate.common(deck).Volume > 1e-5:
        raise ValueError("Candidate cell, carrier and deck interfere")
    for lift in range(17):
        if candidate.common(posed(cell, 0, lift)).Volume > 1e-5:
            raise ValueError("Candidate cell extraction path interferes at {}".format(lift))
    for name in ("NegativePogo", "PositivePogo", "NegativeLead", "PositiveLead"):
        if (raw[name].common(candidate).Volume > 1e-5 or
                raw[name].common(deck).Volume > 1e-5):
            raise ValueError("{} interferes with candidate solids".format(name))
    ir_board = polygon_solid(ir, p["pcb_bottom"], ir_top)
    if ir_board.common(ir_bezel).Volume > 1e-5:
        raise ValueError("IR bezel intersects the IR substrate")
    if ir_board.common(posed(ir_bezel, 0, -0.05)).Volume < 1e-3:
        raise ValueError("IR bezel fails to overlap the IR board edge")
    for name, shape in (("carrier", candidate), ("deck", deck)):
        if shape.common(ir_bezel).Volume > 1e-5:
            raise ValueError("IR bezel intersects {}".format(name))

    OUTPUT.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument("ExperimentalFitGauges")
    reports = {}
    shapes = (("BayonetGauge", bayonet), ("BoardOutlineGauge", gauge),
              ("CarrierFitOnly", candidate), ("DualBoardDeckFitOnly", deck),
              ("IRBezelFitOnly", ir_bezel))
    for name, shape in shapes:
        if not shape.isValid() or len(shape.Solids) != 1:
            raise ValueError("{} is not one valid solid".format(name))
        bop_check(shape)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        step = OUTPUT / (name + ".step")
        shape.exportStep(str(step))
        reloaded = Part.read(str(step))
        if not reloaded.isValid() or abs(reloaded.Volume - shape.Volume) > 1e-5:
            raise ValueError("{} STEP round-trip failed".format(name))
        mesh = mesh_for(shape, p)
        mesh.translate(0, 0, -shape.BoundBox.ZMin)
        if not mesh.isSolid():
            raise ValueError("{} mesh is not watertight".format(name))
        stl = OUTPUT / (name + ".stl")
        mesh.write(str(stl))
        report = check_stl(stl, p["min_printed_wall"])
        if not report["passes"]:
            raise ValueError("{} failed print check: {}".format(name, report))
        reports[name] = report
    doc.recompute()
    doc.saveAs(str(OUTPUT / "ExperimentalFitGauges.FCStd"))
    App.closeDocument(doc.Name)
    restored = App.openDocument(str(OUTPUT / "ExperimentalFitGauges.FCStd"))
    for name, _ in shapes:
        if not restored.getObject(name).Shape.isValid():
            raise ValueError("{} failed native document restore".format(name))
    App.closeDocument(restored.Name)
    report = {
        "status": "EXPERIMENTAL GAUGES ONLY; not a battery holder, assembly or qualified fit",
        "measured_entry_span_mm": 22.1,
        "bayonet_skirt_diameter_mm": 2 * SKIRT_RADIUS,
        "nominal_diametral_clearance_against_measured_span_mm": 22.1 - 2 * SKIRT_RADIUS,
        "nominal_lug_tip_radius_mm": LUG_OUTER_RADIUS,
        "board_outline_clearance_mm": p["pcb_clearance"],
        "board_substrate_thickness_mm": {"mono": mono["thickness"], "ir": ir_thickness},
        "candidate_cell_nominal_diameter_mm": 2 * CR1632_RADIUS,
        "candidate_cell_nominal_height_mm": 3.2,
        "limitations": [
            "The 22.1 mm is one physical span, not a measured cylindrical socket.",
            "Lug slots and tracks remain unmeasured; only the source CAD base is checked.",
            "Board gauge tests outlines only, not thickness, components or electrical contacts.",
            "Candidate cassette is not compatible with either finished assembly until its bezel, components, wiring, electrical safety and retention are checked.",
            "Do not insert a cell, power the boards or wear the candidate.",
            "The parts are not physically printed or tested.",
        ],
        "source_sha256": {path.relative_to(HERE.parent.parent.parent).as_posix(): source_hash(path)
                          for path in (PCB_PATH, IR_PATH, HERE / "parameters.json",
                                       HERE / "design.py", HERE / "lantern_ring.py",
                                       HERE / "fit_gauges.py")},
        "print_check": reports,
        "artifact_sha256": {path.name: artifact_hash(path) for path in OUTPUT.iterdir()
                            if path.suffix.lower() in (".fcstd", ".step", ".stl")},
    }
    (OUTPUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Generated experimental fit prototypes in", OUTPUT)


if __name__ == "__main__":
    build()
