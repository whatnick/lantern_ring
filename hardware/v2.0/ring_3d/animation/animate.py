"""Blender 5 animation: exploded v2 Lantern Ring assembles, locks and lights up.

Run headless after export_parts.py:
    blender -b -P animate.py -- [--preview] [--frames START END]
    blender -b -P animate.py -- --lineup      # all Lantern Corps crowns
Frames go to build/frames; render.ps1 encodes the MP4/GIF.
"""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
MESHES = HERE / "build" / "meshes"
MM = 0.001
FPS = 24
END = 216
LANTERN_GREEN = (0.03, 1.0, 0.22, 1.0)

# Exploded lift (mm) and the frame range in which each group drops onto the carrier.
GROUPS = {
    "carrier": (("Carrier", "Battery", "NegativePogo", "NegativeLead"), 10, None),
    "deck": (("ContactDeck", "PositivePogo", "PositiveLead"), 24, (24, 48)),
    "pcb": (("PCB", "LEDs"), 35, (40, 64)),
    "crown": (("Crown_will",), 44, (56, 80)),
}
INSERT = (88, 112)
TWIST = (112, 128)
GLOW = (140, 152, 164)
LINEUP = HERE.parent / "generated" / "crowns" / "lineup.png"
# Lantern Corps light colours (linear RGB) for the crown lineup.
CORPS_COLORS = {
    "will": (0.03, 1.0, 0.22), "fear": (1.0, 0.80, 0.02), "rage": (1.0, 0.03, 0.02),
    "avarice": (1.0, 0.28, 0.01), "hope": (0.04, 0.30, 1.0), "compassion": (0.18, 0.04, 0.80),
    "love": (0.75, 0.10, 1.0), "life": (0.85, 0.85, 0.85),
}
PARTS = {}

MATERIALS = {
    # name: (base colour, metallic, roughness)
    "RingBase": ((0.02, 0.42, 0.10), 0.85, 0.28),
    "Carrier": ((0.08, 0.42, 0.20), 0.0, 0.45),
    "ContactDeck": ((0.78, 0.60, 0.28), 0.0, 0.5),
    "PCB": ((0.04, 0.20, 0.08), 0.0, 0.4),
    "Battery": ((0.80, 0.80, 0.82), 1.0, 0.22),
    "PositivePogo": ((1.0, 0.76, 0.34), 1.0, 0.2),
    "NegativePogo": ((1.0, 0.76, 0.34), 1.0, 0.2),
    "PositiveLead": ((0.80, 0.80, 0.82), 1.0, 0.3),
    "NegativeLead": ((0.04, 0.04, 0.05), 0.0, 0.5),
    "LEDs": ((0.9, 0.95, 0.9), 0.0, 0.25),
}


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="low resolution, few samples")
    parser.add_argument("--frames", nargs=2, type=int, default=(1, END))
    parser.add_argument("--no-render", action="store_true", help="only save the .blend")
    parser.add_argument("--stills", nargs="+", type=int, help="render single frames to build/stills")
    parser.add_argument("--lineup", action="store_true", help="render all corps crowns to " + str(LINEUP))
    return parser.parse_args(argv)


