import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

from design import (
    HERE, PCB_PATH, artifact_hash, load_parameters, offset_polygon, parse_sexpr,
    pcb_interface, point_inside, source_hash, validate_parameters,
)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.p = load_parameters()
        self.pcb = pcb_interface()

    def test_actual_mono_outline_not_legacy_octagon(self):
        self.assertEqual(len(self.pcb["outline"]), 10)
        self.assertAlmostEqual(self.pcb["width"], 17.78)
        self.assertAlmostEqual(self.pcb["height"], 19.05)
        self.assertAlmostEqual(self.pcb["thickness"], 1.6)
        self.assertEqual(self.pcb["origin"], (136.906, 83.185))

    def test_contact_nets_and_coordinate_handedness(self):
        self.assertEqual(self.pcb["ground_reference"], "TP1")
        self.assertAlmostEqual(self.pcb["ground"][0], -0.0254)
        self.assertAlmostEqual(self.pcb["ground"][1], 7.493)
        self.assertAlmostEqual(self.pcb["positive"][0], 0)
        self.assertAlmostEqual(self.pcb["positive"][1], 0.381)
        self.assertAlmostEqual(self.pcb["positive_radius"], 2.962124)
        self.assertEqual(len(self.pcb["components"]), 6)
        d5 = next(c for c in self.pcb["components"] if c["reference"] == "D5")
        self.assertEqual(d5["angle"], 150.0)

    def test_closed_outline_edges_accounted_for(self):
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in
                       zip(self.pcb["outline"], self.pcb["outline"][1:] + self.pcb["outline"][:1]))) / 2
        self.assertGreater(area, 260)
        self.assertLess(area, 280)
        self.assertTrue(point_inside((0, 0), self.pcb["outline"]))

    def test_offsets_make_real_clearance_not_scaled_outline(self):
        points = self.pcb["outline"]
        grown = offset_polygon(points, self.p["pcb_clearance"])
        inset = offset_polygon(points, -0.45)
        for vertex in points:
            self.assertTrue(point_inside(vertex, grown))
        for vertex in inset:
            self.assertTrue(point_inside(vertex, points))
        for (a, b), (c, d) in zip(zip(points, points[1:] + points[:1]),
                                  zip(grown, grown[1:] + grown[:1])):
            line_distance = abs((b[0] - a[0]) * (a[1] - c[1]) -
                                (a[0] - c[0]) * (b[1] - a[1])) / math.dist(a, b)
            self.assertAlmostEqual(line_distance, self.p["pcb_clearance"])

    def test_pcb_profile_is_not_an_electrical_orientation_key(self):
        pocket = offset_polygon(self.pcb["outline"], self.p["pcb_clearance"])
        self.assertTrue(all(point_inside((-x, -y), pocket) for x, y in self.pcb["outline"]))

    def test_board_net_change_is_not_silently_accepted(self):
        text = PCB_PATH.read_text(encoding="utf-8").replace('"/GND"', '"/WRONG"')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid.kicad_pcb"
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "/GND"):
                pcb_interface(path)

    def test_parser_rejects_malformed_input(self):
        for text in ("", "(", "(a))", "(a)(b)", "a"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_sexpr(text)

    def test_nominal_stack(self):
        result = validate_parameters(self.p, self.pcb)
        self.assertAlmostEqual(result["working_pin_height"], 3.785)
        self.assertAlmostEqual(result["negative_flange"], 4.215)
        self.assertAlmostEqual(result["positive_flange"], 14.985)
        self.assertAlmostEqual(result["pcb_top"], 19.4)
        self.assertAlmostEqual(result["assembly_top"], 22.4)

    def test_all_supported_finger_sizes(self):
        for diameter in (15.5, 16.5, 18.5, 19.5, 22.0):
            with self.subTest(diameter=diameter):
                p = dict(self.p, finger_diameter=diameter)
                validate_parameters(p, self.pcb)

    def test_invalid_designs_fail_explicitly(self):
        cases = {
            "negative dimension": {"finger_diameter": -1},
            "nan": {"pcb_clearance": float("nan")},
            "no preload": {"pin_compression": 0.4},
            "bottomed out": {"pin_compression": 1.2},
            "cell too large": {"battery_clearance": 0.1},
            "PCB hitting tail": {"pcb_bottom": 16.0},
            "tail protruding": {"pin_tail_length": 3},
            "flange not captured": {"deck_floor_top": 14.5},
            "no wiring clearance": {"deck_floor_top": 18.0},
            "thin bayonet": {"body_radius": 17.1},
            "radial collision": {"socket_radius": 14.9},
            "thin carrier": {"deck_pocket_radius": 14.2},
            "deck interference": {"deck_radius": 13.7},
            "disconnected lugs": {"lug_inner_radius": 15.1},
            "bad key": {"lug_widths": [16, 14, 14]},
            "overlapping tracks": {"lock_angle": 100},
            "missing shelf": {"lug_bottom": 2.1},
            "wrong lug count": {"lug_angles": [0, 180]},
            "wire interference": {"wire_channel_diameter": 0.6},
            "battery wire short risk": {"wire_channel_y": 10.2},
            "barrel too large": {"pin_bore_diameter": 1.4},
            "flange falls through": {"pin_bore_diameter": 1.9},
            "flange too large": {"pin_flange_bore_diameter": 1.7},
        }
        for label, changes in cases.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                p = copy.deepcopy(self.p)
                p.update(changes)
                validate_parameters(p, self.pcb)

    def test_checked_in_artifacts_match_source_interface(self):
        report_path = HERE / "generated" / "validation.json"
        self.assertTrue(report_path.exists(), "Run build.ps1 before committing")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["pcb_sha256"], source_hash(PCB_PATH))
        for name, expected in report["source_sha256"].items():
            self.assertEqual(expected, source_hash(HERE / name), "Regenerate CAD after source changes")
        for name, expected in report["artifact_sha256"].items():
            self.assertEqual(expected, artifact_hash(report_path.parent / name))
        self.assertEqual(report["parameters"], self.p)
        self.assertIn("NOT PRINTED", report["physical_test_status"])
        for filename in ("Lantern_Ring_v2.FCStd", "Lantern_Ring_v2.step",
                         "assembly.png", "exploded.png"):
            self.assertGreater((report_path.parent / filename).stat().st_size, 100)
        for part in ("RingBase", "Carrier", "ContactDeck", "Bezel"):
            for extension in ("step", "stl"):
                self.assertGreater((report_path.parent / (part + "." + extension)).stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
