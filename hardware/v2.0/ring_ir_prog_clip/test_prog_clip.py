"""Standard-library checks for the ring_pcb_IR programming clip.

Run from the repository root:

    python -m unittest discover -s hardware\\v2.0\\ring_ir_prog_clip -p test_prog_clip.py

The checks parse the KiCad text files directly, so they are independent of the
pcbnew-based generator.  They do not prove physical fit or contact quality.
"""

import hashlib
import json
import math
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.normpath(os.path.join(HERE, "..", "ring_pcb_IR", "ring_pcb_IR.kicad_pcb"))
PROBE = os.path.join(HERE, "probe", "ring_ir_prog_probe.kicad_pcb")
ANVIL = os.path.join(HERE, "anvil", "ring_ir_prog_anvil.kicad_pcb")
FENCE = os.path.join(HERE, "fence", "ring_ir_prog_fence.kicad_pcb")
ORIGIN = (150.0, 100.0)
TOL = 0.002


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def blocks(text, key):
    out, i = [], 0
    pattern = re.compile(r"\(" + re.escape(key.strip()) + (r"\s" if key.endswith(" ") else ""))
    while True:
        m = pattern.search(text, i)
        if not m:
            return out
        j = m.start()
        depth = 0
        for k in range(j, len(text)):
            if text[k] == "(":
                depth += 1
            elif text[k] == ")":
                depth -= 1
                if depth == 0:
                    break
        out.append(text[j:k + 1])
        i = k + 1


def footprints(path):
    """Return {ref: {"at": (x, y), "rot": deg, "layer": str, "pads": {num: ((x, y), net, size)}, "crtyd": [...]}}"""
    result = {}
    for fp in blocks(read(path), "footprint "):
        head = fp[:fp.find("(pad ")] if "(pad " in fp else fp
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", head)
        x, y, rot = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
        ref = re.search(r'\(property "Reference" "([^"]+)"', fp) or re.search(r'\(fp_text reference "([^"]+)"', fp)
        layer = re.search(r'\(layer "([^"]+)"\)', head).group(1)
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        pads = {}
        for pad in blocks(fp, "pad "):
            num = re.match(r'\(pad "([^"]*)"', pad).group(1)
            pat = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pad)
            px, py = float(pat.group(1)), float(pat.group(2))
            net = re.search(r'\(net (?:\d+ )?"([^"]*)"\)', pad)
            size = re.search(r"\(size ([-\d.]+) ([-\d.]+)\)", pad)
            pads[num] = ((x + px * c + py * s, y - px * s + py * c), net.group(1) if net else "",
                         (float(size.group(1)), float(size.group(2))))
        crtyd = []
        for shape in blocks(fp, "fp_"):
            if '"F.CrtYd"' in shape:
                for px, py in re.findall(r"\((?:start|end|center|mid) ([-\d.]+) ([-\d.]+)\)", shape):
                    px, py = float(px), float(py)
                    crtyd.append((x + px * c + py * s, y - px * s + py * c))
        result[ref.group(1)] = {"at": (x, y), "rot": rot, "layer": layer, "pads": pads, "crtyd": crtyd}
    return result


def edge_items(path):
    text = read(path)
    segments, polys = [], []
    for kind in ("gr_line", "gr_arc", "gr_poly"):
        for item in blocks(text, kind + " "):
            if '"Edge.Cuts"' not in item:
                continue
            if kind == "gr_poly":
                polys.append([(float(a), float(b)) for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", item)])
            else:
                pts = re.findall(r"\((start|mid|end) ([-\d.]+) ([-\d.]+)\)", item)
                segments.append([(float(a), float(b)) for _, a, b in pts])
    return segments, polys


def loops(segments):
    """Chain Edge.Cuts segments into closed loops (point lists)."""
    remaining = [list(s) for s in segments]
    out = []
    while remaining:
        loop = remaining.pop(0)
        changed = True
        while changed:
            changed = False
            for s in remaining:
                if math.dist(s[0], loop[-1]) < 1e-3:
                    loop += s[1:]
                elif math.dist(s[-1], loop[-1]) < 1e-3:
                    loop += list(reversed(s))[1:]
                else:
                    continue
                remaining.remove(s)
                changed = True
                break
        out.append(loop)
    return out


def bbox(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def inside(poly, x, y):
    hit = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    if ax * ax + ay * ay < 1e-12:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay)))
    return math.dist(p, (a[0] + t * ax, a[1] + t * ay))


class ClipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "parameters.json"), encoding="utf-8") as handle:
            cls.params = json.load(handle)
        cls.target = footprints(TARGET)
        cls.probe = footprints(PROBE)
        cls.anvil = footprints(ANVIL)
        _, polys = edge_items(TARGET)
        cls.outline = polys[0]
        origin = cls.target[cls.params["dut"]["origin_test_point"]]["pads"]["1"][0]
        cls.uv = staticmethod(lambda x, y: (ORIGIN[0] - (x - origin[0]), ORIGIN[1] + (y - origin[1])))

    def test_target_nets_unchanged(self):
        for ref, net in self.params["dut"]["expected_nets"].items():
            self.assertEqual(self.target[ref]["pads"]["1"][1], net, ref)

    def test_each_pogo_lands_on_its_mirrored_test_pad(self):
        for ref in self.params["dut"]["probe_test_points"]:
            (tx, ty), net, size = self.target[ref]["pads"]["1"]
            self.assertEqual(self.target[ref]["layer"], "B.Cu")
            pogo = self.probe["P" + ref[2:]]["pads"]["1"]
            ex, ey = self.uv(tx, ty)
            self.assertLess(math.dist(pogo[0], (ex, ey)), TOL, ref)
            expected = net if net in self.params["isp_header"]["pins"].values() else "unconnected-"
            self.assertTrue(pogo[1].lstrip("/").startswith(expected), (ref, pogo[1]))

    def test_pogo_pitch_leaves_pad_and_tip_margin(self):
        pogos = [self.probe["P" + r[2:]]["pads"]["1"] for r in self.params["dut"]["probe_test_points"]]
        clearance = min(math.dist(a[0], b[0]) - a[2][0] / 2 - b[2][0] / 2
                        for i, a in enumerate(pogos) for b in pogos[i + 1:])
        self.assertGreaterEqual(clearance, 0.2)
        self.assertGreater(self.params["pogo"]["drill"], self.params["pogo"]["barrel_diameter"])

    def test_isp_header_is_standard_avr_isp6(self):
        header = self.probe["J1"]["pads"]
        for pin, net in self.params["isp_header"]["pins"].items():
            self.assertEqual(header[pin][1], "/" + net, pin)
        self.assertEqual(self.params["isp_header"]["functions"],
                         {"PB0": "MOSI", "PB1": "MISO", "PB2": "SCK", "PB5": "RESET"})
        # Standard ISP-6 geometry: odd and even pins in two rows 2.54 mm apart.
        self.assertAlmostEqual(math.dist(header["1"][0], header["2"][0]), 2.54, places=3)
        self.assertAlmostEqual(math.dist(header["1"][0], header["5"][0]), 5.08, places=3)

    def test_ground_reaches_both_boards(self):
        self.assertEqual(self.probe["J2"]["pads"]["1"][1], "/GND")
        self.assertEqual(self.anvil["P8"]["pads"]["1"][1], "/GND")
        self.assertEqual(self.anvil["J1"]["pads"]["1"][1], "/GND")

    def test_anvil_pad_sits_inside_exposed_front_ground_bar(self):
        (cx, cy), _, (w, h) = self.anvil["P8"]["pads"]["1"]
        bar = self.target["TP8"]["pads"]["1"][0]
        text = read(TARGET)
        masks = []
        for zone in blocks(text, "zone "):
            if '(layer "F.Mask")' in zone:
                pts = [(float(a), float(b)) for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", zone)]
                if pts and inside(pts, *bar):
                    masks.append(pts)
        self.assertTrue(masks, "front mask opening around TP8 not found")
        for du in (-w / 2, w / 2):
            for dv in (-h / 2, h / 2):
                x = self.target["TP3"]["pads"]["1"][0][0] - (cx + du - ORIGIN[0])
                y = self.target["TP3"]["pads"]["1"][0][1] + (cy + dv - ORIGIN[1])
                self.assertTrue(inside(self.outline, x, y), (x, y))
                self.assertTrue(any(inside(m, x, y) for m in masks), (x, y))

    def test_anvil_window_clears_every_front_component(self):
        segments, _ = edge_items(ANVIL)
        windows = sorted(loops(segments), key=lambda l: (bbox(l)[2] - bbox(l)[0]) * (bbox(l)[3] - bbox(l)[1]))
        window = bbox(windows[0])
        for ref, fp in self.target.items():
            if fp["layer"] != "F.Cu" or ref.startswith("TP"):
                continue
            for x, y in fp["crtyd"]:
                u, v = self.uv(x, y)
                self.assertTrue(window[0] < u < window[2] and window[1] < v < window[3], (ref, u, v))
        # The board still supports the target edges outside the window.
        target_uv = [self.uv(x, y) for x, y in self.outline]
        tb = bbox(target_uv)
        self.assertGreaterEqual(window[0] - tb[0], self.params["anvil"]["min_rail_contact"])
        self.assertGreaterEqual(tb[2] - window[2], self.params["anvil"]["min_rail_contact"])

    def test_fence_pocket_clears_target_outline(self):
        segments, _ = edge_items(FENCE)
        pocket = min(loops(segments), key=lambda l: (bbox(l)[2] - bbox(l)[0]))
        clearance = self.params["anvil"]["pocket_clearance"]
        for x, y in self.outline:
            u, v = self.uv(x, y)
            self.assertTrue(inside(pocket, u, v))
            gap = min(seg_dist((u, v), pocket[i - 1], pocket[i]) for i in range(len(pocket)))
            self.assertGreaterEqual(gap, clearance - TOL)
            self.assertLess(gap, clearance / math.sin(math.radians(67.5 / 2)) + 0.05)

    def test_reports_clean_and_unmeasured_inputs_declared(self):
        with open(os.path.join(HERE, "generated", "validation.json"), encoding="utf-8") as handle:
            result = json.load(handle)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(all(v == 0 for v in result["violations"].values()))
        declared = [k for k in ("clip_kit", "pogo") if not self.params[k]["measured"]]
        self.assertEqual(sorted(result["unmeasured"]), sorted(declared))

    def test_validation_hashes_match_sources(self):
        def digest(path):
            with open(path, "rb") as handle:
                return hashlib.sha256(handle.read().replace(b"\r\n", b"\n")).hexdigest()

        with open(os.path.join(HERE, "generated", "validation.json"), encoding="utf-8") as handle:
            result = json.load(handle)
        self.assertEqual(result["target_sha256"], digest(TARGET))
        for name, expected in result["sources_sha256"].items():
            self.assertEqual(expected, digest(os.path.join(HERE, *name.split("/"))), name)
        self.assertIn("no physical fit", result["scope"])


if __name__ == "__main__":
    unittest.main()
