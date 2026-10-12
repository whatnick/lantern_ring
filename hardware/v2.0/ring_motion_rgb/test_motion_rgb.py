"""Mechanical and programming-clip interface checks for the RGB board."""

import math
import os
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RING_3D = ROOT / "hardware" / "v2.0" / "ring_3d"
CLIP_TESTS = ROOT / "hardware" / "v2.0" / "ring_ir_prog_clip"
sys.path.insert(0, str(RING_3D))
sys.path.insert(0, str(CLIP_TESTS))

from design import pcb_interface
from test_prog_clip import footprints


PCB = HERE / "ring_motion_rgb.kicad_pcb"
MONO_PCB = ROOT / "hardware" / "v2.0" / "ring_mono" / "ring_mono.kicad_pcb"
IR_PCB = ROOT / "hardware" / "v2.0" / "ring_pcb_IR" / "ring_pcb_IR.kicad_pcb"
ORIGIN = (136.906, 83.185)
CLIP_NETS = {
    "P1": "PB0",
    "P2": "PB1",
    "P3": "PB2",
    "P4": "PB3",
    "P5": "PB4",
    "P6": "PB5",
    "P9": "VCC",
    "TP8": "/GND",
}
IR_CLIP_REFS = {
    "P1": "TP1",
    "P2": "TP2",
    "P3": "TP3",
    "P4": "TP4",
    "P5": "TP5",
    "P6": "TP6",
    "P9": "TP9",
    "TP8": "TP8",
}

def canonical_outline(vertices):
    points = [tuple(round(value, 6) for value in vertex) for vertex in vertices]
    candidates = []
    for sequence in (points, list(reversed(points))):
        for index in range(len(sequence)):
            candidates.append(tuple(sequence[index:] + sequence[:index]))
    return min(candidates)


@unittest.skipUnless(PCB.is_file(), "Run generate_board.py first")
class MotionRgbInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = footprints(PCB)
        cls.ir = footprints(IR_PCB)
        cls.mono = pcb_interface(MONO_PCB)
        cls.new = pcb_interface(PCB)

    def test_outline_and_battery_contact_interface_match_mono(self):
        self.assertEqual(
            canonical_outline(self.new["outline"]),
            canonical_outline(self.mono["outline"]),
        )
        self.assertEqual(self.new["origin"], self.mono["origin"])
        self.assertEqual(self.new["positive"], self.mono["positive"])
        self.assertAlmostEqual(
            self.new["positive_radius"], self.mono["positive_radius"], places=6
        )
        self.assertEqual(self.new["ground"], self.mono["ground"])
        self.assertEqual(self.board["TP1"]["pads"]["1"][1], "/GND")
        self.assertEqual(self.board["TP2"]["pads"]["1"][1], "/GND")
        self.assertAlmostEqual(self.new["thickness"], 1.6)

    def test_clip_pads_use_exact_ir_board_locations_nets_and_layers(self):
        for ref, expected_net in CLIP_NETS.items():
            new_pad, new_net, _ = self.board[ref]["pads"]["1"]
            ir_ref = IR_CLIP_REFS[ref]
            ir_pad, ir_net, _ = self.ir[ir_ref]["pads"]["1"]
            new_origin = self.board["P3"]["pads"]["1"][0]
            ir_origin = self.ir["TP3"]["pads"]["1"][0]
            self.assertEqual(new_net, expected_net, ref)
            expected_layer = "F.Cu" if ref == "TP8" else "B.Cu"
            self.assertEqual(self.board[ref]["layer"], expected_layer, ref)
            self.assertLess(
                math.dist(
                    (new_pad[0] - new_origin[0], new_pad[1] - new_origin[1]),
                    (ir_pad[0] - ir_origin[0], ir_pad[1] - ir_origin[1]),
                ),
                0.002,
                ref,
            )

    def test_ground_anvil_and_mask_opening_remain_clip_compatible(self):
        self.assertEqual(self.board["TP8"]["layer"], "F.Cu")
        self.assertEqual(self.board["TP8"]["pads"]["1"][1], "/GND")
        self.assertEqual(self.board["TP1"]["pads"]["1"][1], "/GND")
        self.assertEqual(self.board["TP2"]["pads"]["1"][1], "/GND")

    def test_board_has_required_motion_rgb_footprints(self):
        for ref in ("U1", "U2", "D1", "J1", "J2", "J3", "R1", "R2", "R3",
                    "C1", "C2", "R4"):
            self.assertIn(ref, self.board)
        for ref in ("TP1", "TP2", "TP8", "P1", "P2", "P3", "P4",
                    "P5", "P6", "P9"):
            self.assertIn(ref, self.board)

    def test_rgb_led_and_sensor_pads_follow_manufacturer_pinouts(self):
        expected_led = {"1": "LED_R", "2": "/GND", "3": "LED_G", "4": "LED_B"}
        expected_accelerometer = {
            "1": "/GND", "3": "ACC_SCL", "4": "VCC", "5": "/GND",
            "6": "ACC_SDA", "9": "ACC_INT", "10": "VCC",
            "11": "VCC", "12": "/GND",
        }
        for ref, expected in (("D1", expected_led), ("U2", expected_accelerometer)):
            for number, net in expected.items():
                self.assertEqual(self.board[ref]["pads"][number][1], net, ref + "." + number)

    def test_mcu_native_usi_isp_pins_match_the_clip_contract(self):
        expected = {
            "1": "ACC_INT",
            "2": "PWM_B",
            "3": "ACC_SCL",
            "4": "PWM_G",
            "5": "PWM_R",
            "8": "/GND",
            "9": "VCC",
            "11": "PB0",
            "12": "PB1",
            "13": "PB5",
            "14": "PB2",
            "15": "ACC_SDA",
            "16": "PB4",
            "20": "PB3",
            "21": "/GND",
        }
        for number, net in expected.items():
            self.assertEqual(
                self.board["U1"]["pads"][number][1], net, "U1." + number
            )


if __name__ == "__main__":
    unittest.main()
