"""Generate the motion/RGB board's placed KiCad PCB from the mono board datum.

Run with KiCad's bundled Python, for example:
    & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" `
      hardware\\v2.0\\ring_motion_rgb\\generate_board.py

This creates a placement/interface baseline only. The electrical nets are
assigned, but the board is intentionally not routed or manufacturing-ready.
"""

from pathlib import Path
import os
import re
import tempfile

import pcbnew


ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
SOURCE = ROOT / "hardware" / "v2.0" / "ring_mono" / "ring_mono.kicad_pcb"
OUTPUT = OUT_DIR / "ring_motion_rgb.kicad_pcb"
FOOTPRINT_ROOT = Path(
    os.environ.get(
        "KICAD_FOOTPRINT_DIR",
        r"C:\Program Files\KiCad\10.0\share\kicad\footprints",
    )
)

BOARD_CENTER = (136.906, 83.185)
MM = pcbnew.FromMM


def point(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def net_map(board):
    return {
        str(name): net
        for name, net in board.GetNetInfo().NetsByName().items()
    }


def add_net(board, nets, name):
    if name not in nets:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net
    return nets[name]


def footprint(library, name, reference, value, x, y, angle=0):
    path = FOOTPRINT_ROOT / f"{library}.pretty"
    item = pcbnew.FootprintLoad(str(path), name)
    if item is None:
        raise RuntimeError(f"Could not load footprint {library}:{name}")
    item.SetReference(reference)
    item.SetValue(value)
    item.SetPosition(point(x, y))
    item.SetOrientationDegrees(angle)
    return item


def add_part(board, nets, library, name, reference, value, local_xy,
             angle=0, pad_nets=None, back=False):
    x = BOARD_CENTER[0] + local_xy[0]
    y = BOARD_CENTER[1] + local_xy[1]
    item = footprint(
        library, name, reference, value, x, y, angle=angle
    )
    board.Add(item)
    if back:
        item.Flip(item.GetPosition(), False)
    for pad in item.Pads():
        net_name = (pad_nets or {}).get(pad.GetNumber())
        if net_name:
            pad.SetNet(add_net(board, nets, net_name))
    return item


def add_clip_pad(board, nets, reference, local_xy, net_name):
    return add_part(
        board,
        nets,
        "TestPoint",
        "TestPoint_Pad_1.5x1.5mm",
        reference,
        net_name,
        local_xy,
        pad_nets={"1": net_name},
        back=True,
    )


def strip_source_layout(text):
    """Remove old mono LED footprints and routes before pcbnew loads the board."""
    output = []
    position = 0
    depth = 0
    quoted = False
    escaped = False
    index = 0

    while index < len(text):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            index += 1
            continue

        if char == '"':
            quoted = True
            index += 1
            continue

        if char == "(":
            if depth == 1:
                token = re.match(r"\(([^\s()]+)", text[index:])
                key = token.group(1) if token else ""
                if key in {"segment", "via"}:
                    end = expression_end(text, index)
                    output.append(text[position:index])
                    position = end
                    index = end
                    continue
                if key == "footprint":
                    end = expression_end(text, index)
                    block = text[index:end]
                    reference = re.search(
                        r'(?:\(property "Reference" |\(?fp_text reference )"([^"]+)"',
                        block,
                    )
                    if reference and reference.group(1) in {
                        f"D{i}" for i in range(1, 7)
                    }:
                        output.append(text[position:index])
                        position = end
                        index = end
                        continue
                    if reference and reference.group(1) in {"TP1", "TP2"}:
                        output.append(text[position:index])
                        output.append(
                            block.replace('(layer "F.SilkS")', '(layer "F.Fab")')
                                 .replace('(layer "F.CrtYd")', '(layer "F.Fab")')
                        )
                        position = end
                        index = end
                        continue
            depth += 1
        elif char == ")":
            depth -= 1
        index += 1

    output.append(text[position:])
    return "".join(output)


def expression_end(text, start):
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError(f"Unclosed KiCad expression at offset {start}")


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if not FOOTPRINT_ROOT.is_dir():
        raise FileNotFoundError(
            f"KiCad footprint library directory not found: {FOOTPRINT_ROOT}"
        )

    source_text = strip_source_layout(SOURCE.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        clean_source = Path(temporary) / "ring_mono_seed.kicad_pcb"
        clean_source.write_text(source_text, encoding="utf-8")
        board = pcbnew.LoadBoard(str(clean_source))

    # F.Cu keeps the ground anvil plane and B.Cu keeps the battery contact
    # plane, so the inner layers are signal layers for routing density.
    board.SetCopperLayerCount(4)
    ground = board.FindNet("/GND")
    vcc = board.FindNet("VCC")
    nets = {"/GND": ground, "GND": ground, "VCC": vcc}

    for item in board.GetFootprints():
        if item.GetReference() in {"TP1", "TP2"}:
            for pad in item.Pads():
                pad.SetNet(ground)

    for zone in board.Zones():
        if zone.GetLayer() == pcbnew.F_Cu:
            zone.SetNet(ground)
        elif zone.GetLayer() == pcbnew.B_Cu:
            zone.SetNet(vcc)

    for name in (
        "PB0", "PB1", "PB2", "PB3", "PB4", "PB5",
        "ACC_SCL", "ACC_SDA", "ACC_INT",
        "PWM_R", "PWM_G", "PWM_B",
        "LIMIT_R", "LIMIT_G", "LIMIT_B",
    ):
        add_net(board, nets, name)

    # QFN pad numbers follow the KiCad ATtiny84A-M symbol. The clip's PB0,
    # PB1, and PB2 pads are the native USI programming pins. PB5 is the clip
    # alias for the chip's native PB3/RESET pad; PB3/PB4 are spare probe aliases.
    mcu_pads = {
        "1": "ACC_INT",   # PA4
        "2": "PWM_B",     # PA3
        "3": "ACC_SCL",   # PA2
        "4": "PWM_G",     # PA1
        "5": "PWM_R",     # AREF / PA0
        "8": "GND",
        "9": "VCC",
        "11": "PB0",      # USI DI / MOSI
        "12": "PB1",      # USI DO / MISO
        "13": "PB5",      # PB3 / RESET, clip alias
        "14": "PB2",      # USI USCK / SCK
        "15": "ACC_SDA",  # PA7
        "16": "PB4",      # PA6, spare clip probe alias
        "20": "PB3",      # PA5, spare clip probe alias
        "21": "GND",      # exposed pad
    }
    add_part(
        board, nets, "Package_DFN_QFN",
        "QFN-20-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
        "U1", "ATtiny84A-MU", (5.9, 0), pad_nets=mcu_pads,
    )

    add_part(
        board, nets, "LED_SMD", "LED_RGB_1210",
        "D1", "IN-S128TATRGB", (0, 0),
        pad_nets={
            "1": "LED_R",
            "2": "GND",
            "3": "LED_G",
            "4": "LED_B",
        },
    )

    add_part(
        board, nets, "Package_LGA", "LGA-12_2x2mm_P0.5mm",
        "U2", "LIS2DW12TR", (-4.0, 4.5),
        pad_nets={
            "1": "GND",
            "2": "",
            "3": "ACC_SCL",  # SCL / SPC
            "4": "VCC",      # CS tied high selects I2C
            "5": "GND",      # SDO / SA0 low selects address 0x18
            "6": "ACC_SDA",
            "7": "",
            "8": "",         # INT2 unused
            "9": "ACC_INT",  # INT1
            "10": "VCC",     # VDDIO
            "11": "VCC",     # VDD
            "12": "GND",
        },
    )

    for ref, color, x, y in (
        ("J1", "R", -5.5, -4.7),
        ("J2", "G", -1.5, -4.7),
        ("J3", "B", 5.5, -4.7),
    ):
        pwm_net = f"PWM_{color}"
        limit_net = f"LIMIT_{color}"
        add_part(
            board, nets, "Jumper", "SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
            ref, f"{color} enable", (x, y),
            pad_nets={"1": pwm_net, "2": limit_net},
            angle=180 if ref == "J3" else 0,
        )

    for ref, color, x, y in (
        ("R1", "R", -4.1, -0.6),
        ("R2", "G", -4.1, 1.5),
        ("R3", "B", 0, -2.5),
    ):
        add_part(
            board, nets, "Resistor_SMD", "R_0402_1005Metric",
            ref, "1k", (x, y),
            pad_nets={"1": f"LIMIT_{color}", "2": f"LED_{color}"},
            angle=180 if ref == "R3" else 0,
        )

    add_part(
        board, nets, "Resistor_SMD", "R_0402_1005Metric",
        "R4", "10k RESET pull-up", (5.9, 4.2),
        angle=0, pad_nets={"1": "PB5", "2": "VCC"},
    )
    add_part(
        board, nets, "Capacitor_SMD", "C_0402_1005Metric",
        "C1", "100nF MCU decoupling", (2.0, -3.8),
        pad_nets={"1": "VCC", "2": "GND"},
    )
    add_part(
        board, nets, "Capacitor_SMD", "C_0402_1005Metric",
        "C2", "100nF accelerometer decoupling", (-6.3, 4.5),
        angle=90, pad_nets={"1": "VCC", "2": "GND"},
    )

    # Preserve the exact seven-pad programming-clip grid and front ground
    # anvil datum from the IR board, translated to the mono board center.
    clip = {
        "P1": ((3.0754, 4.6736), "PB0"),
        "P2": ((3.0754, 7.7236), "PB1"),
        "P3": ((0.0254, 4.6736), "PB2"),
        "P4": ((0.0254, 7.7236), "PB3"),
        "P5": ((-3.0246, 4.6736), "PB4"),
        "P6": ((-3.0246, 7.7236), "PB5"),
        "P9": ((0.127, 0.127), "VCC"),
    }
    for reference, (xy, name) in clip.items():
        add_clip_pad(board, nets, reference, xy, name)

    add_part(
        board, nets, "TestPoint", "TestPoint_Pad_1.5x1.5mm",
        "TP8", "GND", (0.127, 8.509),
        pad_nets={"1": "GND"},
    )

    for item in board.GetFootprints():
        if item.GetReference() == "U2":
            pads = item.Pads()
            for index in range(pads.size()):
                pad = pads[index]
                pad.SetLocalClearance(MM(0.15))
        pads = item.Pads()
        for index in range(pads.size()):
            pad = pads[index]
            if pad.GetNetname() in {"/GND", "GND"}:
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    pad_only_refs = {
        "TP1", "TP2", "TP8", "P1", "P2", "P3", "P4", "P5", "P6", "P9"
    }
    for item in board.GetFootprints():
        if item.GetReference() not in pad_only_refs:
            continue
        drawings = item.GraphicalItems()
        if not hasattr(drawings, "size"):
            continue
        for index in range(drawings.size()):
            graphic = drawings[index]
            layer = graphic.GetLayer()
            if layer == pcbnew.F_SilkS:
                graphic.SetLayer(pcbnew.F_Fab)
            elif layer == pcbnew.B_SilkS:
                graphic.SetLayer(pcbnew.B_Fab)
            elif layer == pcbnew.F_CrtYd:
                graphic.SetLayer(pcbnew.F_Fab)
            elif layer == pcbnew.B_CrtYd:
                graphic.SetLayer(pcbnew.B_Fab)

    # The clip's specified front anvil pad has only 0.1 mm of edge margin.
    board.GetDesignSettings().m_CopperEdgeClearance = MM(0.1)

    # Preserve readable assembly references without crowding the tiny board's
    # required contact and component-side silkscreen.
    for item in board.GetFootprints():
        fab_layer = (
            pcbnew.F_Fab if item.GetLayer() == pcbnew.F_Cu else pcbnew.B_Fab
        )
        item.Reference().SetLayer(fab_layer)
        item.Reference().SetVisible(True)
        item.Value().SetVisible(False)

    # In2.Cu is a ground plane so isolated front GND pads can via down to it.
    for zone in list(board.Zones()):
        if zone.GetLayer() == pcbnew.F_Cu and not zone.GetIsRuleArea():
            inner = zone.Duplicate()
            inner.SetLayer(pcbnew.In2_Cu)
            inner.SetNet(ground)
            board.Add(inner)
            break

    # Keep vias and tracks out of the exposed battery contact on B.Cu.
    keepout = pcbnew.ZONE(board)
    keepout.SetIsRuleArea(True)
    keepout.SetDoNotAllowTracks(True)
    keepout.SetDoNotAllowVias(True)
    keepout.SetDoNotAllowPads(False)
    keepout.SetDoNotAllowFootprints(False)
    keepout.SetDoNotAllowZoneFills(False)
    keepout.SetLayer(pcbnew.B_Cu)
    keepout.SetZoneName("battery_contact_keepout")
    outline = keepout.Outline()
    outline.NewOutline()
    import math
    for step in range(48):
        angle = 2 * math.pi * step / 48
        outline.Append(
            MM(BOARD_CENTER[0] + 3.1 * math.cos(angle)),
            MM(BOARD_CENTER[1] - 0.381 - 3.1 * math.sin(angle)),
        )
    board.Add(keepout)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pcbnew.SaveBoard(str(OUTPUT), board)
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
