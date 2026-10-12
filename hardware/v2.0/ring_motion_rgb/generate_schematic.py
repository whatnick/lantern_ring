"""Generate the motion/RGB ring schematic from its PCB interface contract."""

from pathlib import Path
import re
import uuid


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "ring_motion_rgb.kicad_sch"
KICAD_SYMBOLS = Path(
    r"C:\Program Files\KiCad\10.0\share\kicad\symbols"
)
ROOT_UUID = "d2c8c6c5-3e4a-45eb-9a9a-5f1e1eb91048"
PROJECT = "ring_motion_rgb"
MCU_LIBRARY = KICAD_SYMBOLS / "MCU_Microchip_ATtiny.kicad_sym"


def uid():
    return str(uuid.uuid4())


def sexpr_end(text, start):
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
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("Unclosed KiCad symbol expression")


def mcu_symbol():
    text = MCU_LIBRARY.read_text(encoding="utf-8")
    start = text.index('(symbol "ATtiny24V-10M"')
    source = text[start:sexpr_end(text, start)]
    source = source.replace("ATtiny24V-10M", "ATtiny84A-MU")
    source = source.replace(
        "http://ww1.microchip.com/downloads/en/DeviceDoc/doc8006.pdf",
        "https://ww1.microchip.com/downloads/en/DeviceDoc/"
        "ATtiny24A-44A-84A-DataSheet-DS40002269A.pdf",
    )
    source = source.replace(
        "10MHz, 2kB Flash, 128B SRAM, 128B EEPROM, debugWIRE, QFN-20",
        "8-bit AVR MCU, 8kB Flash, 512B SRAM, 512B EEPROM, QFN-20",
    )
    return source.replace(
        '(symbol "ATtiny84A-MU"',
        '(symbol "Lantern:ATtiny84A-MU"',
        1,
    )


def font(size=1.27):
    return f"(effects (font (size {size} {size})))"


def lib_pin(number, name, electrical, x, y, angle, length=2.54, hide=False):
    hidden = " hide" if hide else ""
    return (
        f'(pin {electrical} line (at {x:g} {y:g} {angle}) '
        f'(length {length:g}){hidden} '
        f'(name "{name}" {font()}) (number "{number}" {font()}))'
    )


def rectangle_symbol(lib_id, reference, pins, footprint="", description=""):
    short_name = lib_id.split(":")[-1]
    pin_text = "\n".join(pins)
    hide_fp = " hide"
    return f'''(symbol "{lib_id}"
  (pin_names (offset 1.016))
  (exclude_from_sim no)
  (in_bom yes)
  (on_board yes)
  (property "Reference" "{reference}" (at 0 6.35 0) {font()})
  (property "Value" "{short_name}" (at 0 -6.35 0) {font()})
  (property "Footprint" "{footprint}" (at 0 0 0)
    (effects (font (size 1.27 1.27)){hide_fp}))
  (property "Datasheet" "" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (property "ki_description" "{description}" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (symbol "{short_name}_0_1"
    (rectangle (start -5.08 -5.08) (end 5.08 5.08)
      (stroke (width 0.254) (type default)) (fill (type background))))
  (symbol "{short_name}_1_1"
    {pin_text}
  )
)'''


def resistor_symbol(name, reference_prefix, footprint):
    return f'''(symbol "Lantern:{name}"
  (pin_names (offset 0.762) (hide yes))
  (in_bom yes) (on_board yes)
  (property "Reference" "{reference_prefix}" (at 0 2.54 90) {font()})
  (property "Value" "{name}" (at 0 -2.54 90) {font()})
  (property "Footprint" "{footprint}" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (property "Datasheet" "" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (symbol "{name}_0_1"
    (polyline (pts (xy -1.27 -1.905) (xy 1.27 -1.905)
                   (xy 1.27 1.905) (xy -1.27 1.905)
                   (xy -1.27 -1.905))
      (stroke (width 0.254) (type default)) (fill (type none))))
  (symbol "{name}_1_1"
    {lib_pin("1", "1", "passive", -3.81, 0, 0)}
    {lib_pin("2", "2", "passive", 3.81, 0, 180)}
  )
)'''


