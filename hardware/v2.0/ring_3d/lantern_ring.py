"""Rebuildable FreeCAD v2 bayonet cassette. Run with FreeCAD's Python."""

import argparse
from functools import lru_cache
import itertools
import json
import math
import os
from pathlib import Path
import sys

import FreeCAD as App
import Mesh
import MeshPart
import Part

from design import HERE, PCB_PATH, artifact_hash, load_parameters, offset_polygon, pcb_interface, source_hash, validate_parameters


Z = App.Vector(0, 0, 1)
PRINT_PARTS = ("RingBase", "Carrier", "ContactDeck", "Bezel")
COLORS = {
    "RingBase": (0.22, 0.26, 0.31),
    "Carrier": (0.15, 0.55, 0.37),
    "ContactDeck": (0.80, 0.66, 0.34),
    "Bezel": (0.20, 0.68, 0.43),
    "PCB": (0.12, 0.32, 0.16),
    "Battery": (0.72, 0.75, 0.78),
    "PositivePogo": (0.92, 0.72, 0.25),
    "NegativePogo": (0.92, 0.72, 0.25),
    "PositiveLead": (0.72, 0.75, 0.78),
    "NegativeLead": (0.12, 0.12, 0.14),
    "LEDs": (0.83, 0.94, 0.78),
}


def cylinder(radius, bottom, top, x=0, y=0):
    return Part.makeCylinder(radius, top - bottom, App.Vector(x, y, bottom))


def box(width, length, bottom, top, x, y):
    return Part.makeBox(width, length, top - bottom, App.Vector(x, y, bottom))


def polygon_solid(points, bottom, top):
    vertices = [App.Vector(x, y, bottom) for x, y in points]
    return Part.Face(Part.makePolygon(vertices + [vertices[0]])).extrude(Z * (top - bottom))


def sector(inner, outer, bottom, top, start, sweep):
    shape = Part.makeCylinder(outer, top - bottom, App.Vector(0, 0, bottom), Z, sweep)
    shape = shape.cut(cylinder(inner, bottom - 0.1, top + 0.1))
    shape.rotate(App.Vector(), Z, start)
    return shape


def radial_hole(angle, inner, outer, z, radius):
    angle = math.radians(angle)
    direction = App.Vector(math.cos(angle), math.sin(angle), 0)
    return Part.makeCylinder(radius, outer - inner, direction * inner + App.Vector(0, 0, z), direction)


def screw_positions(p):
    return [(p["screw_radius"] * math.cos(math.radians(a)),
             p["screw_radius"] * math.sin(math.radians(a))) for a in p["screw_angles"]]


def pogo(p, flange, point, downward=False):
    """Conservative 0965 SMT envelope; flange datum is the solder-mount plane."""
    x, y = point
    flange_top = flange + p["pin_flange_thickness"]
    body_top = flange + p["pin_body_length"]
    tip_top = flange + p["pin_initial_height"] - p["pin_compression"]
    result = cylinder(p["pin_flange_diameter"] / 2, flange, flange_top, x, y)
    result = result.fuse(cylinder(p["pin_body_diameter"] / 2, flange_top, body_top, x, y))
    result = result.fuse(cylinder(p["pin_tip_diameter"] / 2, body_top, tip_top, x, y))
    if downward:
        result.rotate(App.Vector(x, y, flange), App.Vector(1, 0, 0), 180)
    return result.removeSplitter()


def lead(points, radius):
    vertices = [App.Vector(*point) for point in points]
    segments = []
    for a, b in zip(vertices, vertices[1:]):
        direction = b - a
        segments.append(Part.makeCylinder(radius, direction.Length, a, direction))
    segments.extend(Part.makeSphere(radius, point) for point in vertices[1:-1])
    result = segments[0]
    for segment in segments[1:]:
        result = result.fuse(segment)
    return result.removeSplitter()


