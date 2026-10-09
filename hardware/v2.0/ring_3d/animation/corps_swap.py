"""Blender 5: swap Lantern Corps crowns on the assembled v2 ring, then a hero still.

Run headless after crowns.py and export_parts.py:
    blender -b -P corps_swap.py -- [--preview] [--stills N ...] [--frames A B]
    blender -b -P corps_swap.py -- --hero      # generated/crowns/hero.png
Frames go to build/swap_frames; render_corps.ps1 encodes the MP4/GIF.
"""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import animate as A  # noqa: E402

SEGMENT = 50          # frames per corps
LIFT = 30             # mm a crown travels when removed or fitted
TAIL = 24             # frames held after the last corps
HERO = HERE.parent / "generated" / "crowns" / "hero.png"
BUILD = HERE / "build"
CASSETTE = [n for names, _, _ in A.GROUPS.values() for n in names if not n.startswith("Crown_")]
LED_ON, CROWN_ON, GLOW_ON = 2.5, 0.4, 0.015


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--frames", nargs=2, type=int)
    parser.add_argument("--stills", nargs="+", type=int)
    parser.add_argument("--hero", action="store_true")
    return parser.parse_args(argv)


def rgba(color):
    return (*color, 1.0)


def body_color(key):
    """Ring body in a darker metallic tone of the corps light."""
    return tuple(min(1.0, 0.42 * c) for c in A.CORPS_COLORS[key])


def socket_key(bsdf, name, frame, value):
    socket = bsdf.inputs[name]
    socket.default_value = value
    socket.keyframe_insert("default_value", frame=frame)


def hide(obj, frame, hidden):
    obj.hide_render = hidden
    obj.keyframe_insert("hide_render", frame=frame)


def ring(info, crowns, parent=None):
    """One assembled, locked ring with the given crowns; returns {name: (obj, bsdf)}."""
    lock = math.radians(info["lock_angle"])
    parts = {}
    for name in CASSETTE + ["RingBase"]:
        obj = A.import_part(name)
        mat, bsdf = A.principled(name, *A.MATERIALS[name])
        obj.data.materials.append(mat)
        if name != "RingBase":
            obj.rotation_euler.z = lock
        parts[name] = (obj, bsdf)
    for key in crowns:
        obj = A.import_part("Crown_" + key)
        mat, bsdf = A.crown_material(key)
        obj.data.materials.append(mat)
        obj.rotation_euler.z = lock
        parts["Crown_" + key] = (obj, bsdf)
    if parent is not None:
        for obj, _ in parts.values():
            obj.parent = parent
    return parts


def steel_floor(z):
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, z))
    floor = bpy.context.object
    mat = bpy.data.materials.new("BrushedSteel")
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.30, 0.31, 0.33, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    if "Anisotropic" in bsdf.inputs:
        bsdf.inputs["Anisotropic"].default_value = 0.6
    # Fine streaks along X: high-frequency noise across Y drives the roughness.
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (4, 1500, 1)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Detail"].default_value = 6
    rough = nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.24
    rough.inputs["To Max"].default_value = 0.42
    links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], rough.inputs["Value"])
    links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    floor.data.materials.append(mat)
    return floor


def world(color=(0.010, 0.011, 0.014)):
    w = bpy.data.worlds.new("Studio")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (*color, 1)
    bpy.context.scene.world = w


def mesh_min_z():
    bpy.context.view_layer.update()
    return min((o.matrix_world @ Vector(c)).z for o in bpy.data.objects
               if o.type == "MESH" for c in o.bound_box)


def point_glow(name, color, location, energy=0.0):
    data = bpy.data.lights.new(name, "POINT")
    data.color, data.energy, data.shadow_soft_size = color, energy, 4 * A.MM
    # Coloured spill only: a specular point would mirror as a blob in the steel.
    data.specular_factor = 0.0
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    bpy.context.collection.objects.link(obj)
    return data


def caption(camera, text, color):
    curve = bpy.data.curves.new("Caption", "FONT")
    curve.body, curve.align_x, curve.size = text, "CENTER", 0.0021
    obj = bpy.data.objects.new("Caption", curve)
    bpy.context.collection.objects.link(obj)
    obj.parent = camera
    obj.location = (0, -0.0142, -0.1)
    mat, bsdf = A.principled("Caption", tuple(0.3 * c for c in color), 0.0, 0.5)
    bsdf.inputs["Emission Color"].default_value = rgba(color)
    bsdf.inputs["Emission Strength"].default_value = 1.0
    curve.materials.append(mat)
    return obj


