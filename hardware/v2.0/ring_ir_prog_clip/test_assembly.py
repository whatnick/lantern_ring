"""Portable regression checks for the album reconstruction and FreeCAD evidence."""
import json
import unittest

import assembly_interface as interface


class AssemblyTests(unittest.TestCase):
    def test_variant_pitch_and_barrel_clearance(self):
        cfg = interface.load()
        self.assertEqual([v["pitch_mm"] for v in cfg["variants"]], [1.27, 2.0, 2.54, 3.05])
        for variant in cfg["variants"][:3]:
            points = interface.stock_grid(variant["pitch_mm"])
            self.assertEqual(len(points), 12)
            prefix = "fine_" if variant["pins"] == "fine" else ""
            hole = cfg["estimated"][prefix + "pogo_barrel_diameter"] + 0.13
            self.assertGreater(variant["pitch_mm"], hole)

    def test_standard_254_does_not_match_ir(self):
        result = interface.compatibility(2.54, 0.9, 0.15)
        self.assertFalse(result["direct_isp_compatible"])
        self.assertFalse(result["signals_fully_contained"])
        outer = next(p for p in result["signal_contacts"] if p["ref"] == "TP1")
        self.assertAlmostEqual(abs(outer["pin_uv"][0] - outer["pad_uv"][0]), 0.51)

    def test_custom_signal_centres(self):
        result = interface.compatibility(3.05, 0.9, 0)
        self.assertTrue(result["signals_fully_contained"])
        self.assertTrue(all(p["offset_mm"] == 0 for p in result["signal_contacts"]))
        self.assertFalse(result["direct_isp_compatible"])  # still needs VCC/GND adapter

    def test_report_and_roundtrip_artifacts(self):
        out = interface.HERE / "generated" / "assembly"
        report = json.loads((out / "validation.json").read_text())
        for path, expected in report["source_sha256"].items():
            self.assertEqual(interface.sha256(interface.HERE / path), expected, path)
        for path, expected in report["artifact_sha256"].items():
            self.assertEqual(interface.artifact_sha256(out / path), expected, path)
        self.assertEqual(report["pcb_sha256"],
                         interface.sha256(interface.HERE / ".." / "ring_pcb_IR" / "ring_pcb_IR.kicad_pcb"))
        self.assertEqual(set(report["variants"]), {v["id"] for v in interface.load()["variants"]})
        for name, variant in report["variants"].items():
            self.assertFalse(variant["static_collisions"])
            self.assertFalse(variant["opening"]["collisions"])
            self.assertEqual(len(variant["opening"]["samples"]), 13)
            self.assertGreater(variant["details"]["working_compression_mm"], 0)
            self.assertLess(variant["details"]["working_compression_mm"], variant["details"]["travel_mm"])
            for filename in ("clip.FCStd", "clip.step", "meshes.json"):
                self.assertTrue((out / name / filename).is_file())
        contact = report["custom_ir_contact"]["signal_contacts"]
        self.assertTrue(all(p["freecad_tip_overlap_fraction"] == 1 for p in contact))
        stock = next(r for r in report["stock_ir_compatibility"] if r["pitch_mm"] == 2.54)
        self.assertFalse(all(p["freecad_axis_on_pad"] for p in stock["signal_contacts"]))

    def test_photograph_provenance(self):
        images = interface.HERE / "images"
        import hashlib
        for item in json.loads((images / "sources.json").read_text()):
            self.assertEqual(hashlib.sha256((images / item["file"]).read_bytes()).hexdigest(),
                             item["sha256"])

    def test_actual_kicad_board_layers_and_pitch(self):
        out = interface.HERE / "generated" / "assembly"
        layers = json.loads((out / "ir_board_layers.json").read_text())
        self.assertEqual(layers["board_sha256"],
                         interface.sha256(interface.HERE / ".." / "ring_pcb_IR" / "ring_pcb_IR.kicad_pcb"))
        self.assertEqual(layers["exporter_sha256"], interface.sha256(interface.HERE / "export_ir_visual.py"))
        self.assertEqual(layers["measured_from_file"]["x_mm"], [3.05, 3.05])
        self.assertEqual(layers["measured_from_file"]["y_mm"], [3.05])
        ox, oy = layers["origin_xy_mm"]
        for ref, pad in interface.ir_contacts().items():
            actual = layers["pads"][ref]
            x, y = actual["xy_mm"]
            self.assertAlmostEqual(ox - x, pad["uv"][0], places=6)
            self.assertAlmostEqual(y - oy, pad["uv"][1], places=6)
            self.assertEqual(actual["net"], pad["net"])
        meshes = json.loads((out / "ir_custom" / "meshes.json").read_text())
        visuals = [p for p in meshes if p.get("visual_surface_only") and p["name"].startswith("PCB_")]
        self.assertEqual(len(visuals), 6)
        self.assertTrue(all(p["area_mm2"] > 0 for p in visuals))

    def test_actual_clip_layers_and_ground_path(self):
        out = interface.HERE / "generated" / "assembly"
        data = json.loads((out / "clip_board_layers.json").read_text())
        self.assertEqual(data["exporter_sha256"], interface.sha256(interface.HERE / "export_ir_visual.py"))
        for name, board in data["boards"].items():
            path = interface.HERE / name / ("ring_ir_prog_" + name + ".kicad_pcb")
            self.assertEqual(board["board_sha256"], interface.sha256(path))
        from test_prog_clip import footprints
        for name, board in data["boards"].items():
            expected = footprints(str(interface.HERE / name / ("ring_ir_prog_" + name + ".kicad_pcb")))
            for p in board["pads"]:
                position, net, _ = expected[p["ref"]]["pads"][p["number"]]
                self.assertEqual(net, p["net"])
                for actual, target in zip(p["xy_mm"], position):
                    self.assertAlmostEqual(actual, target, places=5)
        probe = data["boards"]["probe"]["pads"]
        anvil = data["boards"]["anvil"]["pads"]
        for ref in ("J1", "J2"):
            ground = [p for p in probe if p["ref"] == ref and p["net"] == "/GND"]
            self.assertEqual(len(ground), 1)
        self.assertEqual({p["net"] for p in anvil}, {"/GND"})
        self.assertEqual({p["ref"] for p in anvil}, {"P8", "J1"})
        meshes = json.loads((out / "ir_custom" / "meshes.json").read_text())
        for part in ("Probe", "Guide", "Anvil", "Fence"):
            self.assertTrue(any(p["name"].startswith(part + "PCB_") for p in meshes))
        self.assertTrue(all(p["surface_normal_z"] in (-1, 1) for p in meshes
                            if p.get("visual_surface_only")))


if __name__ == "__main__":
    unittest.main()