def unrotated_geometry(p, pcb):
    s = validate_parameters(p, pcb)
    pcb_top = s["pcb_top"]
    cell_radius = p["battery_radius"] + p["battery_clearance"]
    wire_x = pcb["ground"][0]
    wire_y = p["wire_channel_y"]
    wire_r = p["wire_channel_diameter"] / 2

    band_centre = App.Vector(0, -p["band_width"] / 2,
                             -p["finger_diameter"] / 2 - p["band_wall"] / 2)
    outer = Part.makeCylinder(p["finger_diameter"] / 2 + p["band_wall"],
                              p["band_width"], band_centre, App.Vector(0, 1, 0))
    inner = Part.makeCylinder(p["finger_diameter"] / 2,
                              p["band_width"] + 2,
                              band_centre - App.Vector(0, 1, 0), App.Vector(0, 1, 0))
    band = outer.cut(inner)
    base = band.fuse(cylinder(p["body_radius"], 0, p["socket_top"]))
    base = base.cut(cylinder(p["socket_radius"], p["carrier_bottom"], p["socket_top"] + 1))
    for angle, width in zip(p["lug_angles"], p["lug_widths"]):
        start = angle - width / 2 - p["angular_clearance"]
        entry_width = width + 2 * p["angular_clearance"]
        track_bottom = p["lug_bottom"] - p["track_clearance"]
        track_top = p["lug_bottom"] + p["lug_height"] + p["track_clearance"]
        base = base.cut(sector(p["socket_radius"] - 0.1, p["track_outer_radius"],
                               track_bottom, p["socket_top"] + 1, start, entry_width))
        base = base.cut(sector(p["socket_radius"] - 0.1, p["track_outer_radius"],
                               track_bottom, track_top, start, entry_width + p["lock_angle"]))
    latch_z = p["lug_bottom"] + p["lug_height"] / 2
    base = base.cut(radial_hole(p["lock_angle"], p["lug_outer_radius"] - 0.1,
                                p["body_radius"] + 1, latch_z, 0.55))

    carrier = cylinder(p["carrier_radius"], p["carrier_bottom"], pcb_top)
    carrier = carrier.cut(cylinder(cell_radius, p["battery_bottom"], p["deck_bottom"]))
    carrier = carrier.cut(cylinder(p["deck_pocket_radius"], p["deck_bottom"], pcb_top + 1))
    for x, y in screw_positions(p):
        carrier = carrier.fuse(cylinder(p["screw_post_radius"], p["deck_bottom"] - 0.5, pcb_top, x, y))
        carrier = carrier.cut(cylinder(p["screw_pilot_diameter"] / 2,
                                       p["deck_bottom"] - 3, pcb_top + 1, x, y))
    carrier = carrier.fuse(cylinder(0.35, p["carrier_bottom"], pcb_top, wire_x, wire_y))
    carrier = carrier.cut(cylinder(wire_r, p["carrier_bottom"] - 1, pcb_top + 1, wire_x, wire_y))
    neg_shoulder = s["negative_flange"] + p["pin_flange_thickness"]
    carrier = carrier.cut(cylinder(p["pin_bore_diameter"] / 2,
                                   neg_shoulder, p["battery_bottom"] + 0.1))
    carrier = carrier.cut(cylinder(p["pin_flange_bore_diameter"] / 2,
                                   p["carrier_bottom"] - 0.1, neg_shoulder))
    # Underside channel encloses the negative lead above the base's insulating floor.
    carrier = carrier.cut(box(3.0, wire_y + wire_r,
                              p["carrier_bottom"] - 0.1, s["negative_flange"], wire_x - 1.5, -wire_r))
    carrier = carrier.cut(box(2.3, 2.3, s["negative_flange"] - 0.25,
                              s["negative_flange"] + 0.01, -1.15, -1.15))
    for angle, width in zip(p["lug_angles"], p["lug_widths"]):
        carrier = carrier.fuse(sector(p["lug_inner_radius"], p["lug_outer_radius"],
                                      p["lug_bottom"], p["lug_bottom"] + p["lug_height"],
                                      angle - width / 2, width))
    carrier = carrier.cut(radial_hole(0, p["carrier_radius"] - 0.9,
                                      p["lug_outer_radius"] + 0.1, latch_z, 0.4))

    deck = cylinder(p["deck_radius"], p["deck_bottom"], pcb_top)
    deck = deck.cut(cylinder(10.5, p["deck_floor_top"], p["pcb_bottom"] - 0.6))
    deck = deck.cut(polygon_solid(offset_polygon(pcb["outline"], -0.45),
                                  p["pcb_bottom"] - 0.6, p["pcb_bottom"] + 0.01))
    deck = deck.cut(polygon_solid(offset_polygon(pcb["outline"], p["pcb_clearance"]),
                                  p["pcb_bottom"], pcb_top + 1))
    positive_x, positive_y = pcb["positive"]
    pos_shoulder = s["positive_flange"] - p["pin_flange_thickness"]
    deck = deck.cut(cylinder(p["pin_bore_diameter"] / 2,
                             p["deck_bottom"] - 0.1, pos_shoulder, positive_x, positive_y))
    deck = deck.cut(cylinder(p["pin_flange_bore_diameter"] / 2,
                             pos_shoulder, p["deck_floor_top"] + 0.1, positive_x, positive_y))
    for x, y in screw_positions(p):
        deck = deck.cut(cylinder(p["screw_post_radius"] + 0.2,
                                 p["deck_bottom"] - 1, pcb_top + 1, x, y))
    deck = deck.cut(cylinder(0.6, p["deck_bottom"] - 1, pcb_top + 1, wire_x, wire_y))

    bezel = cylinder(p["screw_radius"] + p["screw_post_radius"], pcb_top, s["assembly_top"])
    bezel = bezel.cut(polygon_solid(offset_polygon(pcb["outline"], -0.45),
                                    pcb_top - 0.1, s["assembly_top"] + 1))
    for x, y in screw_positions(p):
        bezel = bezel.cut(cylinder(p["screw_clearance_diameter"] / 2,
                                   pcb_top - 0.1, s["assembly_top"] + 1, x, y))
    bezel = bezel.cut(box(p["wire_channel_diameter"], wire_y - pcb["ground"][1] + 0.8,
                          pcb_top - 0.01, pcb_top + 0.9, wire_x - wire_r, pcb["ground"][1] - 0.4))
    battery = cylinder(p["battery_radius"], p["battery_bottom"], s["battery_top"])
    board = polygon_solid(pcb["outline"], p["pcb_bottom"], pcb_top)
    leds = []
    for component in pcb["components"]:
        x, y = component["xy"]
        led = box(3.2, 1.6, pcb_top, pcb_top + 1.1, x - 1.6, y - 0.8)
        led.rotate(App.Vector(x, y, 0), Z, component["angle"])
        leds.append(led)
    positive_lead = cylinder(p["pin_flange_diameter"] / 2,
                             s["positive_flange"], p["pcb_bottom"], positive_x, positive_y)
    negative_lead = lead([
        (0, 0, s["negative_flange"] - 0.2),
        (wire_x, wire_y, s["negative_flange"] - 0.2),
        (wire_x, wire_y, pcb_top + 0.3),
        (wire_x, pcb["ground"][1], pcb_top + 0.3),
        (wire_x, pcb["ground"][1], pcb_top),
    ], p["wire_diameter"] / 2)
    return {
        "RingBase": base,
        "Carrier": carrier,
        "ContactDeck": deck.removeSplitter(),
        "Bezel": bezel.removeSplitter(),
        "PCB": board,
        "Battery": battery,
        "PositivePogo": pogo(p, s["positive_flange"], pcb["positive"], downward=True),
        "NegativePogo": pogo(p, s["negative_flange"], (0, 0)),
        "PositiveLead": positive_lead,
        "NegativeLead": negative_lead,
        "LEDs": Part.makeCompound(leds),
    }