def swap(info):
    keys = list(info["crowns"])
    parts = ring(info, keys)
    leds = parts["LEDs"][1]
    base = parts["RingBase"][1]
    leds.inputs["Emission Color"].default_value = rgba(A.CORPS_COLORS[keys[0]])
    base.inputs["Base Color"].default_value = rgba(body_color(keys[0]))
    glow = point_glow("LEDGlow", A.CORPS_COLORS[keys[0]],
                      (0, 0, (info["stack"]["highest_component"] + 9) * A.MM))

    target = bpy.data.objects.new("Target", None)
    target.location.z = 6 * A.MM
    bpy.context.collection.objects.link(target)
    rig = bpy.data.objects.new("CameraRig", None)
    bpy.context.collection.objects.link(rig)
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens, cam_data.clip_start, cam_data.clip_end = 60, 0.02, 2
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.parent = rig
    elevation, distance = math.radians(32), 125 * A.MM
    cam.location = (0, -distance * math.cos(elevation), distance * math.sin(elevation) + 6 * A.MM)
    cam.constraints.new("TRACK_TO").target = target
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    end = len(keys) * SEGMENT + TAIL
    for frame, orbit in ((1, -35), (end, 55)):
        rig.rotation_euler.z = math.radians(orbit)
        rig.keyframe_insert("rotation_euler", index=2, frame=frame)

    # Will starts fitted and lights up; every later corps swaps in.
    first = parts["Crown_" + keys[0]]
    hide(first[0], 1, False)
    for name, value in ((leds, LED_ON), (first[1], CROWN_ON)):
        socket_key(name, "Emission Strength", 1, 0.0)
        socket_key(name, "Emission Strength", 10, value)
    for frame, energy in ((1, 0.0), (10, GLOW_ON)):
        glow.energy = energy
        glow.keyframe_insert("energy", frame=frame)
    show_from = 1
    for i, key in enumerate(keys):
        crown, crown_bsdf = parts["Crown_" + key]
        color = A.CORPS_COLORS[key]
        s = 1 + i * SEGMENT
        if i:
            prev, prev_bsdf = parts["Crown_" + keys[i - 1]]
            old = A.CORPS_COLORS[keys[i - 1]]
            dark, removed, fitted, lit = s + 5, s + 13, s + 23, s + 29
            for bsdf, value in ((leds, LED_ON), (prev_bsdf, CROWN_ON)):
                socket_key(bsdf, "Emission Strength", s, value)
                socket_key(bsdf, "Emission Strength", dark, 0.0)
            for frame, energy in ((s, GLOW_ON), (dark, 0.0), (fitted, 0.0), (lit, GLOW_ON)):
                glow.energy = energy
                glow.keyframe_insert("energy", frame=frame)
            # Change the light colour while it is dark.
            socket_key(leds, "Emission Color", dark, rgba(old))
            socket_key(leds, "Emission Color", dark + 1, rgba(color))
            for frame, c in ((dark, old), (dark + 1, color)):
                glow.color = c
                glow.keyframe_insert("color", frame=frame)
            A.key(prev, dark, 0)
            A.key(prev, removed, LIFT)
            hide(prev, removed, True)
            A.key(crown, 1, LIFT)
            hide(crown, 1, True)
            hide(crown, removed, False)
            A.key(crown, removed, LIFT)
            A.key(crown, fitted, 0)
            socket_key(base, "Base Color", removed, rgba(body_color(keys[i - 1])))
            socket_key(base, "Base Color", fitted, rgba(body_color(key)))
            for bsdf, value in ((leds, LED_ON), (crown_bsdf, CROWN_ON)):
                socket_key(bsdf, "Emission Strength", fitted, 0.0)
                socket_key(bsdf, "Emission Strength", lit, value)
            show_from = fitted
        label = caption(cam, "{}\n{}".format(info["crowns"][key]["corps"].upper(),
                                             info["crowns"][key]["light"].upper()), color)
        hide(label, 1, True)
        hide(label, show_from, False)
        if i + 1 < len(keys):
            hide(label, 1 + (i + 1) * SEGMENT + 5, True)

    # Large, dim panels: the steel mirrors small hot lights into blown highlights.
    A.area_light("Key", (0.12, -0.12, 0.16), 0.35, 0.35)
    A.area_light("Fill", (-0.16, -0.06, 0.06), 0.05, 0.35, (0.85, 0.9, 1.0))
    A.area_light("Rim", (0.0, 0.18, 0.12), 0.5, 0.3)
    world()
    steel_floor(mesh_min_z() - 0.3 * A.MM)
    return end