def capacitor_symbol():
    return '''(symbol "Lantern:C"
  (pin_names (offset 0.762) (hide yes))
  (in_bom yes) (on_board yes)
  (property "Reference" "C" (at 0 2.54 90) (effects (font (size 1.27 1.27))))
  (property "Value" "C" (at 0 -2.54 90) (effects (font (size 1.27 1.27))))
  (property "Footprint" "Capacitor_SMD:C_0402_1005Metric" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (property "Datasheet" "" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (symbol "C_0_1"
    (polyline (pts (xy -1.27 0.254) (xy 1.27 0.254))
      (stroke (width 0.254) (type default)) (fill (type none)))
    (polyline (pts (xy -1.27 -0.254) (xy 1.27 -0.254))
      (stroke (width 0.254) (type default)) (fill (type none))))
  (symbol "C_1_1"
    (pin passive line (at 0 3.81 270) (length 2.54)
      (name "1" (effects (font (size 1.27 1.27))))
      (number "1" (effects (font (size 1.27 1.27))))
    )
    (pin passive line (at 0 -3.81 90) (length 2.54)
      (name "2" (effects (font (size 1.27 1.27))))
      (number "2" (effects (font (size 1.27 1.27))))
    )
  )
)'''


def jumper_symbol():
    return '''(symbol "Lantern:JP"
  (pin_names (offset 0.762) (hide yes))
  (in_bom yes) (on_board yes)
  (property "Reference" "J" (at 0 2.54 90) (effects (font (size 1.27 1.27))))
  (property "Value" "Open solder bridge" (at 0 -2.54 90) (effects (font (size 1.27 1.27))))
  (property "Footprint" "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (property "Datasheet" "" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (symbol "JP_0_1"
    (circle (center -1.27 0) (radius 0.762)
      (stroke (width 0.254) (type default)) (fill (type none)))
    (circle (center 1.27 0) (radius 0.762)
      (stroke (width 0.254) (type default)) (fill (type none))))
  (symbol "JP_1_1"
    (pin passive line (at -3.81 0 0) (length 2.54)
      (name "1" (effects (font (size 1.27 1.27))))
      (number "1" (effects (font (size 1.27 1.27))))
    )
    (pin passive line (at 3.81 0 180) (length 2.54)
      (name "2" (effects (font (size 1.27 1.27))))
      (number "2" (effects (font (size 1.27 1.27))))
    )
  )
)'''


def simple_symbols():
    sensor = []
    sensor_names = (
        "GND", "RES", "SCL/SPC", "CS", "SDO/SA0", "SDA/SDI",
        "NC", "INT2", "INT1", "VDDIO", "VDD", "GND",
    )
    sensor_types = (
        "power_in", "no_connect", "input", "input", "input", "bidirectional",
        "no_connect", "no_connect", "output", "power_in", "power_in", "power_in",
    )
    for index, (name, electrical) in enumerate(zip(sensor_names, sensor_types)):
        number = index + 1
        side_index = index if index < 6 else index - 6
        local_y = 6.35 - side_index * 2.54
        if index < 6:
            x, angle = -7.62, 0
        else:
            x, angle = 7.62, 180
        sensor.append(lib_pin(number, name, electrical, x, local_y, angle))
    u2 = rectangle_symbol(
        "Lantern:LIS2DW12TR",
        "U",
        sensor,
        "Package_LGA:LGA-12_2x2mm_P0.5mm",
        "3-axis ultra-low-power accelerometer",
    )

    rgb_pins = (
        lib_pin("1", "R", "passive", -7.62, 2.54, 0),
        lib_pin("2", "K", "passive", -7.62, -2.54, 0),
        lib_pin("3", "G", "passive", 7.62, 2.54, 180),
        lib_pin("4", "B", "passive", 7.62, -2.54, 180),
    )
    led = rectangle_symbol(
        "Lantern:RGB_LED_CC", "D", rgb_pins, "LED_SMD:LED_RGB_1210",
        "Common-cathode RGB LED",
    )
    testpoint = '''(symbol "Lantern:TestPoint"
  (pin_names (offset 0.762) (hide yes))
  (in_bom yes) (on_board yes)
  (property "Reference" "TP" (at 0 2.54 90) (effects (font (size 1.27 1.27))))
  (property "Value" "Contact pad" (at 0 -2.54 90) (effects (font (size 1.27 1.27))))
  (property "Footprint" "TestPoint:TestPoint_Pad_1.5x1.5mm" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (property "Datasheet" "" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (symbol "TestPoint_0_1"
    (circle (center 0 0) (radius 1.27)
      (stroke (width 0.254) (type default)) (fill (type none))))
  (symbol "TestPoint_1_1"
    (pin passive line (at 0 0 90) (length 0)
      (name "1" (effects (font (size 1.27 1.27))))
      (number "1" (effects (font (size 1.27 1.27))))
    )
  )
)'''
    pwr_flag = '''(symbol "Lantern:PWR_FLAG"
  (power)
  (pin_names (offset 0))
  (in_bom no) (on_board no)
  (property "Reference" "#FLG" (at 0 2.54 0)
    (effects (font (size 1.27 1.27)) hide))
  (property "Value" "PWR_FLAG" (at 0 0 0)
    (effects (font (size 1.27 1.27))))
  (property "Footprint" "" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (property "Datasheet" "" (at 0 0 0)
    (effects (font (size 1.27 1.27)) hide))
  (symbol "PWR_FLAG_0_1"
    (polyline (pts (xy 0 0) (xy 0 2.54))
      (stroke (width 0) (type default)) (fill (type none)))
    (polyline (pts (xy -1.27 2.54) (xy 1.27 2.54) (xy 0 3.81) (xy -1.27 2.54))
      (stroke (width 0) (type default)) (fill (type none))))
  (symbol "PWR_FLAG_1_1"
    (pin power_out line (at 0 0 90) (length 0) hide
      (name "pwr_flag" (effects (font (size 1.27 1.27))))
      (number "1" (effects (font (size 1.27 1.27))))
    )
  )
)'''
    return [
        u2,
        led,
        testpoint,
        pwr_flag,
        resistor_symbol("R", "R", "Resistor_SMD:R_0402_1005Metric"),
        capacitor_symbol(),
        jumper_symbol(),
    ]


