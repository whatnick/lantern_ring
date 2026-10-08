"""Generate the Lantern Ring IR programming-clip PCBs.

Run with KiCad 10's bundled Python from the repository root:

    & 'C:\\Program Files\\KiCad\\10.0\\bin\\python.exe' hardware\\v2.0\\ring_ir_prog_clip\\generate.py

The ring_pcb_IR board is the only geometry source.  Pad positions, nets, the
front component envelope and the exposed front GND bar are read from it, so
the clip follows the target board instead of a hand-copied pattern.

Clip frame: (u, v) in mm, viewed from the probe side, looking at the target's
rear test pads.  u = -(x - TP3.x) mirrors KiCad X, v = y - TP3.y.
"""

import hashlib
import json
import math
import os
import re
import sys
import uuid

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_SHARE = os.environ.get("KICAD_SHARE", r"C:\Program Files\KiCad\10.0\share\kicad")
LIB_NAME = "ring_ir_prog_clip"
LIB_DIR = os.path.join(HERE, LIB_NAME + ".pretty")
ORIGIN = (150.0, 100.0)
NS = uuid.UUID("5d1d6f0e-6c4b-4e0a-9d6e-6c616e74726e")


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


def mm(v):
    return pcbnew.ToMM(v)


def pt(u, v):
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + u), pcbnew.FromMM(ORIGIN[1] + v))


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read().replace(b"\r\n", b"\n")).hexdigest()