def hero(info):
    keys = list(info["crowns"])
    spacing, tilt = 27 * A.MM, math.radians(72)
    holders = []
    for i, key in enumerate(keys):
        holder = bpy.data.objects.new("Ring_" + key, None)
        bpy.context.collection.objects.link(holder)
        parts = ring(info, [key], holder)
        color = A.CORPS_COLORS[key]
        parts["RingBase"][1].inputs["Base Color"].default_value = rgba(body_color(key))
        leds = parts["LEDs"][1]
        leds.inputs["Emission Color"].default_value = rgba(color)
        leds.inputs["Emission Strength"].default_value = LED_ON
        parts["Crown_" + key][1].inputs["Emission Strength"].default_value = 0.5
        # On its side: band flat-ish, crown facing the camera (-Y), tipped slightly up.
        holder.rotation_euler.x = tilt
        holder.location.x = (i - (len(keys) - 1) / 2) * spacing
        holders.append((holder, color))
    rest = mesh_min_z()
    for holder, color in holders:
        holder.location.z = -rest
        point_glow("Glow_" + holder.name, color,
                   (holder.location.x, -22 * A.MM, 10 * A.MM), 0.004)

    target = bpy.data.objects.new("Target", None)
    target.location = (0, 0, 10 * A.MM)
    bpy.context.collection.objects.link(target)
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens, cam_data.clip_start, cam_data.clip_end = 70, 0.02, 3
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = target
    cam_data.dof.aperture_fstop = 8
    cam = bpy.data.objects.new("Camera", cam_data)
    elevation, distance = math.radians(14), 470 * A.MM
    cam.location = (0, -distance * math.cos(elevation), distance * math.sin(elevation) + 10 * A.MM)
    cam.constraints.new("TRACK_TO").target = target
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    A.area_light("Key", (0.10, -0.30, 0.30), 0.8, 0.5)
    A.area_light("Fill", (-0.30, -0.20, 0.10), 0.2, 0.4, (0.85, 0.9, 1.0))
    # Large soft panel behind the rings gives the steel a bright reflection streak.
    A.area_light("Back", (0.0, 0.40, 0.20), 0.6, 0.8)
    world()
    steel_floor(0.0)


def configure(scene, preview, samples):
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.eevee.taa_render_samples = 8 if preview else samples
    try:
        scene.eevee.use_raytracing = True  # steel floor reflections
    except AttributeError:
        pass
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    scene.render.fps = A.FPS
    A.compositor_glow(scene)


def main():
    options = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    info = json.loads((A.MESHES / "scene.json").read_text(encoding="utf-8"))
    scene = bpy.context.scene
    if options.hero:
        hero(info)
        configure(scene, options.preview, 96)
        scene.render.resolution_x, scene.render.resolution_y = (
            (1200, 400) if options.preview else (2400, 800))
        scene.render.filepath = str(HERO)
        bpy.ops.wm.save_as_mainfile(filepath=str(BUILD / "lantern_corps_hero.blend"))
        bpy.ops.render.render(write_still=True)
        return
    end = swap(info)
    configure(scene, options.preview, 48)
    scene.render.resolution_x, scene.render.resolution_y = (
        (640, 360) if options.preview else (1280, 720))
    scene.frame_start, scene.frame_end = options.frames or (1, end)
    bpy.ops.wm.save_as_mainfile(filepath=str(BUILD / "lantern_corps_swap.blend"))
    if options.stills:
        for frame in options.stills:
            scene.frame_set(frame)
            scene.render.filepath = str(BUILD / "swap_stills" / "frame_{:03d}.png".format(frame))
            bpy.ops.render.render(write_still=True)
        return
    scene.render.filepath = str(BUILD / "swap_frames" / "frame_")
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