def instance(lib_id, ref, value, footprint, datasheet, x, y, pin_numbers,
             angle=0, field_offset=7.62):
    component_uuid = uid()
    properties = [
        ("Reference", ref, x, y - field_offset, 0, ""),
        ("Value", value, x, y + field_offset, 0, ""),
        ("Footprint", footprint, x, y, 0, " hide"),
        ("Datasheet", datasheet, x, y, 0, " hide"),
    ]
    property_text = "\n".join(
        f'''(property "{name}" "{text}" (at {px:g} {py:g} {rotation})
      (effects (font (size 1.27 1.27)){hidden}))'''
        for name, text, px, py, rotation, hidden in properties
    )
    pin_text = "\n".join(
        f'(pin "{number}" (uuid "{uid()}"))' for number in pin_numbers
    )
    return f'''(symbol (lib_id "{lib_id}") (at {x:g} {y:g} {angle}) (unit 1)
  (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced)
  (uuid "{component_uuid}")
  {property_text}
  {pin_text}
  (instances
    (project "{PROJECT}"
      (path "/{ROOT_UUID}" (reference "{ref}") (unit 1))
    )
  )
)'''


def custom_pin_xy(ref, number, x, y, angle=0):
    if ref == "U1":
        mcu_pins = {
            "1": (15.24, 5.08, 0),
            "2": (15.24, 7.62, 0),
            "3": (15.24, 10.16, 0),
            "4": (15.24, 12.7, 0),
            "5": (15.24, 15.24, 0),
            "6": (-12.7, -5.08, 180),
            "7": (-12.7, -7.62, 180),
            "8": (0, -22.86, 0),
            "9": (0, 22.86, 0),
            "10": (-12.7, -10.16, 180),
            "11": (15.24, -7.62, 0),
            "12": (15.24, -10.16, 0),
            "13": (15.24, -15.24, 0),
            "14": (15.24, -12.7, 0),
            "15": (15.24, -2.54, 0),
            "16": (15.24, 0, 0),
            "17": (-12.7, -12.7, 180),
            "18": (-12.7, -15.24, 180),
            "19": (-12.7, -17.78, 180),
            "20": (15.24, 2.54, 0),
            "21": (0, -22.86, 0),
        }
        local_x, local_y, pin_angle = mcu_pins[number]
        return x + local_x, y - local_y, pin_angle
    if ref == "U2":
        index = int(number) - 1
        side_index = index if index < 6 else index - 6
        local_y = 6.35 - side_index * 2.54
        local_x = -7.62 if index < 6 else 7.62
        return x + local_x, y - local_y, 180 if index < 6 else 0
    if ref == "D1":
        side = "left" if number in {"1", "2"} else "right"
        local_x = -7.62 if side == "left" else 7.62
        local_y = 2.54 if number in {"1", "3"} else -2.54
        return x + local_x, y - local_y, 180 if side == "left" else 0
    if ref.startswith(("R", "J")):
        local_x = -3.81 if number == "1" else 3.81
        return x + local_x, y, 180 if number == "1" else 0
    if ref.startswith("C"):
        local_y = 3.81 if number == "1" else -3.81
        return x, y - local_y, 0
    return x, y, 0