@lru_cache(maxsize=4)
def geometry(config_json, interface_json):
    p, pcb = json.loads(config_json), json.loads(interface_json)
    parts = unrotated_geometry(p, pcb)
    for name, shape in parts.items():
        if name != "RingBase":
            shape.rotate(App.Vector(), Z, p["lock_angle"])
    return parts


def object_config(parameters):
    p = json.loads(parameters.Configuration)
    p["finger_diameter"] = parameters.FingerDiameter.Value
    p["pcb_clearance"] = parameters.PCBClearance.Value
    p["lock_angle"] = parameters.LockAngle.Value
    return json.dumps(p, sort_keys=True)


class RingFeature:
    def __init__(self, obj):
        obj.Proxy = self

    def execute(self, obj):
        parts = geometry(object_config(obj.Parameters), obj.Parameters.PCBInterface)
        obj.Shape = parts[obj.PartName].copy()

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        pass


def create_document(p, pcb):
    doc = App.newDocument("LanternRingV2")
    parameters = doc.addObject("App::FeaturePython", "Parameters")
    parameters.addProperty("App::PropertyString", "Configuration", "Design").Configuration = json.dumps(p, sort_keys=True)
    parameters.addProperty("App::PropertyString", "PCBInterface", "Design").PCBInterface = json.dumps(pcb, sort_keys=True)
    parameters.addProperty("App::PropertyLength", "FingerDiameter", "Design").FingerDiameter = p["finger_diameter"]
    parameters.addProperty("App::PropertyLength", "PCBClearance", "Design").PCBClearance = p["pcb_clearance"]
    parameters.addProperty("App::PropertyAngle", "LockAngle", "Design").LockAngle = p["lock_angle"]
    parameters.addProperty("App::PropertyString", "BatteryPolarity", "Interface").BatteryPolarity = "CR2032 positive (+) face UP"
    parameters.addProperty("App::PropertyString", "GroundPad", "Interface").GroundPad = pcb["ground_reference"] + " front /GND"
    parameters.setEditorMode("PCBInterface", 1)
    printable = doc.addObject("App::DocumentObjectGroup", "PrintableParts")
    references = doc.addObject("App::DocumentObjectGroup", "ReferenceParts")
    for name in COLORS:
        obj = doc.addObject("Part::FeaturePython", name)
        if name == "PositiveLead":
            obj.Label = "Positive solder land"
        obj.addProperty("App::PropertyLink", "Parameters", "Design").Parameters = parameters
        obj.addProperty("App::PropertyString", "PartName", "Design").PartName = name
        obj.setEditorMode("PartName", 1)
        RingFeature(obj)
        (printable if name in PRINT_PARTS else references).addObject(obj)
        if App.GuiUp:
            obj.ViewObject.ShapeColor = COLORS[name]
            obj.ViewObject.LineColor = (0.1, 0.1, 0.1)
    doc.recompute()
    return doc


