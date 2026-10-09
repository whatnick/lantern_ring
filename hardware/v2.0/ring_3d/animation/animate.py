"""Blender 5 animation: exploded v2 Lantern Ring assembles, locks and lights up.

Run headless after export_parts.py:
    blender -b -P animate.py -- [--preview] [--frames START END]
Frames go to build/frames; render.ps1 encodes the MP4/GIF.
"""

import argparse
import json
import math
from pathlib import Path
import sys

import bmesh
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
    "bezel": (("Bezel",), 44, (56, 80)),
}
INSERT = (88, 112)
TWIST = (112, 128)
EMBLEM_LIFT, EMBLEM_DROP = 56, (128, 150)
GLOW = (156, 166, 174)
PARTS = {}

MATERIALS = {
    # name: (base colour, metallic, roughness)
    "RingBase": ((0.02, 0.42, 0.10), 0.85, 0.28),
    "Carrier": ((0.08, 0.42, 0.20), 0.0, 0.45),
    "ContactDeck": ((0.78, 0.60, 0.28), 0.0, 0.5),
    "Bezel": ((0.05, 0.55, 0.22), 0.0, 0.55),
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


def clean_mesh(obj):
    """The v1 emblem STL has duplicate vertices and mixed normals."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.remove_doubles(mesh, verts=mesh.verts, dist=0.002 * MM)
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)
    mesh.to_mesh(obj.data)
    mesh.free()
    for polygon in obj.data.polygons:
        polygon.use_smooth = False


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
            obj.data.materials.append(principled(name, *MATERIALS[name])[0])
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
    keyframe_emission(bsdf, [(GLOW[0], 0.0), (GLOW[1], 30.0), (GLOW[2], 18.0)])
    leds.data.materials.clear()
    leds.data.materials.append(mat)

    emblem = import_part("Emblem")
    clean_mesh(emblem)
    mat, bsdf = principled("Emblem", (0.02, 0.55, 0.12), 0.0, 0.25)
    bsdf.inputs["Transmission Weight"].default_value = 0.2
    bsdf.inputs["Emission Color"].default_value = LANTERN_GREEN
    keyframe_emission(bsdf, [(GLOW[0], 0.0), (GLOW[1], 2.0), (GLOW[2], 1.1)])
    emblem.data.materials.append(mat)
    # Emblem bars stay across the finger (X) regardless of the cassette lock angle.
    key(emblem, 1, EMBLEM_LIFT, 0)
    key(emblem, EMBLEM_DROP[0], EMBLEM_LIFT)
    key(emblem, EMBLEM_DROP[1], 0)

    glow = bpy.data.lights.new("LEDGlow", "POINT")
    glow.color = LANTERN_GREEN[:3]
    glow.shadow_soft_size = 4 * MM
    for frame, energy in ((1, 0.0), (GLOW[0], 0.0), (GLOW[1], 0.25), (GLOW[2], 0.15)):
        glow.energy = energy
        glow.keyframe_insert("energy", frame=frame)
    light = bpy.data.objects.new("LEDGlow", glow)
    light.location = (0, 0, (info["stack"]["highest_component"] + 1.5) * MM)
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
        for name, value in (("Type", "Bloom"), ("Threshold", 4.0), ("Strength", 0.4), ("Size", 0.5)):
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


def main():
    options = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    info = json.loads((MESHES / "scene.json").read_text(encoding="utf-8"))
    scene = bpy.context.scene
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
