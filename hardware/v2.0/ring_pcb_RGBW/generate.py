"""Rebuild the RGBW schematic, locked IR interface and unrouted placement."""

import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET

import pcbnew

HERE = Path(__file__).resolve().parent
SHARE = Path(os.environ.get("KICAD_SHARE", r"C:\Program Files\KiCad\10.0\share\kicad"))
CLI = SHARE.parent.parent / "bin" / "kicad-cli.exe"
NAME = "ring_pcb_RGBW"
LIB = "ring_rgbw"
GEN = HERE / "generated"
FPDIR = HERE / (LIB + ".pretty")
NS = uuid.UUID("88dbfd7e-35f1-455f-9f14-6c6d8e51a6ba")
spec = importlib.util.spec_from_file_location(
    "_clip_helpers", HERE.parent / "ring_ir_prog_clip" / "generate.py")
clip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clip)


def uid(*values):
    return str(uuid.uuid5(NS, "/".join(str(v) for v in values)))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def point(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def quote(value):
    return json.dumps(str(value), ensure_ascii=True)


def block(text, pattern):
    match = re.search(pattern, text)
    if not match:
        raise ValueError("Missing symbol/block: " + pattern)
    return clip.extract_block(text, match.start())


def properties(text):
    return {re.match(r'\(property "([^"]+)"', item).group(1): item
            for item in (clip.extract_block(text, m.start())
                         for m in re.finditer(r'\(property "', text))}


def symbol(lib, name):
    text = (SHARE / "symbols" / (lib + ".kicad_sym")).read_text(encoding="utf-8")
    child = block(text, r'\(symbol "' + re.escape(name) + r'"')
    parent = re.search(r'\(extends "([^"]+)"\)', child)
    if parent:
        base = block(text, r'\(symbol "' + re.escape(parent.group(1)) + r'"')
        if '(extends "' in base:
            raise ValueError("Resolve the additional library inheritance explicitly")
        for key, value in properties(child).items():
            old = properties(base).get(key)
            if old:
                base = base.replace(old, value, 1)
        base = base.replace('"' + parent.group(1), '"' + name)
        child = base
    return child


def pins(text):
    result = {}
    for m in re.finditer(r"\(pin (?:input|output|bidirectional|tri_state|passive|power_in|power_out|no_connect|open_collector|open_emitter|unspecified) ", text):
        pin = clip.extract_block(text, m.start())
        at = re.search(r"\(at ([\d.-]+) ([\d.-]+) ([\d.-]+)\)", pin)
        number = re.search(r'\(number "([^"]+)"', pin).group(1)
        result[number] = (float(at[1]), float(at[2]), float(at[3]))
    return result


def led_symbol():
    out = ['(symbol "CLQ6A_RGBW" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)',
           '(property "Reference" "D" (at 0 12.7 0) (effects (font (size 1.27 1.27))))',
           '(property "Value" "CLQ6A_RGBW" (at 0 -12.7 0) (effects (font (size 1.27 1.27))))',
           '(symbol "CLQ6A_RGBW_0_1"']
    for colour, y in zip("RGBW", (7.62, 2.54, -2.54, -7.62)):
        out += ['(polyline (pts (xy -2.54 %s) (xy 0 %s) (xy -2.54 %s) (xy -2.54 %s)) (stroke (width 0.254) (type default)) (fill (type none)))'
                % (y + 1.27, y, y - 1.27, y + 1.27),
                '(polyline (pts (xy 0 %s) (xy 0 %s)) (stroke (width 0.254) (type default)) (fill (type none)))' % (y - 1.27, y + 1.27),
                '(polyline (pts (xy -7.62 %s) (xy -2.54 %s)) (stroke (width 0) (type default)) (fill (type none)))' % (y, y),
                '(polyline (pts (xy 0 %s) (xy 7.62 %s)) (stroke (width 0) (type default)) (fill (type none)))' % (y, y),
                '(text "%s" (at 2.54 %s 0) (effects (font (size 1.27 1.27))))' % (colour, y + 1.27)]
    out += [') (symbol "CLQ6A_RGBW_1_1"']
    for a, k, colour, y in zip("1234", "8765", "RGBW", (7.62, 2.54, -2.54, -7.62)):
        for number, name, x, angle in ((a, "A_" + colour, -10.16, 0), (k, "K_" + colour, 10.16, 180)):
            out.append('(pin passive line (at %s %s %d) (length 2.54) (name "%s" (effects (font (size 1.0 1.0)))) (number "%s" (effects (font (size 1.0 1.0)))))'
                       % (x, y, angle, name, number))
    return "\n".join(out + ["))"])


def write_led_footprint(params):
    out = ['(footprint "CLQ6A_PLCC8" (version 20240108) (generator "pcbnew") (layer "F.Cu")',
           '(descr "Cree CLD-CT1387 Rev14 pp11-12; vector land pattern calibrated to 5.30 x 4.40 mm")',
           '(attr smd)',
           '(fp_text reference "REF**" (at 0 -3.2) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.15))))',
           '(fp_text value "CLQ6A_RGBW" (at 0 3.2) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.15))))',
           '(fp_rect (start -2.9 -2.75) (end 2.9 2.75) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
           '(fp_rect (start -2.6 -2.5) (end 2.6 2.5) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
           '(fp_circle (center -3.1 -1.7) (end -2.95 -1.7) (stroke (width 0.1) (type solid)) (fill none) (layer "F.SilkS"))']
    for number, poly in params["led_lands_mm"].items():
        anchor = (-2.2 if int(number) < 5 else 2.2,
                  {1: -1.75, 2: -0.5, 3: 0.5, 4: 1.75, 5: 1.75, 6: 0.5, 7: -0.5, 8: -1.75}[int(number)])
        pts = " ".join("(xy %.4f %.4f)" % (x - anchor[0], y - anchor[1]) for x, y in poly)
        out.append('(pad "%s" smd custom (at %s %s) (size 0.3 0.3) (layers "F.Cu" "F.Paste" "F.Mask") (options (clearance outline) (anchor rect)) (primitives (gr_poly (pts %s) (width 0) (fill yes))))'
                   % (number, anchor[0], anchor[1], pts))
    out += ['(model "${KIPRJMOD}/models/step/CLQ6A_RGBW.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))', ')']
    (FPDIR / "CLQ6A_PLCC8.kicad_mod").write_text("\n".join(out) + "\n", encoding="utf-8")


def sourcing(manufacturer, mpn, description, datasheet=""):
    from urllib.parse import quote as urlquote
    return {"Manufacturer": manufacturer, "MPN": mpn, "Description": description,
            "Datasheet": datasheet,
            "DigiKey": "https://www.digikey.com/en/products?keywords=" + urlquote(mpn),
            "Mouser": "https://www.mouser.com/c/?q=" + urlquote(mpn)}


def parts(params):
    items = []

    def add(ref, lib, name, value, footprint, nets, at, fields=None, bom=True):
        items.append(dict(ref=ref, lib=lib, name=name, value=value,
                          footprint=footprint, nets=nets, at=at, fields=fields or {}, bom=bom))

    mcu = {str(n): None for n in range(1, 22)}
    mcu.update({"1": "PB5", "2": "PB3", "5": "PB4", "8": "GND",
                "11": "PB0", "12": "PB1", "14": "PB2", "15": "VCC", "21": "GND"})
    add("U1", LIB, "ATtiny85-20M", "ATtiny85-20MU", "QFN20", mcu, (60.96, 58.42),
        sourcing("Microchip", "ATTINY85-20MU", "ATtiny85 8KB, QFN20 exposed pad, 2.7-5.5 V",
                 "https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-2586-AVR-8-bit-Microcontroller-ATtiny25-ATtiny45-ATtiny85_Datasheet.pdf"))
    led_nets = {}
    for ch in params["channels"]:
        led_nets.update({ch["anode"]: "VCC", ch["cathode"]: ch["colour"] + "_K"})
    add("D1", LIB, "CLQ6A_RGBW", "CLQ6A RGBW", "CLQ6A_PLCC8", led_nets, (149.86, 60.96),
        sourcing("Cree LED", params["led_mpn"], "Four independent dies, anodes joined on PCB; 5.2x5.0x1.1 mm", params["led_datasheet"]))
    resistor_mpns = {2200: "RC0402FR-072K2L", 1000: "RC0402FR-071KL",
                     100000: "RC0402FR-07100KL", 10000: "RC0402FR-0710KL"}

    def resistor(ref, value, a, b, at, description):
        add(ref, "Device", "R", {2200: "2.2k", 1000: "1k", 100000: "100k", 10000: "10k"}[value],
            "R0402", {"1": a, "2": b}, at,
            sourcing("YAGEO", resistor_mpns[value], description + "; 0402 1% 63mW"))

    for i, ch in enumerate(params["channels"]):
        c, x = ch["colour"], 50.8 + i * 91.44
        resistor("R" + str(i + 1), params["led_resistance_ohms"], c + "_K", c + "_D",
                 (x + 25.4, 132.08), c + " die current limiter")
        add("Q" + str(i + 1), "Transistor_FET", "DMG1012T", "DMG1012T", "SOT523",
            {"1": c + "_G", "2": "GND", "3": c + "_D"}, (x + 22.86, 157.48),
            sourcing("Diodes Incorporated", params["mosfet_mpn"], c + " low-side MOSFET; Rds max 0.7 ohm at Vgs=1.8 V", params["mosfet_datasheet"]))
        resistor("R" + str(i + 5), params["gate_resistance_ohms"], ch["gpio"], c + "_G",
                 (x, 154.94), c + " gate/ISP isolation")
        resistor("R" + str(i + 9), params["gate_pulldown_ohms"], c + "_G", "GND",
                 (x, 180.34), c + " gate pull-down")
    resistor("R13", params["selector_pullup_ohms"], "VCC", "PB3", (236.22, 43.18), "Mode selector pull-up")
    resistor("R14", params["reset_pullup_ohms"], "VCC", "PB5", (104.14, 43.18), "ISP RESET pull-up")
    add("JP1", "Jumper", "SolderJumper_2_Open", "MODE: open/closed", "ModeBridge",
        {"1": "PB3", "2": "GND"}, (236.22, 68.58), bom=False)
    add("C1", "Device", "C", "100n", "C0402", {"1": "VCC", "2": "GND"}, (104.14, 78.74),
        sourcing("Murata", "GRM155R71A104KA01D", "100nF X7R 10V 0402 local decoupling"))
    add("C2", "Device", "C", "10u", "C0805", {"1": "VCC", "2": "GND"}, (124.46, 78.74),
        sourcing("Samsung Electro-Mechanics", "CL21A106KPFNNNE", "10uF X5R 10V 0805 bulk; verify DC bias"))
    tp_nets = ["PB0", "PB1", "PB2", "PB3", "PB4", "PB5", "GND", "GND", "VCC"]
    for n, net in enumerate(tp_nets, 1):
        add("TP" + str(n), "Connector", "TestPoint", net, "IR_TP" + str(n),
            {"1": net}, (302.26 + ((n - 1) % 3) * 30.48, 38.1 + ((n - 1) // 3) * 20.32), bom=False)
    for n, net in enumerate(("VCC", "GND"), 1):
        add("#FLG0%d" % n, "power", "PWR_FLAG", "PWR_FLAG", None, {"1": net}, (185.42 + n * 20.32, 99.06), bom=False)
    return items


def schematic(items, params):
    custom = [symbol("MCU_Microchip_ATtiny", "ATtiny85-20M"), led_symbol()]
    local_text = '(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n' + "\n".join(custom) + "\n)\n"
    (HERE / (LIB + ".kicad_sym")).write_text(local_text, encoding="utf-8")
    (HERE / "sym-lib-table").write_text('(sym_lib_table (version 7) (lib (name "ring_rgbw")(type "KiCad")(uri "${KIPRJMOD}/ring_rgbw.kicad_sym")(options "")(descr "RGBW local symbols")))\n', encoding="utf-8")
    libraries = {}
    for part in items:
        key = (part["lib"], part["name"])
        if key not in libraries:
            raw = custom[0 if part["name"] == "ATtiny85-20M" else 1] if part["lib"] == LIB else symbol(*key)
            libraries[key] = raw
    root = uid("sheet")
    out = ['(kicad_sch (version 20231120) (generator "eeschema") (uuid "%s") (paper "A3")' % root,
           '(title_block (title "Lantern Ring RGBW - four-channel PWM") (rev "%s") (company "whatnick") (comment 1 "Experimental; IR outline / TP1-TP9; battery removed for ISP"))' % params["revision"],
           '(lib_symbols']
    for (lib, name), raw in libraries.items():
        out.append(raw.replace('(symbol "' + name + '"', '(symbol "' + lib + ":" + name + '"', 1))
    out.append(')')
    for part in items:
        x, y = part["at"]
        sid = uid(part["ref"])
        part["uuid"] = sid
        pp = pins(libraries[(part["lib"], part["name"])])
        if set(pp) != set(part["nets"]):
            raise ValueError("Incomplete pin map for " + part["ref"] + ": " + str(pp))
        out.append('(symbol (lib_id "%s:%s") (at %.2f %.2f 0) (unit 1) (in_bom %s) (on_board %s) (dnp no) (uuid "%s")'
                   % (part["lib"], part["name"], x, y, "yes" if part["bom"] else "no", "yes" if part["footprint"] else "no", sid))
        props = {"Reference": part["ref"], "Value": part["value"],
                 "Footprint": LIB + ":" + part["footprint"] if part["footprint"] else ""}
        props.update(part["fields"])
        for key, value in props.items():
            visible = key in ("Reference", "Value") and not part["ref"].startswith("#")
            dy = -15.24 if part["ref"] in ("U1", "D1") else -6.35
            px, py = x, y + dy + (2.54 if key == "Value" else 0)
            if part["ref"] == "U1":
                px, py = x - 10.16, y - 19.05 + (2.54 if key == "Value" else 0)
            elif part["ref"].startswith("Q"):
                px, py = x + 12.7, y - 2.54 + (2.54 if key == "Value" else 0)
            out.append('(property %s %s (at %.2f %.2f 0) (effects (font (size 1.0 1.0))%s))'
                       % (quote(key), quote(value), px, py, "" if visible else " hide"))
        for number in pp:
            out.append('(pin "%s" (uuid "%s"))' % (number, uid(part["ref"], number)))
        out.append('(instances (project "%s" (path "/%s" (reference "%s") (unit 1)))))' % (NAME, root, part["ref"]))
        for number, (px, py, angle) in pp.items():
            a, b = round(x + px, 4), round(y - py, 4)
            net = part["nets"][number]
            if net is None:
                out.append('(no_connect (at %s %s) (uuid "%s"))' % (a, b, uid(part["ref"], number, "nc")))
                continue
            dx, dy = {0: (-6.35, 0), 180: (6.35, 0), 90: (0, 6.35), 270: (0, -6.35)}[int(angle)]
            lx, ly = round(a + dx, 4), round(b + dy, 4)
            out.append('(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid "%s"))' % (a, b, lx, ly, uid(part["ref"], number, "wire")))
            out.append('(global_label "%s" (shape bidirectional) (at %s %s 0) (effects (font (size 1.0 1.0)) (justify left)) (uuid "%s"))' % (net, lx, ly, uid(part["ref"], number, "label")))
    for text, x, y in (
            ("MCU / ISP: preserve RESET; 8 MHz internal oscillator", 27.94, 20.32),
            ("One RGBW package: independent dice, common anodes on PCB", 119.38, 20.32),
            ("PB3: OPEN = high / CLOSED = low; latch before PWM", 200.66, 20.32),
            ("LOCKED IR CONTACTS: no header needed on ring", 299.72, 20.32),
            ("R / PB0 / OC0A", 30.48, 119.38), ("G / PB1 / OC0B", 121.92, 119.38),
            ("B / PB4 / OC1B", 213.36, 119.38), ("W / PB2 / SOFTWARE PWM", 304.8, 119.38),
            ("2.2k per die: conservative low current, NOT constant brightness. No boost: blue/white may dim on CR2032.", 25.4, 213.36),
            ("Programming: remove battery; single 5V supply, max 5.5V. ISP may light LEDs; current resistors remain in circuit.", 25.4, 223.52),
            ("Firmware must preserve RESET/SPI fuses. Physical current, colour, temperature, cell life and clip fit are unqualified.", 25.4, 233.68)):
        out.append('(text %s (at %s %s 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "%s"))' % (quote(text), x, y, uid("text", text)))
    out.append('(sheet_instances (path "/" (page "1"))))')
    (HERE / (NAME + ".kicad_sch")).write_text("\n".join(out) + "\n", encoding="utf-8")


def vendor_footprint(source, name):
    lib, fpname = source.split(":")
    fp = pcbnew.FootprintLoad(str(SHARE / "footprints" / (lib + ".pretty")), fpname)
    if fp is None:
        raise ValueError("Missing footprint " + source)
    if name == "ModeBridge":
        fp.Models().clear()
    for index in range(len(fp.Models())):
        model = fp.Models()[index]
        generated = {"QFN20": "ATtiny85_QFN20.step", "SOT523": "DMG1012T_SOT523.step"}
        if name in generated:
            src = HERE / "models" / "step" / generated[name]
            if not src.is_file():
                raise FileNotFoundError("Run create_led_model.py first: " + str(src))
            model.m_Filename = "${KIPRJMOD}/models/step/" + src.name
            continue
        root = str(SHARE / "3dmodels")
        filename = model.m_Filename
        filename = re.sub(r"\$\{KICAD\d+_3DMODEL_DIR\}", lambda _: root, filename)
        src = Path(filename).with_suffix(".step")
        if not src.is_file():
            raise FileNotFoundError(src)
        dest = HERE / "models" / "step" / src.name
        shutil.copyfile(src, dest)
        model.m_Filename = "${KIPRJMOD}/models/step/" + src.name
    fp.SetFPID(pcbnew.LIB_ID(LIB, name))
    pcbnew.FootprintSave(str(FPDIR), fp)


def project(params):
    data = json.loads((HERE.parent / "ring_pcb_IR" / "ring_pcb_IR.kicad_pro").read_text())
    data["meta"]["filename"] = NAME + ".kicad_pro"
    data.pop("boards", None)
    data.pop("sheets", None)
    data["text_variables"] = {}
    rules = data["board"]["design_settings"]["rules"]
    rules.update(min_clearance=0.15, min_track_width=0.15, min_via_diameter=0.45,
                 min_through_hole_diameter=0.2, min_via_annular_width=0.1,
                 min_hole_clearance=0.2, min_hole_to_hole=0.2,
                 min_copper_edge_clearance=0.25, min_text_height=0.6,
                 min_text_thickness=0.1, min_silk_clearance=0.1,
                 solder_mask_clearance=0.0, solder_mask_min_width=0.05)
    data["board"]["design_settings"]["drc_exclusions"] = []
    data["erc"]["erc_exclusions"] = []
    base = data["net_settings"]["classes"][0]
    base.update(clearance=0.15, track_width=0.15, via_diameter=0.45, via_drill=0.2)
    data["net_settings"]["classes"] = [base, dict(base, name="Power", priority=0, track_width=0.25)]
    data["net_settings"]["netclass_patterns"] = [
        {"netclass": "Power", "pattern": name} for name in ("VCC", "GND")]
    (HERE / (NAME + ".kicad_pro")).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (HERE / "fp-lib-table").write_text('(fp_lib_table (version 7) (lib (name "ring_rgbw")(type "KiCad")(uri "${KIPRJMOD}/ring_rgbw.pretty")(options "")(descr "Vendored RGBW footprints")))\n', encoding="utf-8")


def keepout(board, name, bounds, layer):
    x0, y0, x1, y1 = bounds
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetZoneName(name)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowZoneFills(False)
    zone.SetDoNotAllowFootprints(False)
    zone.Outline().NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        zone.Outline().Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(zone)


def add_planes(board):
    outline = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    if len(outline) != 1:
        raise ValueError("Expected the native single Edge.Cuts polygon")
    vertices = outline[0].GetPolyShape().COutline(0)
    for layer, name in ((pcbnew.F_Cu, "GND"), (pcbnew.In1_Cu, "GND"),
                        (pcbnew.In2_Cu, "VCC"), (pcbnew.B_Cu, "VCC")):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(board.FindNet(name))
        zone.SetZoneName(name + " board plane")
        zone.SetLocalClearance(pcbnew.FromMM(0.15))
        zone.SetMinThickness(pcbnew.FromMM(0.15))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetThermalReliefGap(pcbnew.FromMM(0.2))
        zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.2))
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        zone.Outline().NewOutline()
        for i in range(vertices.PointCount()):
            zone.Outline().Append(vertices.CPoint(i).x, vertices.CPoint(i).y)
        board.Add(zone)


def power_fanout(board, params):
    """Short, checked supply stubs to dedicated internal planes."""
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()
            if p.GetNumber() and any(p.IsOnLayer(l) for l in (pcbnew.F_Cu, pcbnew.B_Cu))]
    bodies = []
    for fp in board.GetFootprints():
        shapes = [g.GetBoundingBox() for g in fp.GraphicalItems()
                  if g.GetLayer() == pcbnew.F_Fab and isinstance(g, pcbnew.PCB_SHAPE)]
        if shapes:
            bodies.append((min(s.GetX() for s in shapes), min(s.GetY() for s in shapes),
                           max(s.GetRight() for s in shapes), max(s.GetBottom() for s in shapes)))
    outline = next(d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts).GetPolyShape()
    clearance, radius = pcbnew.FromMM(0.15), pcbnew.FromMM(0.225)

    def clear(via, track, own):
        pos = via.GetPosition()
        if not outline.Collide(pos) or outline.CollideEdge(pos, None, radius + pcbnew.FromMM(0.25)):
            return False
        if any(x0 - radius < pos.x < x1 + radius and y0 - radius < pos.y < y1 + radius
               for x0, y0, x1, y1 in bodies):
            return False
        if own.GetEffectiveShape(pcbnew.F_Cu).Collide(pos, pcbnew.FromMM(0.15)):
            return False
        for zone in board.Zones():
            if not zone.GetIsRuleArea():
                continue
            layers = list(zone.GetLayerSet().Seq())
            if any(l in (pcbnew.F_Cu, pcbnew.B_Cu) for l in layers):
                if zone.GetDoNotAllowVias() and zone.Outline().Collide(via.GetEffectiveShape(), 0):
                    return False
                if pcbnew.F_Cu in layers and zone.GetDoNotAllowTracks() and zone.Outline().Collide(track.GetEffectiveShape(), 0):
                    return False
        for pad in pads:
            if pad.GetNetname() == via.GetNetname():
                continue
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if pad.IsOnLayer(layer):
                    shape = pad.GetEffectiveShape(layer)
                    if shape.Collide(via.GetEffectiveShape(), clearance):
                        return False
                    if layer == pcbnew.F_Cu and shape.Collide(track.GetEffectiveShape(), clearance):
                        return False
        for item in board.GetTracks():
            if isinstance(item, pcbnew.PCB_VIA):
                distance = math.hypot(pos.x - item.GetPosition().x, pos.y - item.GetPosition().y)
                if distance < pcbnew.FromMM(0.4):
                    return False
            if item.GetNetname() != via.GetNetname():
                if item.GetEffectiveShape().Collide(via.GetEffectiveShape(), clearance):
                    return False
                if item.IsOnLayer(pcbnew.F_Cu) and item.GetEffectiveShape().Collide(track.GetEffectiveShape(), clearance):
                    return False
        return True

    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        if fp.GetReference().startswith("TP"):
            continue
        for pad in fp.Pads():
            if pad.GetNetname() not in ("GND", "VCC") or not pad.GetNumber():
                continue
            if (fp.GetReference(), pad.GetNumber()) in (("U1", "21"), ("U1", "15"), ("C1", "1"), ("C2", "1")):
                continue
            pos, centre = pad.GetPosition(), fp.GetPosition()
            angle = math.atan2(pos.y - centre.y, pos.x - centre.x)
            for distance, delta in [(d, a) for d in (0.7, 0.8, 0.9, 1.0, 0.6, 1.2, 1.4)
                                    for a in (0, 30, -30, 60, -60, 90, -90)]:
                a = angle + math.radians(delta)
                end = point(pcbnew.ToMM(pos.x) + distance * math.cos(a),
                            pcbnew.ToMM(pos.y) + distance * math.sin(a))
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(end)
                via.SetViaType(pcbnew.VIATYPE_THROUGH)
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                via.SetWidth(pcbnew.FromMM(0.45))
                via.SetDrill(pcbnew.FromMM(0.2))
                via.SetNet(pad.GetNet())
                track = pcbnew.PCB_TRACK(board)
                track.SetStart(pos)
                track.SetEnd(end)
                track.SetWidth(pcbnew.FromMM(0.25))
                track.SetLayer(pcbnew.F_Cu)
                track.SetNet(pad.GetNet())
                if clear(via, track, pad):
                    board.Add(via)
                    board.Add(track)
                    break
            else:
                raise ValueError("No clear power fanout for %s.%s" % (fp.GetReference(), pad.GetNumber()))


def arrange_references(board):
    """Keep readable references outside bodies, exposed copper and each other."""
    def rect(item, margin=0.0):
        box = item.GetBoundingBox()
        return (pcbnew.ToMM(box.GetX()) - margin, pcbnew.ToMM(box.GetY()) - margin,
                pcbnew.ToMM(box.GetRight()) + margin, pcbnew.ToMM(box.GetBottom()) + margin)

    def overlaps(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    shape = next(d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts)
    chain = shape.GetPolyShape().COutline(0)
    vertices = [(pcbnew.ToMM(chain.CPoint(i).x), pcbnew.ToMM(chain.CPoint(i).y))
                for i in range(chain.PointCount())]

    def inside(x, y):
        products = [(bx - ax) * (y - ay) - (by - ay) * (x - ax)
                    for (ax, ay), (bx, by) in zip(vertices, vertices[1:] + vertices[:1])]
        return all(v >= 0 for v in products) or all(v <= 0 for v in products)

    blocked = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
    for zone in board.Zones():
        layers = list(zone.GetLayerSet().Seq())
        for mask, silk in ((pcbnew.F_Mask, pcbnew.F_SilkS), (pcbnew.B_Mask, pcbnew.B_SilkS)):
            if mask in layers:
                blocked[silk].append(rect(zone, 0.06))
    for item in board.GetDrawings():
        if item.GetLayer() in blocked:
            blocked[item.GetLayer()].append(rect(item, 0.06))
    for fp in board.GetFootprints():
        silk = pcbnew.B_SilkS if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_SilkS
        fabrication = pcbnew.B_Fab if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_Fab
        body = []
        for item in fp.GraphicalItems():
            if item.GetLayer() == fabrication and isinstance(item, pcbnew.PCB_SHAPE):
                body.append(rect(item))
            elif item.GetLayer() == silk:
                blocked[silk].append(rect(item, 0.06))
        if body:
            blocked[silk].append((min(r[0] for r in body), min(r[1] for r in body),
                                  max(r[2] for r in body), max(r[3] for r in body)))
        for pad in fp.Pads():
            blocked[silk].append(rect(pad, 0.06))
    offsets = [(x / 5.0, y / 5.0, angle) for x in range(-35, 36)
               for y in range(-35, 36) for angle in (0, 90)]
    offsets.sort(key=lambda p: (p[0] ** 2 + p[1] ** 2, abs(p[0]), p[1], p[0]))
    remaining = {}
    footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for ref, fp in footprints.items():
        text = fp.Reference()
        silk = text.GetLayer()
        x, y = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
        candidates = []
        for dx, dy, angle in offsets:
            text.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
            text.SetPosition(point(x + dx, y + dy))
            bounds = rect(text, 0.06)
            if not all(inside(a, b) for a, b in (
                    (bounds[0], bounds[1]), (bounds[2], bounds[1]),
                    (bounds[2], bounds[3]), (bounds[0], bounds[3]))):
                continue
            if not any(overlaps(bounds, other) for other in blocked[silk]):
                candidates.append((x + dx, y + dy, angle, bounds))
        remaining[ref] = candidates
    while remaining:
        ref = min(remaining, key=lambda key: (len(remaining[key]), key))
        if not remaining[ref]:
            raise ValueError("No unobstructed reference position for " + ref)
        x, y, angle, bounds = remaining.pop(ref)[0]
        text = footprints[ref].Reference()
        text.SetPosition(point(x, y))
        text.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
        for key in remaining:
            if footprints[key].Reference().GetLayer() == text.GetLayer():
                remaining[key] = [c for c in remaining[key] if not overlaps(c[3], bounds)]


def board(items, params):
    source = pcbnew.LoadBoard(str(HERE / params["source_board"]))
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(params["routing"]["copper_layers"])
    b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
    settings = b.GetDesignSettings()
    settings.SetBoardThickness(source.GetDesignSettings().GetBoardThickness())
    settings.m_CopperEdgeClearance = pcbnew.FromMM(0.25)
    settings.m_MinClearance = pcbnew.FromMM(0.15)
    settings.m_TrackMinWidth = pcbnew.FromMM(0.15)
    settings.m_ViasMinSize = pcbnew.FromMM(0.45)
    settings.m_HoleClearance = pcbnew.FromMM(0.2)
    default = settings.m_NetSettings.GetDefaultNetclass()
    default.SetClearance(pcbnew.FromMM(0.15))
    default.SetTrackWidth(pcbnew.FromMM(0.15))
    default.SetViaDiameter(pcbnew.FromMM(0.45))
    default.SetViaDrill(pcbnew.FromMM(0.2))
    source_fp = {f.GetReference(): f for f in source.GetFootprints()}
    for d in source.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            b.Add(d.Duplicate())
    native_nets = ET.parse(GEN / "netlist.xml").getroot()
    netmap, padnets = {}, {}
    for net in native_nets.findall("nets/net"):
        name = net.attrib["name"]
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
        netmap[name] = ni
        for node in net.findall("node"):
            padnets[(node.attrib["ref"], node.attrib["pin"])] = name
    for part in items:
        if not part["footprint"]:
            continue
        ref = part["ref"]
        if ref.startswith("TP"):
            fp = pcbnew.FOOTPRINT(source_fp[ref])
            if ref in ("TP7", "TP8", "TP9"):
                for item in list(fp.GraphicalItems()):
                    if item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                        fp.Remove(item)
            libfp = pcbnew.FOOTPRINT(fp)
            if libfp.GetLayer() == pcbnew.B_Cu:
                libfp.Flip(libfp.GetPosition(), False)
            libfp.SetOrientationDegrees(0)
            libfp.SetPosition(point(0, 0))
            libfp.SetReference("REF**")
            libfp.SetValue(part["footprint"])
            libfp.SetFPID(pcbnew.LIB_ID(LIB, part["footprint"]))
            for pad in libfp.Pads():
                pad.SetNetCode(0)
            pcbnew.FootprintSave(str(FPDIR), libfp)
        else:
            fp = pcbnew.FootprintLoad(str(FPDIR), part["footprint"])
            x, y, angle = params["placement_mm"][ref]
            fp.SetPosition(point(x, y))
            fp.SetOrientationDegrees(angle)
        fp.SetFPID(pcbnew.LIB_ID(LIB, part["footprint"]))
        fp.SetReference(ref)
        fp.SetValue(part["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + part["uuid"]))
        fp.SetSheetfile(NAME + ".kicad_sch")
        fp.SetSheetname("")
        fp.SetExcludedFromBOM(not part["bom"])
        fp.SetLibDescription(part["fields"].get("Description", ""))
        fp.GetField(pcbnew.FIELD_T_DESCRIPTION).SetText(part["fields"].get("Description", ""))
        for name, value in part["fields"].items():
            if name in ("Description", "Datasheet"):
                field = fp.GetField(pcbnew.FIELD_T_DESCRIPTION if name == "Description" else pcbnew.FIELD_T_DATASHEET)
            else:
                field = pcbnew.PCB_FIELD(fp, pcbnew.FIELD_T_USER, name)
                fp.Add(field)
            field.SetText(value)
            field.SetVisible(False)
        fp.Reference().SetVisible(True)
        fp.Reference().SetTextSize(point(0.6, 0.6))
        fp.Reference().SetTextThickness(pcbnew.FromMM(0.12))
        fp.Reference().SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
        fp.Reference().SetLayer(pcbnew.B_SilkS if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_SilkS)
        if fp.GetLayer() == pcbnew.B_Cu:
            fp.Reference().SetPosition(point(pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y) + 1.15))
        fp.Value().SetVisible(False)
        fp.Value().SetLayer(pcbnew.F_Fab)
        for pad in fp.Pads():
            if not pad.GetNumber() and not any(
                    layer in (pcbnew.F_Cu, pcbnew.B_Cu) for layer in pad.GetLayerSet().Seq()):
                pad.SetNetCode(0)
                continue
            key = (ref, pad.GetNumber())
            if key not in padnets:
                raise ValueError("Netlist is missing physical pad " + str(key))
            pad.SetNet(netmap[padnets[key]])
        b.Add(fp)
    for original in source.Zones():
        layers = list(original.GetLayerSet().Seq())
        if pcbnew.F_Mask in layers or pcbnew.B_Mask in layers or (
                layers == [pcbnew.F_Cu] and original.GetNumCorners() == 4):
            z = original.Duplicate()
            if z.GetNetname():
                z.SetNet(netmap[z.GetNetname()])
            if layers == [pcbnew.F_Cu]:
                z.SetAssignedPriority(1)
            z.UnFill()
            b.Add(z)
    keepout(b, "Front upper exposed GND", (132.05, 101.54, 141.02, 104.02), pcbnew.F_Cu)
    keepout(b, "Front lower exposed GND", (132.05, 118.22, 141.04, 120.71), pcbnew.F_Cu)
    keepout(b, "TP9 VCC pour bridge", (138.50, 110.90, 138.76, 111.70), pcbnew.B_Cu)
    keepout(b, "Upper GND pour bridge", (132.45, 104.00, 133.25, 104.25), pcbnew.F_Cu)
    keepout(b, "Lower GND pour bridge", (136.0, 117.95, 136.8, 118.25), pcbnew.F_Cu)
    for route in params["critical_routes_mm"]:
        for start, end in zip(route["points"], route["points"][1:]):
            track = pcbnew.PCB_TRACK(b)
            track.SetStart(point(*start))
            track.SetEnd(point(*end))
            track.SetWidth(pcbnew.FromMM(route["width"]))
            track.SetLayer(b.GetLayerID(route["layer"]))
            track.SetNet(netmap[route["net"]])
            b.Add(track)
    for via in params["critical_vias_mm"]:
        item = pcbnew.PCB_VIA(b)
        item.SetPosition(point(*via["at"]))
        item.SetViaType(pcbnew.VIATYPE_THROUGH)
        item.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        item.SetWidth(pcbnew.FromMM(params["routing"]["via_mm"]))
        item.SetDrill(pcbnew.FromMM(params["routing"]["drill_mm"]))
        item.SetNet(netmap[via["net"]])
        b.Add(item)
    power_fanout(b, params)
    for text, x, y in (("RGBW 0.1 EXP", 136.5, 105.0), ("whatnick", 136.5, 106.4), ("TAPR OHL", 136.5, 107.8)):
        t = pcbnew.PCB_TEXT(b)
        t.SetText(text)
        t.SetPosition(point(x, y))
        t.SetLayer(pcbnew.B_SilkS)
        t.SetMirrored(True)
        t.SetTextSize(point(0.8, 0.8))
        t.SetTextThickness(pcbnew.FromMM(0.12))
        b.Add(t)
    arrange_references(b)
    add_planes(b)
    pcbnew.SaveBoard(str(HERE / (NAME + ".kicad_pcb")), b, True)
    project(params)
    subprocess.run([str(CLI), "pcb", "drc", "--refill-zones", "--save-board",
                    "--severity-all", "--schematic-parity", "--format", "json",
                    "-o", str(GEN / "placement-drc.json"),
                    str(HERE / (NAME + ".kicad_pcb"))], check=True)
    b = pcbnew.LoadBoard(str(HERE / (NAME + ".kicad_pcb")))
    for zone in list(b.Zones()):
        if zone.GetLayer() == pcbnew.F_Cu and zone.GetZoneName() == "GND board plane":
            b.Remove(zone)
    # Keep outer islands out of the router's ideal-plane connectivity model.
    if not pcbnew.ExportSpecctraDSN(b, str(GEN / (NAME + ".dsn"))):
        raise RuntimeError("DSN export failed")
    return b


def main():
    params = json.loads((HERE / "parameters.json").read_text())
    for directory in (GEN, FPDIR, HERE / "models" / "step"):
        directory.mkdir(parents=True, exist_ok=True)
    write_led_footprint(params)
    for src, name in (
            ("Package_DFN_QFN:QFN-20-1EP_4x4mm_P0.5mm_EP2.6x2.6mm", "QFN20"),
            ("Package_TO_SOT_SMD:SOT-523", "SOT523"),
            ("Resistor_SMD:R_0402_1005Metric", "R0402"),
            ("Capacitor_SMD:C_0402_1005Metric", "C0402"),
            ("Capacitor_SMD:C_0805_2012Metric", "C0805"),
            ("Resistor_SMD:R_0402_1005Metric", "ModeBridge")):
        vendor_footprint(src, name)
    items = parts(params)
    schematic(items, params)
    project(params)
    subprocess.run([str(CLI), "sch", "export", "netlist", "--format", "kicadxml",
                    "-o", str(GEN / "netlist.xml"), str(HERE / (NAME + ".kicad_sch"))], check=True)
    b = board(items, params)
    with (GEN / "bom.csv").open("w", newline="", encoding="utf-8") as handle:
        columns = ["Reference", "Value", "Footprint", "Manufacturer", "MPN", "Description", "DigiKey", "Mouser", "Datasheet"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for p in items:
            if p["bom"]:
                writer.writerow(dict(Reference=p["ref"], Value=p["value"], Footprint=LIB + ":" + p["footprint"], **p["fields"]))
    manifest = {"status": "unrouted", "source_board_sha256": digest(HERE / params["source_board"]),
                "placement_board_sha256": digest(HERE / (NAME + ".kicad_pcb")),
                "parameters_sha256": digest(HERE / "parameters.json"),
                "generator_sha256": digest(HERE / "generate.py"),
                "channels": params["channels"],
                "led_land_pattern": "Cree CLD-CT1387 Rev14 p12; PDF vector outline calibrated to 5.30 x 4.40 mm, rounded to 0.001 mm; manufacturer tolerance +/-0.1 mm",
                "unqualified": ["physical clip fit", "colour/brightness at sub-mA drive", "battery life/current/temperature", "firmware PWM"]}
    (GEN / "design.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Generated %d physical footprints; source IR board unchanged." % len(list(b.GetFootprints())))


if __name__ == "__main__":
    main()