def posed(shape, angle, lift=0):
    result = shape.copy()
    result.rotate(App.Vector(), Z, angle)
    result.translate(App.Vector(0, 0, lift))
    return result


def validate_geometry(p, pcb, parts):
    raw = unrotated_geometry(p, pcb)
    checks = []
    for name in PRINT_PARTS:
        shape = parts[name]
        if not shape.isValid() or len(shape.Solids) != 1 or shape.Volume <= 0:
            raise ValueError("{} is not a single valid solid".format(name))
        shape.check(True)
        checks.append("{}: valid single solid".format(name))
    for a, b in itertools.combinations(parts, 2):
        if {a, b} in ({"PositivePogo", "PositiveLead"}, {"NegativePogo", "NegativeLead"}):
            continue
        volume = parts[a].common(parts[b]).Volume
        if volume > 1e-5:
            raise ValueError("Interference {} / {}: {:.6f} mm^3".format(a, b, volume))
    checks.append("No unintended assembled interference; pin/lead solder terminations excluded")
    base = raw["RingBase"]
    moving = Part.makeCompound([raw[n] for n in PRINT_PARTS if n != "RingBase"])
    for i in range(41):
        lift = i * 0.5
        volume = base.common(posed(moving, 0, lift)).Volume
        if volume > 1e-5:
            raise ValueError("Insertion interferes at lift {}".format(lift))
    checks.append("Axial insertion: 41 poses, 0..20 mm")
    poses = max(30, math.ceil(p["lock_angle"]))
    for i in range(poses + 1):
        angle = p["lock_angle"] * i / poses
        volume = base.common(posed(moving, angle)).Volume
        if volume > 1e-5:
            raise ValueError("Twist interferes at {} degrees".format(angle))
    checks.append("Twist: {} poses, 0..{} degrees".format(poses + 1, p["lock_angle"]))
    for angle in (120, 240):
        entry_lift = p["socket_top"] - p["lug_bottom"] - p["lug_height"] / 2
        if base.common(posed(raw["Carrier"], angle, entry_lift)).Volume < 1e-3:
            raise ValueError("Wide lug does not reject {} degree mis-key".format(angle))
    checks.append("Wide lug rejects both incorrect 120/240 degree insertion orientations")
    if base.common(posed(raw["Carrier"], p["lock_angle"], 1)).Volume < 1e-3:
        raise ValueError("Locked bayonet can be pulled out axially")
    checks.append("Locked cassette cannot lift 1 mm through retaining shelves")
    s = validate_parameters(p, pcb)
    checks.append("Pogo travel worst case: {:.3f}..{:.3f} mm; max {:.3f} mm".format(
        p["pin_compression"] - p["printed_stack_tolerance"] - p["pin_height_tolerance"] - p["battery_height_tolerance"],
        p["pin_compression"] + p["printed_stack_tolerance"] + p["pin_height_tolerance"] + p["battery_height_tolerance"],
        p["pin_max_stroke"]))
    for name in ("NegativePogo", "PositivePogo"):
        bound = raw[name].BoundBox
        contact_z = bound.ZMax if name == "NegativePogo" else bound.ZMin
        target_z = p["battery_bottom"] if name == "NegativePogo" else s["battery_top"]
        if abs(contact_z - target_z) > 1e-6:
            raise ValueError("{} does not touch the battery".format(name))
    checks.append("Both pogo tips touch the intended battery faces at nominal compression")
    # Cell must be removable after the PCB/contact deck are lifted, without wires in its path.
    for lift in range(17):
        if raw["Carrier"].common(posed(raw["Battery"], 0, lift)).Volume > 1e-5:
            raise ValueError("Battery is trapped in the carrier at lift {}".format(lift))
    checks.append("Battery extraction: 17 poses, 0..16 mm after deck removal")
    crown = Part.makeCompound([raw[name] for name in ("Carrier", "ContactDeck", "Bezel")])
    if max(crown.BoundBox.XLength, crown.BoundBox.YLength) > 24.9 + 1e-6:
        raise ValueError("Actual crown geometry exceeds the legacy-derived width budget")
    if crown.BoundBox.ZMax > 12.2204 + 1e-6:
        raise ValueError("Actual crown geometry exceeds the compact height budget")
    if (abs(raw["Battery"].BoundBox.XLength - 20) > 1e-6
            or abs(raw["Battery"].BoundBox.ZLength - 3.2) > 1e-6):
        raise ValueError("Do not scale the CR2032 to fit the crown")
    checks.append("Actual solids preserve compact 24.9 mm maximum width / 12.2204 mm top")
    return checks


