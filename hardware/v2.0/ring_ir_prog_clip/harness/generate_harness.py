"""Build an editable Fritzing harness and its colour-coded wiring reference.

The clip/target parts are interface diagrams, not PCB designs or manufacturing CAD.
Run Fritzing -svg on this directory afterwards to export the native sketch views.
"""

import argparse
import html
import json
import pathlib
from xml.dom import minidom
import xml.etree.ElementTree as ET
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
CLIP = HERE.parent
UNO_MODULE = "arduino_Uno_Rev3(fix)"
SIGNALS = [
    ("MISO", "grey", "#707070", "D12", "connector55", "1", "P2", "TP2", "PB1"),
    ("VCC", "white", "#ffffff", "3V3 VCC", None, "2", "P9", "TP9", "VCC"),
    ("SCK", "blue", "#1768c4", "D13", "connector56", "3", "P3", "TP3", "PB2"),
    ("MOSI", "purple", "#7b3fb3", "D11", "connector54", "4", "P1", "TP1", "PB0"),
    ("RESET", "brown", "#8c564b", "D10", "connector53", "5", "P6", "TP6", "PB5"),
    ("GND", "black", "#202020", "GND", "connector89", "6", "J2", "TP8", "GND"),
]
WARNINGS = [
    "REMOVE CR2032. Wire and check continuity with all power OFF.",
    "White lead = user-reported 3V3 VCC. Uno supply pins are NOT automatically wired in this drawing.",
    "STOP: a 3.3V target cannot take direct 5V Uno ISP signals. Disconnect USB and target power.",
    "Use verified SPI level translation or a voltage-compatible ISP host before reconnecting (not shown).",
    "Uno 3V3 power does NOT change its I/O levels. Do not join supply outputs.",
    "Colours match the user's reported COM6 harness; continuity and programming are not yet verified.",
]


def element(parent, tag, text=None, **attrs):
    child = ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})
    child.text = text
    return child


def xml_write(path, root):
    path.write_bytes(minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ", encoding="utf-8"))


def svg_text(x, y, text, size=12, color="#17334c", anchor="start"):
    return ('<text x="%s" y="%s" font-family="Droid Sans,Arial,sans-serif" '
            'font-size="%s" fill="%s" text-anchor="%s">%s</text>'
            % (x, y, size, color, anchor, html.escape(text)))


def svg_line(points, color, width=2):
    coordinates = " ".join("%s,%s" % p for p in points)
    outline = ""
    if color == "#ffffff":
        outline = '<polyline points="%s" fill="none" stroke="#607080" stroke-width="%s"/>' % (
            coordinates, width + 2)
    return outline + '<polyline points="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
        coordinates, color, width)


def signal_ink(color):
    return "#455466" if color == "#ffffff" else color