def principled(name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat, bsdf


def keyframe_emission(bsdf, values):
    socket = bsdf.inputs["Emission Strength"]
    for frame, value in values:
        socket.default_value = value
        socket.keyframe_insert("default_value", frame=frame)


def import_part(name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=str(MESHES / (name + ".stl")), global_scale=MM)
    (obj,) = set(bpy.data.objects) - before
    obj.name = name
    for other in bpy.context.selected_objects:
        other.select_set(other == obj)
    bpy.context.view_layer.objects.active = obj
    PARTS[name] = obj
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    except (AttributeError, RuntimeError):
        pass
    return obj


def crown_material(key):
    """Translucent print-in-place diffuser plastic in the corps colour."""
    color = CORPS_COLORS[key]
    # Frosted (rough) so the key light does not wash the lit green out to cyan.
    mat, bsdf = principled("Crown_" + key, tuple(0.55 * c for c in color), 0.0, 0.7)
    bsdf.inputs["Transmission Weight"].default_value = 0.25
    bsdf.inputs["Specular IOR Level"].default_value = 0.1
    bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    return mat, bsdf


def key(obj, frame, lift=None, angle=None):
    if lift is not None:
        obj.location.z = lift * MM
        obj.keyframe_insert("location", index=2, frame=frame)
    if angle is not None:
        obj.rotation_euler.z = math.radians(angle)
        obj.keyframe_insert("rotation_euler", index=2, frame=frame)


def build_parts(info):
    lock = info["lock_angle"]
    for group, (names, lift, drop) in GROUPS.items():
        for name in names:
            obj = import_part(name)
            if name.startswith("Crown_"):
                mat, crown_bsdf = crown_material(name[len("Crown_"):])
            else:
                mat = principled(name, *MATERIALS[name])[0]
            obj.data.materials.append(mat)
            key(obj, 1, lift, 0)
            if drop:
                key(obj, drop[0], lift)
                key(obj, drop[1], GROUPS["carrier"][1])
            key(obj, INSERT[0], GROUPS["carrier"][1])
            key(obj, INSERT[1], 0)
            key(obj, TWIST[0], angle=0)
            key(obj, TWIST[1], angle=lock)
    base = import_part("RingBase")
    base.data.materials.append(principled("RingBase", *MATERIALS["RingBase"])[0])

    leds = PARTS["LEDs"]
    mat, bsdf = principled("LED", *MATERIALS["LEDs"])
    bsdf.inputs["Emission Color"].default_value = LANTERN_GREEN
    # The crown lens diffuses the LEDs; strong LED emission saturates it to cyan.
    keyframe_emission(bsdf, [(GLOW[0], 0.0), (GLOW[1], 4.0), (GLOW[2], 2.5)])
    leds.data.materials.clear()
    leds.data.materials.append(mat)

    # The LEDs light the crown lens and logo from below.
    keyframe_emission(crown_bsdf, [(GLOW[0], 0.0), (GLOW[1], 0.7), (GLOW[2], 0.4)])

    glow = bpy.data.lights.new("LEDGlow", "POINT")
    glow.color = LANTERN_GREEN[:3]
    glow.shadow_soft_size = 4 * MM
    for frame, energy in ((1, 0.0), (GLOW[0], 0.0), (GLOW[1], 0.025), (GLOW[2], 0.015)):
        glow.energy = energy
        glow.keyframe_insert("energy", frame=frame)
    light = bpy.data.objects.new("LEDGlow", glow)
    # Above the low-profile crown so the green spill lights the band, not a hotspot.
    light.location = (0, 0, (info["stack"]["highest_component"] + 9) * MM)
    bpy.context.collection.objects.link(light)


def area_light(name, location, energy, size, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = energy, size, color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    bpy.context.collection.objects.link(obj)
    track = obj.constraints.new("TRACK_TO")
    track.target = bpy.data.objects["Target"]
    return data


def stage(info):
    target = bpy.data.objects.new("Target", None)
    bpy.context.collection.objects.link(target)
    rig = bpy.data.objects.new("CameraRig", None)
    bpy.context.collection.objects.link(rig)

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 60
    cam_data.clip_start, cam_data.clip_end = 0.02, 2
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = target
    cam_data.dof.aperture_fstop = 11
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.parent = rig
    bpy.context.collection.objects.link(cam)
    cam.constraints.new("TRACK_TO").target = target
    bpy.context.scene.camera = cam

    # (frame, target height mm, camera distance mm, orbit and elevation degrees)
    for frame, height, distance, orbit, elevation in (
            (1, 26, 300, -40, 22), (90, 14, 200, -5, 26),
            (150, 2, 150, 25, 34), (END, 2, 135, 70, 46)):
        target.location.z = height * MM
        target.keyframe_insert("location", index=2, frame=frame)
        cam.location = (0, -distance * MM * math.cos(math.radians(elevation)),
                        distance * MM * math.sin(math.radians(elevation)) + height * MM)
        cam.keyframe_insert("location", frame=frame)
        rig.rotation_euler.z = math.radians(orbit)
        rig.keyframe_insert("rotation_euler", index=2, frame=frame)

    key_light = area_light("Key", (0.12, -0.12, 0.16), 1.2, 0.12)
    area_light("Fill", (-0.16, -0.06, 0.06), 0.35, 0.2, (0.85, 0.9, 1.0))
    area_light("Rim", (0.0, 0.18, 0.12), 1.0, 0.1)
    for frame, energy in ((1, 1.2), (GLOW[0], 1.2), (GLOW[2], 0.6)):
        key_light.energy = energy
        key_light.keyframe_insert("energy", frame=frame)

    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.014, 0.018, 1)
    bpy.context.scene.world = world

    floor_z = min(o.bound_box[0][2] for o in bpy.data.objects if o.type == "MESH")
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, floor_z - 2 * MM))
    floor, _ = principled("Floor", (0.02, 0.025, 0.03), 0.0, 0.18)
    bpy.context.object.data.materials.append(floor)


