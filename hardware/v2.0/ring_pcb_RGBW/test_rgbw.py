"""Portable checks of saved electrical files, the fixed clip interface and evidence."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
GEN = HERE / "generated"
PCB = HERE / "ring_pcb_RGBW.kicad_pcb"
IR = HERE.parent / "ring_pcb_IR" / "ring_pcb_IR.kicad_pcb"
spec = importlib.util.spec_from_file_location(
    "_saved_pcb", HERE.parent / "ring_ir_prog_clip" / "test_prog_clip.py")
saved = importlib.util.module_from_spec(spec)
spec.loader.exec_module(saved)


def digest(path):
    data = path.read_bytes()
    if path.suffix not in (".png", ".pdf", ".FCStd"):
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def mask_windows(text):
    result = []
    for zone in saved.blocks(text, "zone "):
        layers = re.search(r'\((?:layer|layers)\s+([^)]*)\)', zone).group(1)
        mask = "F.Mask" if '"F.Mask"' in layers else "B.Mask" if '"B.Mask"' in layers else None
        if mask:
            polygon = saved.blocks(zone, "polygon ")[0]
            pts = [(float(x), float(y)) for x, y in re.findall(
                r"\(xy ([-\d.]+) ([-\d.]+)\)", polygon)]
            result.append((mask, pts))
    return sorted(result)


def intersects_polygon(a, b, radius, poly):
    if saved.inside(poly, *a) or saved.inside(poly, *b):
        return True
    for c, d in zip(poly, poly[1:] + poly[:1]):
        ux, uy = b[0] - a[0], b[1] - a[1]
        vx, vy = d[0] - c[0], d[1] - c[1]
        det = ux * vy - uy * vx
        if abs(det) > 1e-12:
            wx, wy = c[0] - a[0], c[1] - a[1]
            t, u = (wx * vy - wy * vx) / det, (wx * uy - wy * ux) / det
            if 0 <= t <= 1 and 0 <= u <= 1:
                return True
        if min(saved.seg_dist(a, c, d), saved.seg_dist(b, c, d),
               saved.seg_dist(c, a, b), saved.seg_dist(d, a, b)) <= radius:
            return True
    return False


class RGBWTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PCB.read_text()
        cls.fps = saved.footprints(PCB)
        cls.original = saved.footprints(IR)
        cls.netlist = ET.parse(GEN / "netlist.xml").getroot()
        cls.nets = {(n.attrib["ref"], n.attrib["pin"]): net.attrib["name"]
                    for net in cls.netlist.findall("nets/net") for n in net.findall("node")}

    def test_exact_native_outline_thickness_and_programming_contacts(self):
        self.assertEqual(saved.edge_items(PCB), saved.edge_items(IR))
        self.assertEqual(re.search(r"\(thickness ([\d.]+)\)", self.text).group(1),
                         re.search(r"\(thickness ([\d.]+)\)", IR.read_text()).group(1))
        source_blocks = {re.search(r'\(property "Reference" "([^"]+)"', b).group(1): b
                         for b in saved.blocks(IR.read_text(), "footprint ")}
        target_blocks = {re.search(r'\(property "Reference" "([^"]+)"', b).group(1): b
                         for b in saved.blocks(self.text, "footprint ")}
        for n in range(1, 10):
            ref = "TP%d" % n
            for key in ("at", "rot", "layer", "pads"):
                self.assertEqual(self.fps[ref][key], self.original[ref][key], (ref, key))
            for key in ("layers ", "size ", "roundrect_rratio ", "solder_mask_margin ", "drill "):
                a = saved.blocks(saved.blocks(source_blocks[ref], "pad ")[0], key)
                b = saved.blocks(saved.blocks(target_blocks[ref], "pad ")[0], key)
                self.assertEqual([" ".join(s.split()) for s in a],
                                 [" ".join(s.split()) for s in b], (ref, key))
            self.assertEqual(re.match(r'\(pad "[^"]+" (\w+) (\w+)',
                                      saved.blocks(source_blocks[ref], "pad ")[0]).groups(),
                             re.match(r'\(pad "[^"]+" (\w+) (\w+)',
                                      saved.blocks(target_blocks[ref], "pad ")[0]).groups())
        self.assertEqual(mask_windows(self.text), mask_windows(IR.read_text()))

    def test_actual_schematic_and_board_have_four_independent_limited_channels(self):
        for i, (colour, gpio, anode, cathode) in enumerate(
                (("R", "PB0", "1", "8"), ("G", "PB1", "2", "7"),
                 ("B", "PB4", "3", "6"), ("W", "PB2", "4", "5")), 1):
            expected = {("D1", anode): "VCC", ("D1", cathode): colour + "_K",
                        ("R%d" % i, "1"): colour + "_K", ("R%d" % i, "2"): colour + "_D",
                        ("Q%d" % i, "1"): colour + "_G", ("Q%d" % i, "2"): "GND",
                        ("Q%d" % i, "3"): colour + "_D",
                        ("R%d" % (i + 4), "1"): gpio, ("R%d" % (i + 4), "2"): colour + "_G",
                        ("R%d" % (i + 8), "1"): colour + "_G", ("R%d" % (i + 8), "2"): "GND"}
            for (ref, pin), net in expected.items():
                self.assertEqual(self.nets[(ref, pin)], net)
                self.assertEqual(self.fps[ref]["pads"][pin][1], net)
        for ref, pin, net in (("U1", "1", "PB5"), ("U1", "2", "PB3"),
                              ("U1", "5", "PB4"), ("U1", "8", "GND"),
                              ("U1", "11", "PB0"), ("U1", "12", "PB1"),
                              ("U1", "14", "PB2"), ("U1", "15", "VCC"),
                              ("U1", "21", "GND"), ("JP1", "1", "PB3"),
                              ("JP1", "2", "GND")):
            self.assertEqual(self.nets[(ref, pin)], net)
            self.assertEqual(self.fps[ref]["pads"][pin][1], net)

    def test_no_foreign_net_routes_in_exposed_contacts(self):
        nets = {int(code): name for code, name in re.findall(r'\(net (\d+) "([^"]*)"\)', self.text)}
        for kind in ("segment ", "via "):
            for item in saved.blocks(self.text, kind):
                net = re.search(r'\(net (?:(\d+)|"([^"]+)")\)', item)
                name = net.group(2) if net.group(2) is not None else nets[int(net.group(1))]
                if kind == "via ":
                    at = re.search(r"\(at ([\d.-]+) ([\d.-]+)\)", item)
                    a = b = tuple(float(x) for x in at.groups())
                    radius = float(re.search(r"\(size ([\d.]+)\)", item).group(1)) / 2
                    layers = ("F.Mask", "B.Mask")
                else:
                    layer = re.search(r'\(layer "([^"]+)"\)', item).group(1)
                    if layer not in ("F.Cu", "B.Cu"):
                        continue
                    a = tuple(float(x) for x in re.search(r"\(start ([\d.-]+) ([\d.-]+)\)", item).groups())
                    b = tuple(float(x) for x in re.search(r"\(end ([\d.-]+) ([\d.-]+)\)", item).groups())
                    radius = float(re.search(r"\(width ([\d.]+)\)", item).group(1)) / 2
                    layers = ("F.Mask",) if layer == "F.Cu" else ("B.Mask",)
                for layer, poly in mask_windows(self.text):
                    if layer in layers and name != ("GND" if layer == "F.Mask" else "VCC"):
                        self.assertFalse(intersects_polygon(a, b, radius, poly), (name, a, b, layer))

    def test_final_reports_and_provenance_match_current_saved_files(self):
        validation = json.loads((GEN / "validation.json").read_text())
        self.assertEqual(validation["status"], "passed")
        for path, sha in validation["files_sha256"].items():
            self.assertEqual(digest(HERE / Path(*path.split("/"))), sha, path)
        for filename in ("erc.json", "drc.json"):
            report = json.loads((GEN / filename).read_text())
            self.assertIn("violations" if filename == "drc.json" else "sheets", report)
            findings = report.get("violations", []) + [
                v for s in report.get("sheets", []) for v in s["violations"]]
            if filename == "drc.json":
                self.assertIn("unconnected_items", report)
                self.assertIn("schematic_parity", report)
                findings += report["unconnected_items"] + report["schematic_parity"]
            self.assertEqual(findings, [], filename)
        design = json.loads((GEN / "design.json").read_text())
        self.assertEqual(design["status"], "routed")
        self.assertEqual(design["source_board_sha256"], digest(IR))
        self.assertEqual(design["generator_sha256"], digest(HERE / "generate.py"))
        self.assertEqual(design["parameters_sha256"], digest(HERE / "parameters.json"))
        self.assertEqual(design["routing"]["board_sha256"], digest(PCB))
        cad = json.loads((GEN / "cad-validation.json").read_text())
        self.assertTrue(cad["valid_solids"])
        self.assertTrue(cad["component_window_screen_passed"])
        self.assertEqual(cad["step_sha256"], digest(GEN / "populated.step"))


if __name__ == "__main__":
    unittest.main()