def part(name, title, size, body, pins, buses=()):
    """Write all editable part assets; PCB view is deliberately non-fabrication."""
    assets = HERE / "parts"
    assets.mkdir(exist_ok=True)
    root = ET.Element("module", moduleId="lantern-ring-" + name, fritzingVersion="1.0.8")
    for tag, text in (("version", "1"), ("title", title), ("label", title),
                      ("author", "Lantern Ring contributors"), ("date", "2026-11-10"),
                      ("description", "ISP harness interface only; not a PCB layout or approved voltage converter. "
                       "Artwork: Lantern Ring contributors, CC BY-SA 3.0. Created with Fritzing.")):
        element(root, tag, text)
    props = element(root, "properties")
    element(props, "property", "Lantern Ring ISP harness", name="family")
    views = element(root, "views")
    view_layers = {"breadboardView": ("breadboard", "breadboard"),
                   "schematicView": ("schematic", "schematic"),
                   "iconView": ("icon", "icon"),
                   "pcbView": ("pcb", "silkscreen")}
    for view, (folder, layer) in view_layers.items():
        layers = element(element(views, view), "layers", image=folder + "/" + name + ".svg")
        element(layers, "layer", layerId=layer)
        if view == "pcbView":
            content = svg_text(10, 25, "HARNESS ONLY - NOT A PCB", 11)
        else:
            content = body
            for cid, (x, y, _) in pins.items():
                content += ('<circle id="%spin" cx="%s" cy="%s" r="3" '
                            'fill="#fff" stroke="#8a6c22" stroke-width="1.5"/>' % (cid, x, y))
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%sin" height="%sin" '
               'viewBox="0 0 %s %s"><g id="%s">%s</g></svg>'
               % (size[0] / 90, size[1] / 90, *size, layer, content))
        (assets / ("svg." + folder + "." + name + ".svg")).write_text(svg, encoding="utf-8")
    connectors = element(root, "connectors")
    for cid, (_, _, label) in pins.items():
        conn = element(connectors, "connector", id=cid, name=label, type="male")
        element(conn, "description", label)
        cv = element(conn, "views")
        for view in ("breadboardView", "schematicView"):
            element(element(cv, view), "p", svgId=cid + "pin", layer=view_layers[view][1])
    bus_root = element(root, "buses")
    for i, members in enumerate(buses):
        bus = element(bus_root, "bus", id="bus%d" % i)
        for cid in members:
            element(bus, "nodeMember", connectorId=cid)
    xml_write(assets / ("part." + name + ".fzp"), root)
    return {"name": name, "module": root.get("moduleId"), "pins": pins}


