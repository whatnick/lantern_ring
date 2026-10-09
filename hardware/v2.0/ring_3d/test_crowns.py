"""Tool-neutral checks for the low-profile Lantern Corps crowns (crowns.py output)."""

import json
import math
import unittest

from design import HERE, PCB_PATH, artifact_hash, load_parameters, source_hash

CROWNS = HERE / "generated" / "crowns"
LOGOS = HERE / "logos" / "logos.json"
CORPS = ("will", "fear", "rage", "avarice", "hope", "compassion", "love", "life")


class CrownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((CROWNS / "crowns.json").read_text(encoding="utf-8"))
        cls.logos = json.loads(LOGOS.read_text(encoding="utf-8"))["logos"]

    def test_report_matches_sources(self):
        self.assertEqual(self.report["pcb_sha256"], source_hash(PCB_PATH))
        self.assertEqual(self.report["logos_sha256"], source_hash(LOGOS))
        for name, digest in self.report["source_sha256"].items():
            self.assertEqual(digest, source_hash(HERE / name), name)
        self.assertEqual(self.report["parameters"], load_parameters())

    def test_artifacts_match_report(self):
        expected = {"Crown_{}.{}".format(key, ext) for key in CORPS for ext in ("step", "stl")}
        self.assertEqual(set(self.report["artifact_sha256"]), expected)
        for name, digest in self.report["artifact_sha256"].items():
            self.assertEqual(digest, artifact_hash(CROWNS / name), name)

    def test_every_corps_has_logo_svg_and_crown(self):
        self.assertEqual(tuple(self.logos), CORPS)
        self.assertEqual(tuple(self.report["crowns"]), CORPS)
        for key in CORPS:
            self.assertTrue((HERE / "logos" / (key + ".svg")).is_file(), key)

    def test_logos_fit_inside_bezel(self):
        radius = self.report["parameters"]["screw_radius"] + self.report["parameters"]["screw_post_radius"]
        for key, logo in self.logos.items():
            reach = max(math.hypot(x, y) for loop in logo["loops"] for x, y in loop)
            # Logos are clipped to the bezel; avarice bar tips are the only overhang.
            self.assertLess(reach, radius + 0.3, key)
            self.assertGreater(logo["area_mm2"], 20, key)

    def test_low_profile_versus_v1_emblem(self):
        levels = self.report["levels"]
        self.assertAlmostEqual(levels["top"] - levels["pcb_top"], 2.3, places=3)
        self.assertLess(levels["top"] - levels["pcb_top"],
                        self.report["v1_logo_reference_mm"]["v1_logo_cap_height"] / 2)
        for key, crown in self.report["crowns"].items():
            self.assertLessEqual(crown["top_above_pcb_mm"], 2.5, key)
            self.assertGreaterEqual(crown["led_clearance_mm"], self.report["crown"]["led_clearance"] - 1e-6, key)
            self.assertAlmostEqual(crown["diameter_mm"], 23.4, key)
            self.assertGreater(crown["volume_mm3"], 400, key)

    def test_lens_and_relief_layers_are_printable(self):
        crown = self.report["crown"]
        # 0.2 mm layers: lens is two layers, relief at least three.
        self.assertGreaterEqual(crown["lens"], 0.4)
        self.assertGreaterEqual(crown["relief"], 0.6)

    def test_physical_status_is_explicit(self):
        self.assertTrue(self.report["physical_test_status"].startswith("NOT PRINTED"))


if __name__ == "__main__":
    unittest.main()