def label(name, x, y, angle=0):
    justify = "right" if angle == 180 else "left"
    return f'''(global_label "{name}" (shape input) (at {x:g} {y:g} {angle})
  (fields_autoplaced)
  (effects (font (size 1.27 1.27)) (justify {justify}))
  (uuid "{uid()}")
  (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x:g} {y:g} 0)
    (effects (font (size 1.27 1.27)) (justify {justify}) hide))
)'''


def no_connect(x, y):
    return f'(no_connect (at {x:g} {y:g}) (uuid "{uid()}"))'


def build():
    lib_items = [mcu_symbol()] + simple_symbols()
    elements = []
    labels = []
    nc_marks = []
    component_records = []

    def add_component(lib_id, ref, value, footprint, datasheet, position,
                      pins, net_by_pin, angle=0):
        x, y = position
        x = round(x / 1.27) * 1.27
        y = round(y / 1.27) * 1.27
        elements.append(instance(
            lib_id, ref, value, footprint, datasheet, x, y, pins,
            angle=angle, field_offset=7.62 if ref not in {"U1", "U2"} else 24,
        ))
        component_records.append((ref, lib_id, value, footprint))
        for pin in pins:
            net = net_by_pin.get(str(pin))
            px, py, pin_angle = custom_pin_xy(ref, str(pin), x, y, angle)
            if net:
                labels.append(label(net, px, py, pin_angle))
            elif ref == "U1" and str(pin) in {"6", "7", "10", "17", "18", "19"}:
                # ATtiny84A NC package pads are explicitly left unconnected.
                pin_loc = {
                    "6": (x - 12.7, y + 5.08),
                    "7": (x - 12.7, y + 7.62),
                    "10": (x - 12.7, y + 10.16),
                    "17": (x - 12.7, y + 12.7),
                    "18": (x - 12.7, y + 15.24),
                    "19": (x - 12.7, y + 17.78),
                }[str(pin)]
                nc_marks.append(no_connect(*pin_loc))
            elif ref == "U2" and str(pin) in {"2", "7", "8"}:
                nc_marks.append(no_connect(px, py))

    mcu_nets = {
        "1": "ACC_INT", "2": "PWM_B", "3": "ACC_SCL",
        "4": "PWM_G", "5": "PWM_R", "8": "/GND", "9": "VCC",
        "11": "PB0", "12": "PB1", "13": "PB5", "14": "PB2",
        "15": "ACC_SDA", "16": "PB4", "20": "PB3", "21": "/GND",
    }
    add_component(
        "Lantern:ATtiny84A-MU", "U1", "ATtiny84A-MU",
        "Package_DFN_QFN:QFN-20-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
        "https://ww1.microchip.com/downloads/en/DeviceDoc/"
        "ATtiny24A-44A-84A-DataSheet-DS40002269A.pdf",
        (78.74, 105.41), [str(i) for i in range(1, 22)], mcu_nets,
    )

    sensor_nets = {
        "1": "/GND", "3": "ACC_SCL", "4": "VCC", "5": "/GND",
        "6": "ACC_SDA", "9": "ACC_INT", "10": "VCC",
        "11": "VCC", "12": "/GND",
    }
    add_component(
        "Lantern:LIS2DW12TR", "U2", "LIS2DW12TR",
        "Package_LGA:LGA-12_2x2mm_P0.5mm",
        "https://www.st.com/resource/en/datasheet/lis2dw12.pdf",
        (188.0, 85.0), [str(i) for i in range(1, 13)], sensor_nets,
    )

    add_component(
        "Lantern:RGB_LED_CC", "D1", "IN-S128TATRGB, common cathode",
        "LED_SMD:LED_RGB_1210",
        "https://www.inolux-corp.com/datasheet/SMDLED/RGB%20Top%20View/"
        "IN-S128TATRGB_V1.1.pdf",
        (175.0, 145.0), ["1", "2", "3", "4"],
        {"1": "LED_R", "2": "/GND", "3": "LED_G", "4": "LED_B"},
    )

    for ref, color, x, y in (
        ("J1", "R", 135.0, 132.0),
        ("J2", "G", 165.0, 132.0),
        ("J3", "B", 195.0, 132.0),
    ):
        add_component(
            "Lantern:JP", ref, f"{color} channel enable (normally open)",
            "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm", "",
            (x, y), ["1", "2"],
            {"1": f"PWM_{color}", "2": f"LIMIT_{color}"},
        )

    for ref, color, x, y in (
        ("R1", "R", 133.0, 158.0),
        ("R2", "G", 163.0, 158.0),
        ("R3", "B", 193.0, 158.0),
    ):
        add_component(
            "Lantern:R", ref, "1k", "Resistor_SMD:R_0402_1005Metric", "",
            (x, y), ["1", "2"],
            {"1": f"LIMIT_{color}", "2": f"LED_{color}"},
        )
    add_component(
        "Lantern:R", "R4", "10k RESET pull-up",
        "Resistor_SMD:R_0402_1005Metric", "", (135.0, 67.0), ["1", "2"],
        {"1": "PB5", "2": "VCC"},
    )
    add_component(
        "Lantern:C", "C1", "100nF MCU decoupling",
        "Capacitor_SMD:C_0402_1005Metric", "", (155.0, 65.0), ["1", "2"],
        {"1": "VCC", "2": "/GND"},
    )
    add_component(
        "Lantern:C", "C2", "100nF sensor decoupling",
        "Capacitor_SMD:C_0402_1005Metric", "", (192.0, 65.0), ["1", "2"],
        {"1": "VCC", "2": "/GND"},
    )

    # Programming/ground contact symbols mirror the probe pad references.
    contact_positions = (
        ("P1", "PB0", (65.0, 165.0)),
        ("P2", "PB1", (80.0, 165.0)),
        ("P3", "PB2", (95.0, 165.0)),
        ("P4", "PB3", (110.0, 165.0)),
        ("P5", "PB4", (125.0, 165.0)),
        ("P6", "PB5", (140.0, 165.0)),
        ("P9", "VCC", (155.0, 165.0)),
        ("TP8", "/GND", (170.0, 165.0)),
        ("TP1", "/GND", (185.0, 165.0)),
        ("TP2", "/GND", (200.0, 165.0)),
    )
    for ref, net, position in contact_positions:
        add_component(
            "Lantern:TestPoint", ref, "Programming contact" if ref.startswith("P")
            else "Ground contact", "TestPoint:TestPoint_Pad_1.5x1.5mm", "",
            position, ["1"], {"1": net},
        )

    # Mark externally supplied cell power so ERC understands the contact rails.
    power_flags = (55.88, 185.42), (69.85, 185.42)
    for index, ((x, y), net) in enumerate(zip(power_flags, ("VCC", "/GND")), 1):
        elements.append(instance(
            "Lantern:PWR_FLAG", f"#FLG0{index}", "PWR_FLAG", "", "",
            x, y, ["1"], angle=0, field_offset=0,
        ))
        labels.append(label(net, x, y))

    title = '''(kicad_sch
  (version 20260306)
  (generator "eeschema")
  (generator_version "10.0")
  (uuid "{root}")
  (paper "A4")
  (title_block
    (title "Lantern Ring Motion/RGB Controller")
    (date "2026-10-12")
    (rev "0.1")
    (comment 1 "Prototype circuit - validate coin-cell current before production")
  )
  (lib_symbols
{symbols}
  )
{elements}
{labels}
{no_connects}
  (sheet_instances (path "/" (page "1")))
)
'''
    OUTPUT.write_text(
        title.format(
            root=ROOT_UUID,
            symbols="\n".join("    " + item.replace("\n", "\n    ") for item in lib_items),
            elements="\n".join("  " + item.replace("\n", "\n  ") for item in elements),
            labels="\n".join("  " + item.replace("\n", "\n  ") for item in labels),
            no_connects="\n".join("  " + item for item in nc_marks),
        ),
        encoding="utf-8",
    )
    symbol_lib = "(kicad_symbol_lib (version 20231120) " \
        '(generator "kicad_symbol_editor")\n'
    for item in lib_items:
        definition = re.sub(
            r'^\(symbol "Lantern:([^"]+)"',
            r'(symbol "\1"',
            item,
            count=1,
        )
        symbol_lib += definition + "\n"
    symbol_lib += ")\n"
    (HERE / "ring_motion_rgb.kicad_sym").write_text(
        symbol_lib, encoding="utf-8"
    )
    (HERE / "sym-lib-table").write_text(
        '(sym_lib_table\n'
        '  (version 7)\n'
        '  (lib (name "Lantern") (type "KiCad") '
        '(uri "${KIPRJMOD}/ring_motion_rgb.kicad_sym") '
        '(options "") (descr "Motion/RGB board project symbols"))\n'
        ')\n',
        encoding="utf-8",
    )
    print(f"Generated {OUTPUT} with {len(component_records)} circuit/contact symbols")


if __name__ == "__main__":
    build()