def mesh_for(shape, p):
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=p["mesh_deflection"],
                                  AngularDeflection=0.18, Relative=False)
    mesh.removeDuplicatedPoints()
    return mesh


def preview_png(parts, p, output):
    """Depth-buffered orthographic preview using FreeCAD's bundled NumPy/Qt."""
    import importlib.util
    import numpy as np
    if importlib.util.find_spec("PySide6"):
        from PySide6 import QtGui
    else:
        from PySide2 import QtGui

    faces = []
    for name in COLORS:
        mesh = mesh_for(parts[name], p)
        base_color = COLORS[name]
        for facet in mesh.Facets:
            normal = facet.Normal
            if 0.866 * (normal.x + normal.y) + 0.7 * normal.z <= 0:
                continue
            brightness = 0.55 + 0.45 * max(0, 0.2 * normal.x - 0.35 * normal.y + 0.91 * normal.z)
            color = tuple(int(c * brightness * 255) for c in base_color)
            points = []
            for v in facet.Points:
                x, y, z = v
                points.append((0.866 * (x - y), 0.35 * (x + y) - 0.866 * z,
                               0.866 * (x + y) + 0.7 * z))
            faces.append((points, color))
    coords = [v for points, _ in faces for v in points]
    xs, ys, _ = zip(*coords)
    min_x, min_y, max_x, max_y = min(xs) - 3, min(ys) - 3, max(xs) + 3, max(ys) + 3
    width = 800
    scale = width / (max_x - min_x)
    height = math.ceil((max_y - min_y) * scale)
    rgb = np.full((height, width, 3), (244, 246, 248), dtype=np.uint8)
    depth_buffer = np.full((height, width), -np.inf)
    for points, color in faces:
        vertices = np.array([((x - min_x) * scale, (y - min_y) * scale, depth)
                             for x, y, depth in points])
        left = max(0, math.floor(min(vertices[:, 0])))
        right = min(width, math.ceil(max(vertices[:, 0])) + 1)
        top = max(0, math.floor(min(vertices[:, 1])))
        bottom = min(height, math.ceil(max(vertices[:, 1])) + 1)
        if left >= right or top >= bottom:
            continue
        x0, y0, z0 = vertices[0]
        x1, y1, z1 = vertices[1]
        x2, y2, z2 = vertices[2]
        determinant = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(determinant) < 1e-10:
            continue
        grid_y, grid_x = np.mgrid[top:bottom, left:right] + 0.5
        a = ((y1 - y2) * (grid_x - x2) + (x2 - x1) * (grid_y - y2)) / determinant
        b = ((y2 - y0) * (grid_x - x2) + (x0 - x2) * (grid_y - y2)) / determinant
        c = 1 - a - b
        depth = a * z0 + b * z1 + c * z2
        region = depth_buffer[top:bottom, left:right]
        visible = (a >= -1e-8) & (b >= -1e-8) & (c >= -1e-8) & (depth > region)
        region[visible] = depth[visible]
        rgb[top:bottom, left:right][visible] = color
    image = QtGui.QImage(rgb.data, width, height, width * 3, QtGui.QImage.Format_RGB888).copy()
    if not image.save(str(output)):
        raise ValueError("Could not save CAD preview {}".format(output))


