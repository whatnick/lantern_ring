"""Blender 5: kit explosion/implosion, jaw motion and interchangeable pogo grids."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "generated" / "assembly"
BUILD = HERE / "build"
HUD = None


def material(name, rgb, metal=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = 0.75 if metal else 0
    bsdf.inputs["Roughness"].default_value = 0.28 if metal else 0.45
    return mat


def text(body, location, size, color=(0.9, 0.94, 1.0)):
    curve = bpy.data.curves.new("caption", "FONT")
    curve.body = body
    curve.size = size
    obj = bpy.data.objects.new("caption", curve)
    bpy.context.collection.objects.link(obj)
    obj.parent = HUD
    obj.location = location
    mat = material("text", color)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = 1
    obj.data.materials.append(mat)
    return obj


def visibility(obj, start, end):
    for frame, hidden in ((1, start > 1), (max(1, start - 1), True),
                          (start, False), (end, False), (end + 1, True)):
        obj.hide_render = hidden
        obj.hide_viewport = hidden
        obj.keyframe_insert("hide_render", frame=frame)
        obj.keyframe_insert("hide_viewport", frame=frame)


def displacement(name):
    if name == "LowerJaw":
        return (0, 0, 0), 1
    if name == "Spring":
        return (0, 30, 5), 20
    if name == "UpperJaw":
        return (0, 0, 18), 40
    if name == "Hinge":
        return (0, -35, 0), 60
    if name == "Grip":
        return (0, 0, 30), 75
    if name == "Guide":
        return (0, -28, 0), 90
    if name == "Probe":
        return (0, 0, 28), 105
    if name == "Pads":
        return (0, 0, 28), 105
    if name.startswith("Nut"):
        return (0, -28, -4), 120
    if name.startswith("Screw"):
        return (0, 0, 45), 120
    if name.startswith(("Barrel", "Plunger")):
        return (0, 0, 40), 140
    if name.startswith("Header"):
        return (0, 0, 50), 140
    return (0, 0, 0), 1


def import_variant(variant, active_start, active_end, animate=False):
    entries = json.loads((OUT / variant / "meshes.json").read_text())
    root = bpy.data.objects.new(variant, None)
    bpy.context.collection.objects.link(root)
    root.location = (-27, 0, -8)
    motion = bpy.data.objects.new("Hinge rotation", None)
    bpy.context.collection.objects.link(motion)
    motion.parent = root
    motion.location = (27.5, 0, 5.5)
    for entry in entries:
        name = entry["name"]
        bpy.ops.wm.stl_import(filepath=str(OUT / variant / entry["file"]))
        obj = bpy.context.object
        obj.name = variant + "_" + name
        surface = entry.get("visual_surface_only", False)
        if surface:
            # Separate coplanar render layers visually; never change CAD/contact datums.
            extra = 0.04 * entry["surface_normal_z"]
            for vertex in obj.data.vertices:
                vertex.co.z += extra
        stationary = name in ("LowerJaw", "Hinge", "Spring", "Ring", "RingParts",
                              "Riser", "Anvil", "Fence") or name.startswith(("PCB_", "AnvilPCB_", "FencePCB_"))
        obj.parent = root if stationary else motion
        if not stationary:
            obj.location = (-27.5, 0, -5.5)
        obj.data.materials.append(material(name, entry["color"],
            name.startswith(("Barrel", "Plunger", "Screw", "Nut")) or
            name in ("Hinge", "Spring", "Pins", "HeaderPins", "Pads")))
        if not surface:
            bevel = obj.modifiers.new("Edge highlights", "BEVEL")
            bevel.width = 0.12
            bevel.segments = 2
        if name == "Spring":
            curve = obj.driver_add("scale", 2)
            var = curve.driver.variables.new()
            var.name = "a"
            var.targets[0].id = motion
            var.targets[0].data_path = "rotation_euler[1]"
            e = json.loads((ROOT / "assembly_parameters.json").read_text())["estimated"]
            curve.driver.expression = (
                "({hz}+({gap}+{wire2}-{hz}-sin(a)*({sx}-{hx}))/cos(a)"
                "-{r}*abs(tan(a))-{wire2})/{gap}").format(
                    hz=e["hinge_z"], gap=e["working_gap"], wire2=2 * e["spring_wire_radius"],
                    sx=e["spring_x"], hx=e["hinge_x"], r=e["spring_radius"])
        visibility(obj, active_start, active_end)
        if variant == "ir_custom" and not name.startswith("PCB_") and name not in ("Ring", "RingParts"):
            part = name.split("PCB_")[0] if "PCB_" in name else name
            delta = {"Probe": (0, 0, 25), "Guide": (0, -18, 7),
                     "Anvil": (0, -14, 0), "Fence": (0, -14, 8),
                     "Pins": (0, 0, 35), "Header": (0, 0, 25),
                     "HeaderPins": (0, 0, 25), "Screws": (0, 0, 35),
                     "Nuts": (0, -18, 4)}.get(part, (0, 0, 0))
            base = obj.location.copy()
            for frame, amount in ((321, 1), (330, 1), (348, 0), (440, 0)):
                obj.location = base + Vector(delta) * amount
                obj.keyframe_insert("location", frame=frame)
        if variant == "ir_custom" and (name in ("Ring", "RingParts") or name.startswith("PCB_")):
            # Show the actual rear copper/mask clearly, then lower the board into its pocket.
            for frame, offset in ((321, (0, 0, 0)), (360, (0, 0, 0)),
                                  (380, (-12, -12, 18)), (410, (-12, -12, 18)),
                                  (435, (0, 0, 0)), (440, (0, 0, 0))):
                obj.location = offset
                obj.keyframe_insert("location", frame=frame)
        if animate:
            delta, settle = displacement(name)
            base = obj.location.copy()
            for frame, amount in ((1, 1), (settle, 1), (settle + 18, 0),
                                  (180, 0), (198, 1), (216, 0)):
                obj.location = base + Vector(delta) * amount
                obj.keyframe_insert("location", frame=frame)
    poses = ((1, 0), (208, 0), (222, 6), (235, 0), (240, 0),
             (active_start, 0), (active_end - 12, 6), (active_end, 0))
    if variant == "ir_custom":
        poses = ((321, 0), (348, 6), (360, 0), (375, 6), (420, 6), (440, 0))
    for frame, degrees in poses:
        if not animate and frame < active_start:
            continue
        motion.rotation_euler[1] = math.radians(degrees)
        motion.keyframe_insert("rotation_euler", frame=frame)
    if variant == "ir_custom":
        ground_lead(root, motion, active_end)
    return root


def ground_lead(root, motion, end):
    """Illustrative flexible lead; not included in the rigid CAD clearance claim."""
    curve = bpy.data.curves.new("GND service loop", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.22
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    layers = json.loads((OUT / "clip_board_layers.json").read_text())["boards"]
    geometry = json.loads((ROOT / "generated" / "geometry.json").read_text())
    params = json.loads((ROOT / "parameters.json").read_text())
    lower_tip = geometry["fit_inputs"]["probe"]["lower_tip_v"]
    gap = params["clip_kit"]["geometry"]["parallel_gap_tip"]
    thickness = 1.6
    anvil_top = gap - thickness - geometry["target_thickness_mm"]
    probe_top = gap + params["clip_kit"]["geometry"]["upper_tip_thickness"] + thickness

    def endpoint(board, ref, z):
        source = layers[board]
        pad = next(p for p in source["pads"] if p["ref"] == ref)
        x, y = pad["xy_mm"]
        ox, oy = source["origin_xy_mm"]
        return (y - oy - lower_tip, x - ox, z)

    first, last = endpoint("probe", "J2", probe_top), endpoint("anvil", "J1", anvil_top)
    points = [first, (-8, 13, 18), (15, 13, 10), last]
    spline.bezier_points.add(len(points) - 1)
    for p, co in zip(spline.bezier_points, points):
        p.co = co
        p.handle_left_type = p.handle_right_type = "AUTO"
    wire = bpy.data.objects.new("GND lead: probe J2 to anvil J1", curve)
    bpy.context.collection.objects.link(wire)
    wire.parent = root
    wire.data.materials.append(material("Insulated ground lead", (0.035, 0.035, 0.045)))
    visibility(wire, 349, end)
    p = spline.bezier_points[0]
    e = json.loads((ROOT / "assembly_parameters.json").read_text())["estimated"]
    hx, hz = e["hinge_x"], e["hinge_z"]
    for axis, expression in (
            (0, "{hx}+cos(a)*({x}-{hx})+sin(a)*({z}-{hz})"),
            (2, "{hz}-sin(a)*({x}-{hx})+cos(a)*({z}-{hz})")):
        driver = p.driver_add("co", axis).driver
        var = driver.variables.new()
        var.name = "a"
        var.targets[0].id = motion
        var.targets[0].data_path = "rotation_euler[1]"
        driver.expression = expression.format(hx=hx, hz=hz, x=first[0], z=first[2])


def main():
    global HUD
    bpy.context.preferences.filepaths.save_version = 0
    parser = argparse.ArgumentParser()
    parser.add_argument("--stills", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES" if args.stills else "BLENDER_EEVEE"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.fps = 20
    scene.frame_start, scene.frame_end = 1, 440
    scene.world.color = (0.18, 0.18, 0.18)
    bpy.ops.object.camera_add(location=(-100, -135, 95))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, 0, 20)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 142
    scene.camera = camera
    HUD = bpy.data.objects.new("Screen captions", None)
    bpy.context.collection.objects.link(HUD)
    HUD.parent = camera
    for frame, scale, height in ((1, 142, 95), (145, 142, 95), (165, 110, 83),
                                 (180, 110, 83), (198, 142, 95),
                                 (216, 110, 83), (440, 110, 83)):
        camera.data.ortho_scale = scale
        camera.data.keyframe_insert("ortho_scale", frame=frame)
        camera.location.z = height
        camera.keyframe_insert("location", frame=frame)
        HUD.scale = (scale / 142,) * 3
        HUD.keyframe_insert("scale", frame=frame)
    for location, power, size in (((-45, -60, 110), 180000, 90),
                                   ((70, 30, 80), 140000, 80),
                                   ((0, 65, 20), 80000, 60)):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (Vector((0, 0, 15)) - light.location).to_track_quat("-Z", "Y").to_euler()
    text("ALIEXPRESS POGO CLIP  /  ASSEMBLY GUIDE", (-65, 45, -100), 3.2)
    text("Photo reconstruction: partial measurements, not a qualified jig", (-65, -43, -100), 2.1)
    text("CR2032 REMOVED before programming  |  colours illustrative", (-65, -48, -100), 2.1,
         (1.0, 0.72, 0.3))
    stages = [
        (1, 39, "01  Lower jaw and compression spring"),
        (40, 74, "02  Upper jaw, then insert hinge pin"),
        (75, 104, "03  Grip block and lower guide PCB"),
        (105, 139, "04  Probe PCB, M2 screws and nuts"),
        (140, 179, "05  Insert pogo pins through BOTH boards; solder tops only"),
        (180, 207, "EXPLOSION  /  component identification"),
        (208, 240, "2.54 mm  /  squeeze rear handles to open jaws"),
        (241, 280, "1.27 mm  /  fine pins; do not reuse large guide drills"),
        (281, 320, "2.00 mm  /  same mechanism, different probe/guide grid"),
        (321, 348, "CUSTOM PCBs  /  probe + identical guide, anvil + fence"),
        (349, 360, "ISP GND -> probe J2 -> wire -> anvil J1 -> front TP8"),
        (361, 410, "ACTUAL KiCad IR PCB  /  rear copper, mask and test pads"),
        (411, 440, "Insert PCB LEDs down  /  close onto custom probe"),
    ]
    for start, end, title in stages:
        caption = text(title, (-65, 39, -100), 2.4)
        visibility(caption, start, end)
    caption = text("Stock 2.54 mm pogo grid does NOT match the IR PCB", (-65, -37, -100), 2.3,
                   (1, 0.5, 0.3))
    visibility(caption, 208, 440)
    import_variant("pitch_254", 1, 240, True)
    import_variant("pitch_127", 241, 280)
    import_variant("pitch_200", 281, 320)
    import_variant("ir_custom", 321, 440)
    # Frame at the assembled state rather than the exploded endpoint.
    if args.stills:
        for frame, filename in ((179, "assembled.png"), (198, "exploded.png"),
                                (254, "pitch_127.png"), (294, "pitch_200.png"),
                                (335, "ir_adapter_exploded.png"), (350, "ir_adapter.png"),
                                (400, "ir_actual_pcb.png")):
            scene.frame_set(frame)
            scene.render.filepath = str(OUT / filename)
            bpy.ops.render.render(write_still=True)
    else:
        BUILD.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "clip_assembly.blend"))
        scene.render.filepath = str(BUILD / "frame_")
        if not args.prepare:
            bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