def compositor_glow(scene):
    """Bloom via the Blender 5 compositor; skipped if the API differs."""
    try:
        tree = bpy.data.node_groups.new("Glow", "CompositorNodeTree")
        tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        layers = tree.nodes.new("CompositorNodeRLayers")
        glare = tree.nodes.new("CompositorNodeGlare")
        output = tree.nodes.new("NodeGroupOutput")
        for name, value in (("Type", "Bloom"), ("Threshold", 0.9), ("Strength", 0.4), ("Size", 0.5)):
            if name in glare.inputs:
                glare.inputs[name].default_value = value
        tree.links.new(layers.outputs["Image"], glare.inputs["Image"])
        tree.links.new(glare.outputs["Image"], output.inputs[0])
        scene.compositing_node_group = tree
        scene.render.use_compositing = True
        return True
    except (AttributeError, KeyError, RuntimeError, TypeError) as error:
        print("Compositor glow skipped: {}".format(error))
        return False


def lineup(info):
    """Two rows of crowns, logo up in the locked pose, each glowing in its corps colour."""
    keys = list(info["crowns"])
    spacing = 30
    for index, key in enumerate(keys):
        obj = import_part("Crown_" + key)
        obj.data.materials.append(crown_material(key)[0])
        obj.data.materials[0].node_tree.nodes["Principled BSDF"].inputs[
            "Emission Strength"].default_value = 0.08
        row, col = divmod(index, 4)
        obj.rotation_euler.z = math.radians(info["lock_angle"])
        obj.location = ((col - 1.5) * spacing * MM, (0.5 - row) * spacing * MM,
                        -info["stack"]["assembly_top"] * MM)
    target = bpy.data.objects.new("Target", None)
    bpy.context.collection.objects.link(target)
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 60
    cam_data.clip_start, cam_data.clip_end = 0.02, 2
    cam = bpy.data.objects.new("Camera", cam_data)
    elevation = math.radians(48)
    cam.location = (0, -0.24 * math.cos(elevation), 0.24 * math.sin(elevation))
    cam.constraints.new("TRACK_TO").target = target
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    # Low grazing key so the 0.6 mm logo relief casts readable shadows.
    area_light("Key", (0.22, -0.06, 0.05), 0.9, 0.06)
    area_light("Fill", (-0.16, -0.08, 0.10), 0.12, 0.25, (0.85, 0.9, 1.0))
    area_light("Rim", (0.0, 0.20, 0.12), 0.4, 0.15)
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.014, 0.018, 1)
    bpy.context.scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, -0.02 * MM))
    floor, _ = principled("Floor", (0.02, 0.025, 0.03), 0.0, 0.18)
    bpy.context.object.data.materials.append(floor)


def main():
    options = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    info = json.loads((MESHES / "scene.json").read_text(encoding="utf-8"))
    scene = bpy.context.scene
    if options.lineup:
        lineup(info)
    else:
        build_parts(info)
        stage(info)
    scene.frame_start, scene.frame_end = options.frames
    scene.render.fps = FPS
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.eevee.taa_render_samples = 8 if options.preview else 48
    scene.render.resolution_x, scene.render.resolution_y = (640, 360) if options.preview else (1280, 720)
    scene.render.image_settings.file_format = "PNG"
    # Standard keeps the Lantern greens saturated; AgX desaturates them to mint.
    scene.view_settings.view_transform = "Standard"
    glow = compositor_glow(scene)
    build = HERE / "build"
    if options.lineup:
        scene.render.resolution_x, scene.render.resolution_y = (1600, 800)
        scene.render.filepath = str(LINEUP)
        bpy.ops.render.render(write_still=True)
        return
    scene.render.filepath = str(build / "frames" / "frame_")
    bpy.ops.wm.save_as_mainfile(filepath=str(build / "lantern_ring_v2_assembly.blend"))
    print("Scene ready: engine {}, compositor glow {}".format(scene.render.engine, glow))
    if options.stills:
        for frame in options.stills:
            scene.frame_set(frame)
            scene.render.filepath = str(build / "stills" / "frame_{:03d}.png".format(frame))
            bpy.ops.render.render(write_still=True)
    elif not options.no_render:
        bpy.ops.render.render(animation=True)


main()