def legacy_comparison(p, parts, output):
    import importlib.util
    if importlib.util.find_spec("PySide6"):
        from PySide6 import QtCore, QtGui
    else:
        from PySide2 import QtCore, QtGui
    legacy_dir = HERE.parents[1] / "v1.0" / "ring_3d"
    native = legacy_dir / "Lantern_Ring_Assembly.FCStd"
    body = legacy_dir / "Lantern_Ring_Assembly-ring_body_185.stl"
    doc = App.openDocument(str(native))
    setting, band = doc.Tube001, doc.Tube019
    reference = {
        "setting_diameter": 2 * setting.OuterRadius.Value,
        "setting_height_above_pcb": setting.Height.Value,
        "band_width": band.Height.Value,
        "band_wall": band.OuterRadius.Value - band.InnerRadius.Value,
        "finger_diameter": 2 * band.InnerRadius.Value,
        "band_centre_z": (band.Shape.BoundBox.ZMin + band.Shape.BoundBox.ZMax) / 2,
    }
    App.closeDocument(doc.Name)
    if reference != {"setting_diameter": 22.0, "setting_height_above_pcb": 5.0,
                     "band_width": 11.0, "band_wall": 1.0,
                     "finger_diameter": 18.5, "band_centre_z": -14.0}:
        raise ValueError("Legacy CAD reference changed; remeasure before resizing")
    reference["files_sha256"] = {path.relative_to(HERE.parents[2]).as_posix(): artifact_hash(path)
                                  for path in (native, body)}
    old = Mesh.Mesh(str(body))
    reference["body_width"] = old.BoundBox.XLength
    reference["body_height"] = old.BoundBox.ZLength
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication(["ring-comparison"])
    if not QtGui.QFontDatabase().families() and os.name == "nt":
        font = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf"
        if QtGui.QFontDatabase.addApplicationFont(str(font)) < 0:
            raise ValueError("Cannot load dimension comparison font")
    if not QtGui.QFontDatabase().families():
        raise ValueError("Cannot label dimension comparison without fonts")
    image = QtGui.QImage(900, 700, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor("#f4f6f8"))
    painter = QtGui.QPainter(image)
    painter.setPen(QtCore.Qt.NoPen)
    scale, baseline = 14, 410
    scenes = [
        (old, 230, (old.BoundBox.XMin + old.BoundBox.XMax) / 2,
         reference["band_centre_z"], "#64727e"),
    ]
    for name in PRINT_PARTS:
        scenes.append((mesh_for(parts[name], p), 670, 0,
                       -p["finger_diameter"] / 2 - p["band_wall"] / 2, "#28724d"))
    for mesh, centre_x, source_x, source_z, color in scenes:
        painter.setBrush(QtGui.QColor(color))
        for facet in mesh.Facets:
            points = [QtCore.QPointF(centre_x + scale * (v[0] - source_x),
                                    baseline - scale * (v[2] - source_z)) for v in facet.Points]
            painter.drawPolygon(QtGui.QPolygonF(points))
    painter.setPen(QtGui.QColor("#203040"))
    painter.setFont(QtGui.QFont("Arial", 16))
    painter.drawText(24, 32, "Legacy and compact v2: actual CAD silhouettes at the SAME scale")
    painter.setFont(QtGui.QFont("Arial", 12))
    labels = [
        (60, 65, "Legacy 18.5 mm body STL"),
        (490, 65, "Compact v2 printed assembly"),
        (60, 600, "Setting: 22 mm diameter; 5 mm above PCB"),
        (490, 600, "Socket: {:g} mm; bezel: {:g} mm diameter".format(
            2 * p["body_radius"], 2 * (p["screw_radius"] + p["screw_post_radius"]))),
        (60, 630, "Band: 11 mm wide, 1 mm wall; bore: 18.5 mm"),
        (490, 630, "Band: 11 mm wide, 1 mm wall; bore: {:g} mm".format(p["finger_diameter"])),
        (60, 675, "Front projection; bore centres aligned; 14 pixels/mm. NOT physical qualification."),
    ]
    for x, y, text in labels:
        painter.drawText(x, y, text)
    painter.end()
    if not image.save(str(output / "legacy-comparison.png")):
        raise ValueError("Cannot save measured legacy comparison")
    return reference