def load_parameters():
    with open(os.path.join(HERE, "parameters.json"), encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------- target board

def read_target(params):
    path = os.path.normpath(os.path.join(HERE, params["dut"]["board"]))
    board = pcbnew.LoadBoard(path)
    pads = {}
    courtyards = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("TP"):
            pad = fp.Pads()[0]
            pos = pad.GetPosition()
            size = pad.GetSize()
            pads[ref] = {
                "x": mm(pos.x), "y": mm(pos.y), "net": pad.GetNetname(),
                "layer": board.GetLayerName(fp.GetLayer()),
                "size": [mm(size.x), mm(size.y)],
            }
        elif fp.GetLayer() == pcbnew.F_Cu:
            box = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
            courtyards.append((ref, mm(box.GetLeft()), mm(box.GetTop()),
                               mm(box.GetRight()), mm(box.GetBottom()), fp.GetFPIDAsString()))
    outline = None
    for drawing in board.GetDrawings():
        if drawing.GetLayer() == pcbnew.Edge_Cuts and drawing.GetShape() == pcbnew.SHAPE_T_POLY:
            outline = [(mm(p.x), mm(p.y)) for p in drawing.GetPolyPoints()]
    if outline is None:
        raise SystemExit("target outline polygon not found")
    gnd = params["dut"]["ground_test_point"]
    gx, gy = pads[gnd]["x"], pads[gnd]["y"]
    bar = None
    for zone in board.Zones():
        layers = [board.GetLayerName(l) for l in zone.GetLayerSet().Seq()]
        box = zone.GetBoundingBox()
        rect = (mm(box.GetLeft()), mm(box.GetTop()), mm(box.GetRight()), mm(box.GetBottom()))
        if (layers == ["F.Cu"] and zone.GetNetname() == "GND" and rect[0] <= gx <= rect[2]
                and rect[1] <= gy <= rect[3] and rect[2] - rect[0] < 12):
            bar = rect
    if bar is None:
        raise SystemExit("front GND bar under %s not found" % gnd)
    thickness = mm(board.GetDesignSettings().GetBoardThickness())
    return {"path": path, "pads": pads, "courtyards": courtyards,
            "outline": outline, "gnd_bar": bar, "thickness": thickness}


def to_uv(target, params, x, y):
    o = target["pads"][params["dut"]["origin_test_point"]]
    return (-(x - o["x"]), y - o["y"])


def check_target(target, params):
    errors = []
    for ref, net in params["dut"]["expected_nets"].items():
        pad = target["pads"].get(ref)
        if pad is None:
            errors.append("%s missing" % ref)
        elif pad["net"] != net:
            errors.append("%s net %s != %s" % (ref, pad["net"], net))
    for ref in params["dut"]["probe_test_points"]:
        if target["pads"][ref]["layer"] != "B.Cu":
            errors.append("%s is not on the rear" % ref)
    if target["pads"][params["dut"]["ground_test_point"]]["layer"] != "F.Cu":
        errors.append("ground test point is not on the front")
    if errors:
        raise SystemExit("target board changed: " + "; ".join(errors))


# ------------------------------------------------------------- local footprints

def write_footprints(params, gnd_pad):
    os.makedirs(LIB_DIR, exist_ok=True)
    pogo = params["pogo"]
    r = pogo["pad_diameter"] / 2
    pogo_fp = """(footprint "Pogo_P75_THT"
\t(version 20240108)
\t(generator "ring_ir_prog_clip")
\t(layer "F.Cu")
\t(descr "P75-class spring probe, {barrel} mm barrel in {drill} mm plated hole. Generated from parameters.json")
\t(tags "pogo spring probe test")
\t(attr through_hole)
\t(fp_text reference "REF**" (at 0 -{ref_y}) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))
\t(fp_text value "Pogo_P75_THT" (at 0 {ref_y}) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))
\t(fp_circle (center 0 0) (end {barrel_r} 0) (stroke (width 0.05) (type solid)) (fill none) (layer "F.Fab"))
\t(fp_circle (center 0 0) (end {cy} 0) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_circle (center 0 0) (end {cy} 0) (stroke (width 0.05) (type solid)) (fill none) (layer "B.CrtYd"))
\t(pad "1" thru_hole circle (at 0 0) (size {pad} {pad}) (drill {drill}) (layers "*.Cu" "*.Mask"))
)
""".format(barrel=pogo["barrel_diameter"], drill=pogo["drill"], pad=pogo["pad_diameter"],
           barrel_r=pogo["barrel_diameter"] / 2, cy=round(r + 0.1, 3), ref_y=round(r + 0.5, 3))
    w, h = gnd_pad["w"], gnd_pad["h"]
    anvil_fp = """(footprint "GND_Anvil_Pad"
\t(version 20240108)
\t(generator "ring_ir_prog_clip")
\t(layer "F.Cu")
\t(descr "Exposed flat GND contact under the ring_pcb_IR front GND bar. Generated from the target board")
\t(tags "anvil contact ground")
\t(attr smd)
\t(fp_text reference "REF**" (at 0 -{ty}) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))
\t(fp_text value "GND_Anvil_Pad" (at 0 {ty}) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))
\t(fp_rect (start -{cx} -{cy}) (end {cx} {cy}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at 0 0) (size {w} {h}) (layers "F.Cu" "F.Mask"))
)
""".format(w=round(w, 3), h=round(h, 3), cx=round(w / 2 + 0.1, 3), cy=round(h / 2 + 0.1, 3),
           ty=round(h / 2 + 0.5, 3))
    slot = params["clip_kit"]["mount_slot"]
    sl, sw = slot["u_outer"] - slot["u_inner"] + slot["width"], slot["width"]
    slot_fp = """(footprint "M2_Slot_Clip_Jaw"
\t(version 20240108)
\t(generator "ring_ir_prog_clip")
\t(layer "F.Cu")
\t(descr "Unplated M2 slot; length absorbs the unmeasured clip-jaw hole spacing. Generated from parameters.json")
\t(tags "mounting slot M2")
\t(attr exclude_from_pos_files exclude_from_bom)
\t(fp_text reference "REF**" (at 0 -2) (layer "F.Fab") hide (effects (font (size 0.5 0.5) (thickness 0.08))))
\t(fp_text value "M2_Slot_Clip_Jaw" (at 0 2) (layer "F.Fab") hide (effects (font (size 0.5 0.5) (thickness 0.08))))
\t(fp_rect (start -{cx} -{cy}) (end {cx} {cy}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "" np_thru_hole oval (at 0 0) (size {sl} {sw}) (drill oval {sl} {sw}) (layers "*.Cu" "*.Mask"))
)
""".format(sl=round(sl, 3), sw=sw, cx=round(sl / 2 + 0.25, 3), cy=round(sw / 2 + 0.25, 3))
    for name, text in (("Pogo_P75_THT", pogo_fp), ("GND_Anvil_Pad", anvil_fp), ("M2_Slot_Clip_Jaw", slot_fp)):
        with open(os.path.join(LIB_DIR, name + ".kicad_mod"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)


def load_fp(lib, name):
    if lib == LIB_NAME:
        path = LIB_DIR
    else:
        path = os.path.join(KICAD_SHARE, "footprints", lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit("footprint %s:%s not found" % (lib, name))
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


# -------------------------------------------------------------------- geometry

def offset_convex(poly, d):
    """Miter-offset a convex polygon outward by d."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sign = 1 if area > 0 else -1
    lines = []
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        nx, ny = sign * dy / length, -sign * dx / length
        lines.append(((x1 + nx * d, y1 + ny * d), (dx, dy)))
    out = []
    for i in range(n):
        (p, r), (q, s) = lines[i - 1], lines[i]
        cross = r[0] * s[1] - r[1] * s[0]
        t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / cross
        out.append((p[0] + t * r[0], p[1] + t * r[1]))
    return out


def point_in_convex(poly, x, y):
    n = len(poly)
    signs = set()
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        c = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        if abs(c) > 1e-9:
            signs.add(c > 0)
    return len(signs) <= 1


def add_line(board, layer, a, b, width=0.1):
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetStart(pt(*a))
    shape.SetEnd(pt(*b))
    shape.SetLayer(layer)
    shape.SetWidth(pcbnew.FromMM(width))
    board.Add(shape)


def add_arc(board, layer, start, mid, end, width=0.1):
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_ARC)
    shape.SetArcGeometry(pt(*start), pt(*mid), pt(*end))
    shape.SetLayer(layer)
    shape.SetWidth(pcbnew.FromMM(width))
    board.Add(shape)


def add_polygon(board, layer, points, width=0.1):
    for i, a in enumerate(points):
        add_line(board, layer, a, points[(i + 1) % len(points)], width)


def add_rounded_rect(board, layer, u0, v0, u1, v1, r, width=0.1):
    k = r * (1 - math.sqrt(0.5))
    add_line(board, layer, (u0 + r, v0), (u1 - r, v0), width)
    add_line(board, layer, (u1, v0 + r), (u1, v1 - r), width)
    add_line(board, layer, (u1 - r, v1), (u0 + r, v1), width)
    add_line(board, layer, (u0, v1 - r), (u0, v0 + r), width)
    add_arc(board, layer, (u1 - r, v0), (u1 - k, v0 + k), (u1, v0 + r), width)
    add_arc(board, layer, (u1, v1 - r), (u1 - k, v1 - k), (u1 - r, v1), width)
    add_arc(board, layer, (u0 + r, v1), (u0 + k, v1 - k), (u0, v1 - r), width)
    add_arc(board, layer, (u0, v0 + r), (u0 + k, v0 + k), (u0 + r, v0), width)


def add_text(board, layer, text, u, v, size=0.8, thickness=0.12, mirror=False):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(pt(u, v))
    item.SetLayer(layer)
    item.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    item.SetTextThickness(pcbnew.FromMM(thickness))
    item.SetMirrored(mirror)
    board.Add(item)


def add_track(board, net, layer, path, width):
    for a, b in zip(path, path[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(pt(*a))
        track.SetEnd(pt(*b))
        track.SetWidth(pcbnew.FromMM(width))
        track.SetLayer(layer)
        track.SetNet(net)
        board.Add(track)


# ------------------------------------------------------------------ schematics

def extract_block(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("unbalanced")


def library_symbol(lib, name):
    path = os.path.join(KICAD_SHARE, "symbols", lib + ".kicad_sym")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    start = text.find('(symbol "%s"' % name)
    block = extract_block(text, start)
    pins = {}
    for match in re.finditer(r"\(pin \w+ \w+", block):
        pin = extract_block(block, match.start())
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pin)
        number = re.search(r'\(number "([^"]+)"', pin).group(1)
        pins[number] = (float(at.group(1)), float(at.group(2)))
    return block.replace('(symbol "%s"' % name, '(symbol "%s:%s"' % (lib, name), 1), pins


def write_schematic(path, project, title, parts):
    """parts: list of dict(lib, name, ref, value, footprint, at, nets{pin: net})."""
    sheet = uid(project, "sheet")
    libs, out = {}, []
    for part in parts:
        key = (part["lib"], part["name"])
        if key not in libs:
            libs[key] = library_symbol(*key)
    for part in parts:
        block, pins = libs[(part["lib"], part["name"])]
        x, y = (round(c / 2.54) * 2.54 for c in part["at"])
        sym = uid(project, part["ref"])
        part["uuid"] = sym
        props = [("Reference", part["ref"], -3.0), ("Value", part["value"], 3.0),
                 ("Footprint", part["footprint"], 5.0), ("Datasheet", "", 5.0)]
        text = ['\t(symbol (lib_id "%s:%s") (at %.2f %.2f 0) (unit 1)' % (part["lib"], part["name"], x, y),
                '\t\t(in_bom %s) (on_board yes) (dnp no)' % ("yes" if part.get("in_bom", True) else "no"),
                '\t\t(uuid "%s")' % sym]
        for i, (key, value, dy) in enumerate(props):
            hide = " hide" if key in ("Footprint", "Datasheet") else ""
            text.append('\t\t(property "%s" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27))%s))'
                        % (key, value, x + 2.54, y + dy, hide))
        for number in sorted(pins):
            text.append('\t\t(pin "%s" (uuid "%s"))' % (number, uid(project, part["ref"], number)))
        text.append('\t\t(instances (project "%s" (path "/%s" (reference "%s") (unit 1))))'
                    % (project, sheet, part["ref"]))
        text.append("\t)")
        out.append("\n".join(text))
        for number, net in part["nets"].items():
            px, py = pins[number]
            lx, ly = x + px, y - py
            if net is None:
                out.append('\t(no_connect (at %.2f %.2f) (uuid "%s"))' % (lx, ly, uid(project, part["ref"], number, "nc")))
                continue
            out.append('\t(label "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "%s"))'
                       % (net, lx, ly, uid(project, part["ref"], number, "label")))
    body = "\n".join(out)
    lib_text = "\n".join(block for block, _ in libs.values())
    content = """(kicad_sch (version 20231120) (generator "ring_ir_prog_clip") (generator_version "8.0")
\t(uuid "{sheet}")
\t(paper "A4")
\t(title_block (title "{title}") (rev "1") (comment 1 "Generated by generate.py; edit parameters.json, not this file"))
\t(lib_symbols
{libs}
\t)
{body}
\t(sheet_instances (path "/" (page "1")))
)
""".format(sheet=sheet, title=title, libs=lib_text, body=body)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def write_project(path, name):
    template = os.path.normpath(os.path.join(HERE, "..", "ring_pcb_IR", "ring_pcb_IR.kicad_pro"))
    with open(template, encoding="utf-8") as handle:
        project = json.load(handle)
    project["meta"]["filename"] = name + ".kicad_pro"
    project.pop("sheets", None)
    project.pop("boards", None)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(project, handle, indent=2)
        handle.write("\n")
    table = os.path.join(os.path.dirname(path), "fp-lib-table")
    with open(table, "w", encoding="utf-8", newline="\n") as handle:
        handle.write('(fp_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/../%s.pretty")(options "")(descr "Programming clip footprints"))\n)\n'
                     % (LIB_NAME, LIB_NAME))


def new_board(name):
    # NewBoard() creates a project in the working directory; a bare BOARD does not.
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    settings = board.GetDesignSettings()
    settings.SetBoardThickness(pcbnew.FromMM(1.6))
    return board


def place(board, part, fp, u, v, angle=0.0, sheetfile=None):
    fp.SetReference(part["ref"])
    fp.SetValue(part["value"])
    fp.SetPosition(pt(u, v))
    fp.SetOrientationDegrees(angle)
    if sheetfile:
        fp.SetPath(pcbnew.KIID_PATH("/" + part["uuid"]))
        fp.SetSheetfile(sheetfile)
        fp.SetSheetname("")
    board.Add(fp)
    return fp


def assign_nets(board, fp, nets, netmap):
    for pad in fp.Pads():
        name = nets.get(pad.GetNumber())
        if name is None:
            name = "unconnected-(%s-Pad%s)" % (fp.GetReference(), pad.GetNumber())
            if name not in netmap:
                netmap.update(make_nets(board, [name]))
        if name:
            pad.SetNet(netmap[name])


def make_nets(board, names):
    """Local schematic labels produce sheet-qualified net names."""
    netmap = {}
    for name in names:
        net = pcbnew.NETINFO_ITEM(board, name if name.startswith("unconnected-") else "/" + name)
        board.Add(net)
        netmap[name] = net
    return netmap


def pad_uv(pad):
    pos = pad.GetPosition()
    return (round(mm(pos.x) - ORIGIN[0], 4), round(mm(pos.y) - ORIGIN[1], 4))


# --------------------------------------------------------------- probe board

def probe_layout(params):
    """Clip-derived probe dimensions shared by the KiCad build and the FreeCAD fit check."""
    pb, isp, kit = params["probe_board"], params["isp_header"], params["clip_kit"]
    g = kit["geometry"]
    tip = kit["upper_tip_v"]
    # Header in front of the pogo grid: odd row (a) nearest the pins, even row (b) outboard.
    a = -isp["row_a_offset"]
    b = a - 2.54
    slot = kit["mount_slot"]
    hole_v = tip + g["hole_setback_from_upper_tip"]
    centre = (slot["u_inner"] + slot["u_outer"]) / 2
    return {
        "a": a, "b": b, "upper_tip_v": tip, "lower_tip_v": tip - g["upper_tip_setback"],
        "u_min": pb["u_min"], "u_max": pb["u_max"], "v_min": pb["v_min"],
        "v_max": round(tip + g["upper_tip_section_end"] - g["upper_tip_setback"] - pb["step_margin"], 4),
        "slots": [(-centre, hole_v), (centre, hole_v)],
        "slot_size": (slot["u_outer"] - slot["u_inner"] + slot["width"], slot["width"]),
    }


def build_probe(target, params, pogo_uv):
    name = "ring_ir_prog_probe"
    folder = os.path.join(HERE, "probe")
    os.makedirs(folder, exist_ok=True)
    pb, isp, kit = params["probe_board"], params["isp_header"], params["clip_kit"]
    lay = probe_layout(params)
    a, b = lay["a"], lay["b"]
    nets = {ref: target["pads"][ref]["net"] for ref in params["dut"]["probe_test_points"]}
    parts = []
    isp_nets = set(isp["pins"].values())
    for i, ref in enumerate(sorted(nets, key=lambda r: int(r[2:]))):
        # PB3/PB4 are probed for test access only; their pogo tops are the breakout.
        net = nets[ref] if nets[ref] in isp_nets else None
        parts.append({"lib": "Connector", "name": "TestPoint", "ref": "P" + ref[2:],
                      "value": "Pogo %s %s" % (ref, nets[ref]),
                      "footprint": "%s:Pogo_P75_THT" % LIB_NAME, "at": (40 + 20 * (i % 4), 50 + 25 * (i // 4)),
                      "nets": {"1": net}, "target": ref})
    header = {"lib": "Connector_Generic", "name": "Conn_02x03_Odd_Even", "ref": "J1",
              "value": "AVR_ISP_6", "footprint": "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical",
              "at": (60, 110), "nets": dict(isp["pins"])}
    lead = {"lib": "Connector", "name": "TestPoint", "ref": "J2", "value": "GND_lead_to_anvil",
            "footprint": "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm", "at": (110, 110), "nets": {"1": "GND"},
            "in_bom": False}
    parts += [header, lead]
    sch = os.path.join(folder, name + ".kicad_sch")
    write_schematic(sch, name, "Lantern Ring IR programming clip - probe head", parts)
    write_project(os.path.join(folder, name + ".kicad_pro"), name)

    board = new_board(name)
    netmap = make_nets(board, sorted(isp_nets))
    u_min, v_min, u_max, v_max = lay["u_min"], lay["v_min"], lay["u_max"], lay["v_max"]
    add_rounded_rect(board, pcbnew.Edge_Cuts, u_min, v_min, u_max, v_max, pb["corner_radius"])
    for part in parts[:-2]:
        fp = place(board, part, load_fp(LIB_NAME, "Pogo_P75_THT"), *pogo_uv[part["target"]],
                   sheetfile=name + ".kicad_sch")
        assign_nets(board, fp, part["nets"], netmap)
    # Header sits in front of the pogo grid so the jaw tip can sit just behind it.
    # Odd row (MISO, SCK, RESET) faces the pogo grid; even row (VCC, MOSI, GND) is outboard.
    want = {"1": (-2.54, a), "2": (-2.54, b), "3": (0.0, a)}
    for angle in (0, 90, 180, 270):
        fp = load_fp("Connector_PinHeader_2.54mm", "PinHeader_2x03_P2.54mm_Vertical")
        fp.SetOrientationDegrees(angle)
        fp.SetPosition(pt(-2.54, a))
        got = {p.GetNumber(): pad_uv(p) for p in fp.Pads()}
        if all(abs(got[k][0] - w[0]) < 1e-3 and abs(got[k][1] - w[1]) < 1e-3 for k, w in want.items()):
            break
    else:
        raise SystemExit("could not orient ISP header")
    fp = place(board, header, fp, -2.54, a, angle, sheetfile=name + ".kicad_sch")
    assign_nets(board, fp, header["nets"], netmap)
    fp = place(board, lead, load_fp("TestPoint", "TestPoint_THTPad_D1.5mm_Drill0.7mm"),
               *pb["gnd_lead_pad"], sheetfile=name + ".kicad_sch")
    assign_nets(board, fp, lead["nets"], netmap)
    for i, (u, v) in enumerate(lay["slots"]):
        hole = load_fp(LIB_NAME, "M2_Slot_Clip_Jaw")
        hole.SetBoardOnly(True)
        hole.SetReference("H%d" % (i + 1))
        hole.Reference().SetVisible(False)
        hole.SetPosition(pt(u, v))
        board.Add(hole)

    # Routes are relative to the measured pogo grid; generate() checks the grid first.
    p = {nets[ref]: pogo_uv[ref] for ref in nets}
    s = (p["PB4"][0] - p["PB2"][0]) / 2
    w = pb["track_width"]
    top, bot = pcbnew.F_Cu, pcbnew.B_Cu
    mi, ms, rs, sk, vc = p["PB1"], p["PB0"], p["PB5"], p["PB2"], p["VCC"]
    o = pb["outer_route_u"]
    add_track(board, netmap["PB1"], top, [mi, (-o, mi[1] - (o - abs(mi[0]))), (-o, a + 1.0),
                                          (-o + 1.0, a), (-2.54, a)], w)
    add_track(board, netmap["PB5"], top, [rs, (o, rs[1] - (o - abs(rs[0]))), (o, a + 1.0),
                                          (o - 1.0, a), (2.54, a)], w)
    add_track(board, netmap["PB2"], bot, [sk, (s, -s), (s, a + 1.27), (0.0, a)], w)
    # MOSI and VCC pass header pin 1 in the channel at u = -1.27, on opposite layers.
    add_track(board, netmap["PB0"], bot, [ms, (-s, -s), (-s, vc[1] - 1.05), (-1.27, vc[1] - 1.05 - (s - 1.27)),
                                          (-1.27, b + 1.27), (0.0, b)], w)
    add_track(board, netmap["VCC"], top, [vc, (-1.27, vc[1] - (1.27 + vc[0])), (-1.27, b + 1.27), (-2.54, b)], w)
    add_track(board, netmap["GND"], bot, [(2.54, b), tuple(pb["gnd_lead_pad"])], w)

    fsilk, bsilk, ffab = pcbnew.F_SilkS, pcbnew.B_SilkS, pcbnew.F_Fab
    add_text(board, fsilk, "1", -4.6, a, 0.8, 0.12)
    add_text(board, fsilk, "ISP", 0.0, b - 1.9, 0.8, 0.12)
    add_text(board, fsilk, "PB4", p["PB4"][0] + 2.1, p["PB4"][1] - 1.5, 0.8, 0.12)
    add_text(board, fsilk, "PB3", p["PB3"][0], p["PB3"][1] + 1.75, 0.8, 0.12)
    add_text(board, fsilk, "GND", pb["gnd_lead_pad"][0], pb["gnd_lead_pad"][1] + 1.5, 0.8, 0.12)
    add_text(board, fsilk, "RING IR ISP", 0.0, lay["upper_tip_v"] + 1.5, 0.8, 0.12)
    add_text(board, bsilk, "PINS DOWN", 0.0, lay["upper_tip_v"] + 1.5, 0.8, 0.12, mirror=True)
    # Fab marks: nominal upper-jaw tip and the hinge side of the jaw sandwich.
    tip = lay["upper_tip_v"]
    add_line(board, ffab, (u_min + 0.3, tip), (u_max - 0.3, tip), 0.1)
    add_text(board, ffab, "UPPER JAW TIP (EST)", 0.0, tip + 0.6, 0.5, 0.08)
    if not kit["measured"]:
        add_text(board, ffab, "KIT JAW UNMEASURED", 0.0, v_min + 1.0, 0.5, 0.08)
    # Rear fab layer marks where the target outline falls under the pins.
    outline = [to_uv(target, params, x, y) for x, y in target["outline"]]
    edge = [(u, v) for u, v in outline]
    for i, q in enumerate(edge):
        r = edge[(i + 1) % len(edge)]
        if all(u_min + 0.6 <= c[0] <= u_max - 0.6 and v_min + 0.6 <= c[1] <= v_max - 0.6
               for c in (q, r)):
            add_line(board, pcbnew.B_Fab, q, r, 0.1)
    path = os.path.join(folder, name + ".kicad_pcb")
    board.Save(path)
    return path, sch


# --------------------------------------------------------------- anvil + fence

def anvil_geometry(target, params):
    an = params["anvil"]
    outline = [to_uv(target, params, x, y) for x, y in target["outline"]]
    us = [q[0] for q in outline]
    vs = [q[1] for q in outline]
    m = an["outline_margin"]
    # The hinge side is trimmed so the clip-jaw M2 nuts clear the anvil and fence.
    frame = (min(us) - m, min(vs) - m, max(us) + m, max(vs) + an["hinge_margin"])
    cys = [to_uv(target, params, c[1], c[2]) + to_uv(target, params, c[3], c[4]) for c in target["courtyards"]]
    wm = an["window_margin"]
    window = (min(min(c[0], c[2]) for c in cys) - wm, min(min(c[1], c[3]) for c in cys) - wm,
              max(max(c[0], c[2]) for c in cys) + wm, max(max(c[1], c[3]) for c in cys) + wm)
    x0, y0, x1, y1 = target["gnd_bar"]
    gnd = params["dut"]["ground_test_point"]
    cx = (x0 + x1) / 2
    half = an["gnd_pad_half_width"]
    inset = an["gnd_pad_inset"]
    top = y0 + inset
    # Lowest board edge over the pad width, measured on the target outline.
    xs = [cx - half + i * (2 * half) / 20 for i in range(21)]
    ext = offset_convex(target["outline"], -inset)
    bottom = min(max(y for y in [top + k * 0.001 for k in range(4000)] if point_in_convex(ext, x, y))
                 for x in xs)
    pad_uv_c = to_uv(target, params, cx, (top + bottom) / 2)
    pad = {"w": 2 * half, "h": bottom - top, "uv": pad_uv_c, "x_range": (cx - half, cx + half),
           "y_range": (top, bottom), "target": gnd}
    pocket = offset_convex(outline, an["pocket_clearance"])
    rails = {"left_u": window[0] - min(us), "right_u": max(us) - window[2],
             "top_v": window[1] - min(vs), "bar_gap_v": pad_uv_c[1] - pad["h"] / 2 - window[3]}
    return {"outline": outline, "frame": frame, "window": window, "pad": pad,
            "pocket": pocket, "rails": rails}


def build_anvil(target, params, geo):
    name = "ring_ir_prog_anvil"
    folder = os.path.join(HERE, "anvil")
    os.makedirs(folder, exist_ok=True)
    an = params["anvil"]
    u0, v0, u1, v1 = geo["frame"]
    tail = v1 + an["tail_length"]
    lead_uv = (0.0, v1 + an["tail_length"] / 2)
    parts = [
        {"lib": "Connector", "name": "TestPoint", "ref": "P8", "value": "GND anvil (TP8 bar)",
         "footprint": "%s:GND_Anvil_Pad" % LIB_NAME, "at": (50, 50), "nets": {"1": "GND"}},
        {"lib": "Connector", "name": "TestPoint", "ref": "J1", "value": "GND_lead_to_probe",
         "footprint": "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm", "at": (80, 50), "nets": {"1": "GND"},
         "in_bom": False},
    ]
    sch = os.path.join(folder, name + ".kicad_sch")
    write_schematic(sch, name, "Lantern Ring IR programming clip - GND anvil", parts)
    write_project(os.path.join(folder, name + ".kicad_pro"), name)
    board = new_board(name)
    netmap = make_nets(board, ["GND"])
    t = an["tail_half_width"]
    add_polygon(board, pcbnew.Edge_Cuts, [(u0, v0), (u1, v0), (u1, v1), (t, v1), (t, tail),
                                          (-t, tail), (-t, v1), (u0, v1)], 0.1)
    w0, wv0, w1, wv1 = geo["window"]
    add_rounded_rect(board, pcbnew.Edge_Cuts, w0, wv0, w1, wv1, an["window_corner_radius"])
    pad = geo["pad"]
    fp = place(board, parts[0], load_fp(LIB_NAME, "GND_Anvil_Pad"), *pad["uv"], sheetfile=name + ".kicad_sch")
    assign_nets(board, fp, parts[0]["nets"], netmap)
    fp = place(board, parts[1], load_fp("TestPoint", "TestPoint_THTPad_D1.5mm_Drill0.7mm"), *lead_uv,
               sheetfile=name + ".kicad_sch")
    assign_nets(board, fp, parts[1]["nets"], netmap)
    add_track(board, netmap["GND"], pcbnew.F_Cu, [pad["uv"], lead_uv], an["gnd_track_width"])
    add_polygon(board, pcbnew.F_Fab, geo["outline"], 0.1)
    add_text(board, pcbnew.F_SilkS, "GND", 0.0, lead_uv[1] + 1.8, 0.8, 0.12)
    add_text(board, pcbnew.F_SilkS, "RING LEDS DOWN", 0.0, v0 + 1.1, 0.8, 0.12)
    add_text(board, pcbnew.B_SilkS, "IR ANVIL - TAPE TO RISER", 0.0, v0 + 1.1, 0.8, 0.12, mirror=True)
    path = os.path.join(folder, name + ".kicad_pcb")
    board.Save(path)
    return path, sch


def build_fence(params, geo):
    name = "ring_ir_prog_fence"
    folder = os.path.join(HERE, "fence")
    os.makedirs(folder, exist_ok=True)
    an = params["anvil"]
    write_project(os.path.join(folder, name + ".kicad_pro"), name)
    board = new_board(name)
    u0, v0, u1, v1 = geo["frame"]
    add_rounded_rect(board, pcbnew.Edge_Cuts, u0, v0, u1, v1, an["corner_radius"])
    add_polygon(board, pcbnew.Edge_Cuts, geo["pocket"], 0.1)
    add_text(board, pcbnew.F_SilkS, "LEDS DOWN, TP1-6 HINGE", 0.0, v0 + 1.1, 0.8, 0.12)
    path = os.path.join(folder, name + ".kicad_pcb")
    board.Save(path)
    return path


# ---------------------------------------------------------------------- main

def check_pogo_grid(pogo_uv, nets):
    by_net = {nets[r]: uvp for r, uvp in pogo_uv.items()}
    s = by_net["PB4"][0] - by_net["PB2"][0]
    expect = {"PB0": (-s, 0), "PB2": (0, 0), "PB4": (s, 0), "PB1": (-s, s), "PB3": (0, s), "PB5": (s, s)}
    for net, (u, v) in expect.items():
        got = by_net[net]
        if abs(got[0] - u) > 0.01 or abs(got[1] - v) > 0.01:
            raise SystemExit("pogo grid changed at %s: %s" % (net, got))
    if not (2.9 < s < 3.2):
        raise SystemExit("pogo pitch %.3f outside routed range" % s)
    vcc = by_net["VCC"]
    if abs(vcc[0]) > 0.3 or not (-5.0 < vcc[1] < -4.0):
        raise SystemExit("VCC pogo moved: %s" % (vcc,))
    return s


def fit_inputs(target, params, pogo_uv, geo):
    """Plain (u, v) geometry for the FreeCAD fit check, which cannot import pcbnew."""
    lay = probe_layout(params)
    r = lambda pts: [[round(c, 4) for c in q] for q in pts]
    an = params["anvil"]
    u0, v0, u1, v1 = geo["frame"]
    t = an["tail_half_width"]
    tail = v1 + an["tail_length"]
    comps = []
    for ref, x0, y0, x1, y1, fpid in target["courtyards"]:
        a, b = to_uv(target, params, x0, y0), to_uv(target, params, x1, y1)
        comps.append({"ref": ref, "footprint": fpid,
                      "uv": [round(min(a[0], b[0]), 4), round(min(a[1], b[1]), 4),
                             round(max(a[0], b[0]), 4), round(max(a[1], b[1]), 4)]})
    pads = {ref: {"uv": list(to_uv(target, params, q["x"], q["y"])), "size": q["size"],
                  "layer": q["layer"], "net": q["net"]} for ref, q in target["pads"].items()}
    holes = [{"uv": list(pogo_uv[ref]), "d": params["pogo"]["drill"], "kind": "pogo", "ref": ref}
             for ref in sorted(pogo_uv)]
    for i, col in enumerate((-2.54, 0.0, 2.54)):
        for row in (lay["a"], lay["b"]):
            holes.append({"uv": [col, row], "d": 1.0, "kind": "header"})
    holes.append({"uv": list(params["probe_board"]["gnd_lead_pad"]), "d": 0.7, "kind": "lead"})
    return {
        "probe": dict(lay, corner_radius=params["probe_board"]["corner_radius"], holes=holes,
                      header_origin=[0.0, (lay["a"] + lay["b"]) / 2]),
        "anvil": {"outline": r([(u0, v0), (u1, v0), (u1, v1), (t, v1), (t, tail), (-t, tail), (-t, v1), (u0, v1)]),
                  "window": [round(c, 4) for c in geo["window"]],
                  "pad_uv": [round(c, 4) for c in geo["pad"]["uv"]],
                  "pad_size": [round(geo["pad"]["w"], 4), round(geo["pad"]["h"], 4)],
                  "lead_uv": [0.0, v1 + an["tail_length"] / 2]},
        "fence": {"frame": [round(c, 4) for c in geo["frame"]], "pocket": r(geo["pocket"])},
        "ring": {"outline": r(geo["outline"]), "thickness": target["thickness"],
                 "components": comps, "pads": pads},
    }


def main():
    params = load_parameters()
    target = read_target(params)
    check_target(target, params)
    pogo_uv = {}
    nets = {}
    for ref in params["dut"]["probe_test_points"]:
        pad = target["pads"][ref]
        pogo_uv[ref] = tuple(round(c, 4) for c in to_uv(target, params, pad["x"], pad["y"]))
        nets[ref] = pad["net"]
    pitch = check_pogo_grid(pogo_uv, nets)
    geo = anvil_geometry(target, params)
    an = params["anvil"]
    if min(geo["rails"].values()) < an["min_rail_contact"]:
        raise SystemExit("anvil support too narrow: %s" % geo["rails"])
    write_footprints(params, geo["pad"])
    probe_pcb, probe_sch = build_probe(target, params, pogo_uv)
    anvil_pcb, anvil_sch = build_anvil(target, params, geo)
    fence_pcb = build_fence(params, geo)
    os.makedirs(os.path.join(HERE, "generated"), exist_ok=True)
    rel = lambda p: os.path.relpath(p, HERE).replace("\\", "/")
    summary = {
        "target_board": rel(target["path"]),
        "target_sha256": sha256(target["path"]),
        "parameters_sha256": sha256(os.path.join(HERE, "parameters.json")),
        "target_thickness_mm": target["thickness"],
        "pogo_pitch_mm": round(pitch, 4),
        "pogo_uv": {ref: {"uv": list(pogo_uv[ref]), "net": nets[ref],
                          "function": params["isp_header"]["functions"].get(nets[ref], nets[ref])}
                    for ref in sorted(pogo_uv)},
        "isp_pins": params["isp_header"]["pins"],
        "anvil": {
            "window_uv": [round(c, 3) for c in geo["window"]],
            "support_contact_mm": {k: round(v, 3) for k, v in geo["rails"].items()},
            "gnd_pad_mm": [round(geo["pad"]["w"], 3), round(geo["pad"]["h"], 3)],
            "gnd_pad_target_xy": [[round(c, 3) for c in geo["pad"]["x_range"]],
                                  [round(c, 3) for c in geo["pad"]["y_range"]]],
            "pocket_clearance_mm": an["pocket_clearance"],
        },
        "fit_inputs": fit_inputs(target, params, pogo_uv, geo),
        "unmeasured": [k for k, v in (("clip_kit", params["clip_kit"]["measured"]),
                                      ("pogo", params["pogo"]["measured"])) if not v],
        "outputs": [rel(p) for p in (probe_pcb, probe_sch, anvil_pcb, anvil_sch, fence_pcb)],
    }
    with open(os.path.join(HERE, "generated", "geometry.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    print(json.dumps(summary["anvil"], indent=1))
    print("pitch", summary["pogo_pitch_mm"], "unmeasured", summary["unmeasured"])


if __name__ == "__main__":
    sys.exit(main())