def make_parts():
    body = '<rect x="4" y="4" width="302" height="376" rx="10" fill="#eee8f5" stroke="#624780"/>'
    body += svg_text(16, 25, "PROGRAMMING CLIP / PROBE", 16)
    body += svg_text(16, 44, "J1 TOP VIEW - extended front edge up", 11)
    body += svg_text(16, 61, "2.54 mm mating posts; pin 1 lower left", 11)
    pins, buses = {}, []
    for sig, color, hexcolor, host, _, number, pogo, tp, net in SIGNALS:
        n = int(number)
        x, y = 55 + ((n - 1) // 2) * 90, 85 if n % 2 == 0 else 132
        cid = "connector" + number
        pins[cid] = (x, y, "J1." + number + " " + sig)
        body += svg_text(x, y - 10, number + " " + sig, 11, signal_ink(hexcolor), "middle")
        output = "connector" + str(10 + n)
        oy = 185 + (n - 1) * 28
        pins[output] = (299, oy, pogo + " " + sig)
        buses.append((cid, output))
        body += svg_line([(x, y + 4), (x, 153 + n * 2), (270 + n * 2, 153 + n * 2),
                          (270 + n * 2, oy), (295, oy)], hexcolor, 1)
        body += svg_text(16, oy + 4, "J1.%s -> %s : %s" % (number, pogo, sig), 11, signal_ink(hexcolor))
    body += svg_text(16, 361, "P4 / PB3 and P5 / PB4: spare, NO ISP cable", 10)
    body += svg_text(16, 377, "Right-hand links depict contacts; not more jumpers", 10)
    probe = part("isp_probe", "IR ISP probe", (310, 384), body, pins, buses)

    body = '<rect x="4" y="4" width="302" height="105" rx="8" fill="#eee8f5" stroke="#624780"/>'
    body += svg_text(16, 25, "ANVIL / FRONT GND RETURN", 15)
    body += svg_text(16, 48, "J1 -> P8 (earlier) / P8L + P8R (v0.2)", 11)
    body += svg_line([(299, 8), (299, 72)], "#202020")
    body += svg_text(16, 99, "Insulated wire from probe J2; NOT an upper pogo", 10)
    anvil = part("isp_anvil", "IR ground anvil", (310, 114), body,
                 {"connector1": (299, 8, "Anvil J1 GND"),
                  "connector2": (299, 72, "P8 / P8L / P8R GND")},
                 [("connector1", "connector2")])

    body = '<rect x="4" y="4" width="302" height="376" rx="10" fill="#e2f1e7" stroke="#22734e"/>'
    body += svg_text(16, 25, "RING IR PCB / ATtiny85", 16)
    body += svg_text(16, 45, "Rear test pads UP; LEDs/components DOWN", 11)
    body += svg_text(16, 62, "Logical pad list below, NOT physical pad spacing", 11)
    pins = {}
    for i, (sig, _, hexcolor, _, _, _, _, tp, net) in enumerate(SIGNALS):
        y = 185 + i * 28
        pins["connector" + str(i + 1)] = (10, y, tp + " " + net)
        body += svg_text(27, y + 4, tp + " / " + net + " / " + sig, 13, signal_ink(hexcolor))
    body += svg_text(16, 104, "Rear: TP1 / TP2 / TP3 / TP6 + off-grid TP9", 10)
    body += svg_text(16, 123, "Front: TP8 GND bar (via lower anvil)", 11)
    body += svg_text(16, 145, "TP4 / PB3 and TP5 / PB4 are spare", 11)
    body += svg_text(16, 369, "REMOVE CR2032 before programming", 12, "#a62b0d")
    ring = part("isp_target", "Ring IR target", (310, 384), body, pins)

    body = '<rect x="4" y="4" width="302" height="99" rx="8" fill="#fff1ee" stroke="#d62728"/>'
    body += svg_text(16, 48, "SELECTED TARGET SUPPLY", 14)
    body += svg_text(16, 69, "One current-limited source, voltage qualified", 11)
    body += svg_text(16, 90, "No automatic connection to Uno 5V / 3V3", 11)
    body += svg_text(252, 25, "3V3 VCC", 11)
    body += svg_text(32, 25, "GND", 11, "#202020")
    supply = part("isp_supply", "Selected target VCC", (310, 108), body,
                  {"connector1": (299, 8, "Selected target VCC"),
                   "connector2": (45, 8, "Common GND")})
    return probe, anvil, ring, supply


def uno_positions(fritzing):
    part_path = fritzing / "fritzing-parts" / "core" / (UNO_MODULE + ".fzp")
    part_root = ET.parse(part_path).getroot()
    result = {}
    wanted = {s[4] for s in SIGNALS if s[4]}
    for _, _, _, host, cid, _, _, _, _ in SIGNALS:
        if cid:
            connector = part_root.find("connectors/connector[@id='%s']" % cid)
            if connector is None or connector.get("name").split()[0].split("/")[0] != host:
                raise ValueError("Installed Uno part changed connector mapping: " + host)
    for view in ("breadboardView", "schematicView"):
        image = part_root.find("views/" + view + "/layers").get("image")
        root = ET.parse(fritzing / "fritzing-parts" / "svg" / "core" / image).getroot()
        width = float(root.get("width")[:-2]) * 90
        units = float(root.get("viewBox").split()[2])
        scale = width / units
        by_id = {e.get("id"): e for e in root.iter() if e.get("id")}
        points = {}
        for cid in wanted:
            con = part_root.find("connectors/connector[@id='%s']" % cid)
            node = con.find("views/" + view + "/p")
            ident = node.get("terminalId") or node.get("svgId")
            e = by_id[ident]
            if "cx" in e.attrib:
                x, y = float(e.get("cx")), float(e.get("cy"))
            else:
                x = float(e.get("x")) + float(e.get("width")) / 2
                y = float(e.get("y")) + float(e.get("height")) / 2
            points[cid] = (x * scale, y * scale)
        result[view] = points
    return result


def sketch(parts, uno):
    root = ET.Element("module", fritzingVersion="1.0.8")
    global_views = element(root, "views")
    for name in ("breadboardView", "schematicView", "pcbView"):
        element(global_views, "view", name=name, backgroundColor="#ffffff",
                gridSize="0.1in", showGrid="0", alignToGrid="0")
    instances = element(root, "instances")
    models, locations = {}, {}
    layers = {"breadboardView": ("breadboard", "breadboardWire", 64),
              "schematicView": ("schematic", "schematicTrace", 128)}
    for index, (part_info, pos) in enumerate(zip(parts, [(425, 135), (425, 570),
                                                       (925, 135), (30, 570)]), start=2):
        inst = element(instances, "instance", moduleIdRef=part_info["module"],
                       modelIndex=index, path=part_info["name"] + ".fzp")
        element(inst, "title", part_info["name"])
        views = element(inst, "views")
        models[index] = {}
        locations[index] = {}
        for view, (layer, _, _) in layers.items():
            v = element(views, view, layer=layer)
            element(v, "geometry", x=pos[0], y=pos[1], z=2)
            models[index][view] = element(v, "connectors")
            locations[index][view] = {cid: (pos[0] + pin[0], pos[1] + pin[1])
                                      for cid, pin in part_info["pins"].items()}
    host = element(instances, "instance", moduleIdRef=UNO_MODULE, modelIndex=1,
                   path=UNO_MODULE + ".fzp")
    element(host, "title", "UNO - ArduinoISP")
    views = element(host, "views")
    models[1], locations[1] = {}, {}
    for view, (layer, _, _) in layers.items():
        host_layer = "breadboardbreadboard" if view == "breadboardView" else layer
        v = element(views, view, layer=host_layer)
        element(v, "geometry", x=45, y=215, z=2)
        models[1][view] = element(v, "connectors")
        locations[1][view] = {cid: (45 + x, 215 + y) for cid, (x, y) in uno[view].items()}

    connector_nodes = {}

    def connect(model, cid, view, wire, endpoint, wire_layer):
        key = (model, cid, view)
        if key not in connector_nodes:
            layer = "breadboardbreadboard" if model == 1 and view == "breadboardView" else layers[view][0]
            c = element(models[model][view], "connector", connectorId=cid, layer=layer)
            element(c, "geometry", x=0, y=0)
            connector_nodes[key] = element(c, "connects")
        element(connector_nodes[key], "connect", connectorId=endpoint, modelIndex=wire, layer=wire_layer)

    wire_index = 100

    def wire(a, b, color, title, bend=None):
        nonlocal wire_index
        wire_index += 1
        w = element(instances, "instance", moduleIdRef="WireModuleID",
                    modelIndex=wire_index, path="wire.fzp")
        element(w, "title", title)
        views = element(w, "views")
        for view, (_, wire_layer, flags) in layers.items():
            start = locations[a[0]][view][a[1]]
            end = locations[b[0]][view][b[1]]
            v = element(views, view, layer=wire_layer)
            dx, dy = end[0] - start[0], end[1] - start[1]
            element(v, "geometry", x=start[0], y=start[1], z=3,
                    x1=0, y1=0, x2=dx, y2=dy, wireFlags=flags)
            extras = element(v, "wireExtras", mils=22, color=color, opacity=1, banded=0)
            if bend is not None:
                bezier = element(extras, "bezier")
                element(bezier, "cp0", x=bend[0], y=bend[1])
                element(bezier, "cp1", x=dx + bend[2], y=dy + bend[3])
            connectors = element(v, "connectors")
            for i, (model, cid) in enumerate((a, b)):
                c = element(connectors, "connector", connectorId="connector%d" % i, layer=wire_layer)
                element(c, "geometry", x=0, y=0)
                target_layer = "breadboardbreadboard" if model == 1 and view == "breadboardView" else layers[view][0]
                element(element(c, "connects"), "connect", connectorId=cid,
                        modelIndex=model, layer=target_layer)
                connect(model, cid, view, wire_index, "connector%d" % i, wire_layer)

    for sig, _, color, _, cid, number, _, _, _ in SIGNALS:
        n = int(number)
        source = (5, "connector1") if sig == "VCC" else (1, cid)
        wire(source, (2, "connector" + number), color, "Cable: " + sig)
        if sig != "GND":
            wire((2, "connector" + str(10 + n)), (4, "connector" + number), color,
                 "CONTACT ONLY: " + sig)
    wire((1, "connector89"), (5, "connector2"), "#202020", "Supply common GND")
    wire((2, "connector16"), (3, "connector1"), "#202020", "WIRE: probe J2 to anvil J1",
         (70, 50, 70, -25))
    wire((3, "connector2"), (4, "connector6"), "#202020", "CONTACT ONLY: front TP8 GND")

    notes = [
        (15, 5, 1250, 100, "<h2>Arduino Uno ArduinoISP -> programming clip -> Ring IR PCB</h2>"
         "<p>GREY MISO | WHITE 3V3 VCC | BLUE SCK | PURPLE MOSI | BROWN RESET | BLACK GND<br/>"
         "J1 = board-top view. Right-hand links represent spring/flat contacts, NOT extra cables.</p>"),
        (15, 115, 370, 90, "<b>HOST: Arduino Uno / ATmega328P</b><br/>"
         "Load File > Examples > 11.ArduinoISP > ArduinoISP.<br/>"
         "D12=MISO, D11=MOSI, D13=SCK, D10=target RESET.<br/>"
         "Do NOT use Uno RESET or the USB-interface ICSP header."),
        (15, 710, 1250, 190, "<b>POWER / SAFETY - READ BEFORE CONNECTING</b><br/>"
         + "<br/>".join(html.escape(s) for s in WARNINGS)),
        (790, 595, 460, 105, "<b>BLACK inter-jaw lead is essential.</b><br/>"
         "J1.6 -> probe J2 -> insulated slack wire -> anvil J1 -> P8 / P8L+P8R -> front TP8.<br/>"
         "Fence and lower guide are mechanical; do not populate their header."),
    ]
    for i, (x, y, width, height, text) in enumerate(notes, start=900):
        note = element(instances, "instance", moduleIdRef="NoteModuleID", modelIndex=i, path="note.fzp")
        element(note, "title", "Wiring note")
        element(note, "text", "<html><body style='font-family:Arial;font-size:10pt'>" + text + "</body></html>")
        views = element(note, "views")
        for view, layer in (("breadboardView", "breadboardNote"), ("schematicView", "schematicNote")):
            v = element(views, view, layer=layer)
            element(v, "geometry", x=x, y=y, z=6, width=width, height=height)
    xml_write(HERE / "arduino_isp_harness.fz", root)
    with zipfile.ZipFile(HERE / "arduino_isp_harness.fzz", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(HERE / "arduino_isp_harness.fz", "arduino_isp_harness.fz")
        for p in sorted((HERE / "parts").iterdir()):
            z.write(p, p.name)


def reference():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1080" viewBox="0 0 1500 1080">'
    svg += ('<title>ArduinoISP to clip to IR ring: colour-coded harness reference</title>'
            '<desc>Lantern Ring contributors. CC BY-SA 3.0: https://creativecommons.org/licenses/by-sa/3.0/</desc>'
            '<rect width="1500" height="1080" fill="#fff"/>')
    svg += svg_text(35, 48, "ARDUINO ISP -> PROGRAMMING CLIP -> RING IR PCB", 29)
    svg += svg_text(35, 80, "User-reported COM6 harness colours; unchanged ISP-6 pinout. White leads have a dark outline for print.", 18)
    headers = [(35, 100, 250, "ARDUINO UNO / HOST"), (460, 100, 240, "PROBE J1 / ISP-6"),
               (855, 100, 265, "CLIP CONTACT PATH"), (1215, 100, 250, "RING IR / TARGET")]
    for x, y, w, text in headers:
        svg += '<rect x="%s" y="%s" width="%s" height="44" rx="5" fill="#17334c"/>' % (x, y, w)
        svg += svg_text(x + 12, y + 29, text, 17, "#fff")
    for i, (sig, color, hexcolor, host, _, number, pogo, tp, net) in enumerate(SIGNALS):
        y = 185 + i * 65
        svg += '<rect x="30" y="%s" width="1440" height="54" rx="5" fill="#f3f6f8"/>' % (y - 31)
        svg += svg_text(45, y, host + (" *" if sig == "VCC" else ""), 22)
        svg += svg_line([(290, y - 6), (445, y - 6)], hexcolor, 6)
        svg += svg_text(365, y - 16, color.upper(), 14, signal_ink(hexcolor), "middle")
        svg += svg_text(475, y, number + "  " + sig, 23)
        svg += svg_line([(710, y - 6), (840, y - 6)], hexcolor, 6)
        route = "J2 -> wire -> anvil" if sig == "GND" else pogo + " pogo"
        svg += svg_text(870, y, route, 20)
        svg += svg_line([(1125, y - 6), (1200, y - 6)], hexcolor, 4)
        svg += svg_text(1230, y, tp + " / " + net, 22)
    svg += svg_text(35, 600, "J1: TOP VIEW of the populated probe", 22)
    svg += svg_text(35, 630, "Extended front/header edge is above; pogo grid and jaw slots below.", 16)
    for _, _, color, _, _, n, _, _, _ in SIGNALS:
        number = int(n)
        sig = next(s[0] for s in SIGNALS if s[5] == n)
        x, y = 95 + ((number - 1) // 2) * 170, 680 if number % 2 == 0 else 742
        svg += '<rect x="%s" y="%s" width="150" height="48" rx="5" fill="%s" stroke="#607080"/>' % (x - 60, y - 30, color)
        svg += svg_text(x + 15, y, n + " " + sig, 20, "#17334c" if color == "#ffffff" else "#fff", "middle")
    svg += svg_text(35, 790, "Confirm pin 1 on silk. Cable mating-face view is mirrored.", 16)
    svg += svg_text(650, 605, "BLACK ground-return lead inside the clip", 22)
    svg += svg_text(650, 637, "J1.6 -> probe J2 -> insulated slack wire -> anvil J1", 18)
    svg += svg_text(650, 667, "-> P8 (earlier) or P8L + P8R (v0.2) -> FRONT TP8.", 18)
    svg += svg_text(650, 705, "Five upper ISP contacts: TP1, TP2, TP3, TP6 and TP9.", 18)
    svg += svg_text(650, 735, "TP4/PB3 and TP5/PB4 are spare, NOT extra ISP signals.", 18)
    svg += svg_text(650, 773, "D10 goes to TARGET RESET, never to the Uno RESET pin.", 18)
    svg += '<rect x="25" y="814" width="1450" height="240" rx="8" fill="#fff1e9" stroke="#a62b0d"/>'
    for i, text in enumerate(WARNINGS):
        svg += svg_text(40, 844 + i * 31, ("* " if i == 1 else "") + text, 18, "#8c250d")
    svg += "</svg>"
    (HERE / "wiring-reference.svg").write_text(svg, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fritzing", type=pathlib.Path, default=pathlib.Path(r"C:\Program Files\Fritzing"))
    args = parser.parse_args()
    params = json.loads((CLIP / "parameters.json").read_text())
    for sig, _, _, _, _, number, _, tp, net in SIGNALS:
        if params["isp_header"]["pins"][number] != net or params["dut"]["expected_nets"][tp] != net:
            raise ValueError("Harness no longer matches clip/target pinout: " + sig)
    parts = make_parts()
    sketch(parts, uno_positions(args.fritzing))
    reference()
    print("Generated arduino_isp_harness.fzz and wiring-reference.svg; export with Fritzing -svg.")


if __name__ == "__main__":
    main()