def generate(output=HERE / "generated", parameters_path=HERE / "parameters.json"):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    p, pcb = load_parameters(parameters_path), pcb_interface()
    s = validate_parameters(p, pcb)
    doc = create_document(p, pcb)
    parts = {name: doc.getObject(name).Shape for name in COLORS}
    checks = validate_geometry(p, pcb, parts)
    body_bounds = Part.makeCompound([parts[name] for name in PRINT_PARTS]).BoundBox
    reference = legacy_comparison(p, parts, output)
    checks.append("Legacy native CAD measured: 22 mm setting, 5 mm above PCB, 11 mm band")
    for name in PRINT_PARTS:
        parts[name].exportStep(str(output / (name + ".step")))
        loaded = Part.Shape()
        loaded.read(str(output / (name + ".step")))
        if (not loaded.isValid() or len(loaded.Solids) != 1
                or abs(loaded.Volume - parts[name].Volume) > 0.01):
            raise ValueError("{} STEP reload failed".format(name))
        # OCC 7.5's STEP reader resets edge tolerances to 1e-7 mm. A 1e-5 mm
        # check tolerance accommodates numeric curve conversion, not fit errors.
        loaded.fixTolerance(1e-5)
        loaded.check(True)
        shape = parts[name].copy()
        # Manufacturing meshes lie on the bed in their insertion orientation.
        if name != "RingBase":
            shape.rotate(App.Vector(), Z, -p["lock_angle"])
        shape.translate(App.Vector(0, 0, -shape.BoundBox.ZMin))
        mesh = mesh_for(shape, p)
        if not mesh.isSolid():
            raise ValueError("{} mesh is not watertight".format(name))
        mesh.write(str(output / (name + ".stl")))
        if not Mesh.Mesh(str(output / (name + ".stl"))).isSolid():
            raise ValueError("{} STL reload failed".format(name))
        checks.append("{} STL watertight and STEP valid after re-import".format(name))
    assembly = Part.makeCompound(list(parts.values()))
    assembly_path = output / "Lantern_Ring_v2.step"
    assembly.exportStep(str(assembly_path))
    loaded_assembly = Part.read(str(assembly_path))
    if (not loaded_assembly.isValid() or len(loaded_assembly.Solids) != len(assembly.Solids)
            or abs(loaded_assembly.Volume - assembly.Volume) > 0.02):
        raise ValueError("Assembly STEP roundtrip failed")
    loaded_assembly.fixTolerance(1e-5)
    for solid in loaded_assembly.Solids:
        solid.check(True)
    checks.append("Assembly STEP re-import preserves every solid and total volume")
    preview_png(parts, p, output / "assembly.png")
    explode = {}
    for name, shape in parts.items():
        lift = {"Carrier": 10, "Battery": 10, "NegativePogo": 10, "NegativeLead": 10,
                "PositiveLead": 24,
                "ContactDeck": 24, "PositivePogo": 24, "PCB": 35, "LEDs": 35, "Bezel": 44}.get(name, 0)
        explode[name] = shape.copy()
        explode[name].translate(App.Vector(0, 0, lift))
    preview_png(explode, p, output / "exploded.png")
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    native = output / "Lantern_Ring_v2.FCStd"
    doc.saveAs(str(native))
    doc_name = doc.Name
    App.closeDocument(doc_name)
    restored = App.openDocument(str(native))
    restored.recompute()
    for name in PRINT_PARTS:
        shape = restored.getObject(name).Shape
        if not shape.isValid() or abs(shape.Volume - parts[name].Volume) > 1e-5:
            raise ValueError("{} native document restore failed".format(name))
    checks.append("FCStd re-open/recompute preserves all four printed solids")
    report = {
        "freecad_version": ".".join(App.Version()[:3]),
        "pcb_sha256": source_hash(PCB_PATH),
        "source_sha256": {name: source_hash(HERE / name)
                          for name in ("design.py", "lantern_ring.py")},
        "artifact_sha256": {path.name: artifact_hash(path)
                            for path in sorted(output.iterdir())
                            if path.suffix.lower() in (".fcstd", ".step", ".stl", ".png")},
        "parameters": p,
        "pcb_interface": pcb,
        "stack": s,
        "legacy_reference": reference,
        "printed_body_envelope": {
            "width": body_bounds.XLength,
            "depth": body_bounds.YLength,
            "height": body_bounds.ZLength,
        },
        "checks": checks,
        "physical_test_status": "NOT PRINTED: fit, wear, electrical continuity and battery safety require bench validation",
    }
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Generated {}. {} checks passed.".format(output, len(checks)))
    return restored


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "generated")
    parser.add_argument("--parameters", type=Path, default=HERE / "parameters.json")
    args = parser.parse_args()
    try:
        # Persist proxies under their importable module, never "__main__".
        from lantern_ring import generate as build_document
        build_document(args.output, args.parameters)
    except Exception as error:
        print("FreeCAD generation FAILED: {}".format(error), file=sys.stderr)
        raise
