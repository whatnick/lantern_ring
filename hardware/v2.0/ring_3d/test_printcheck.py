"""Print-DRC gates: every committed STL must meet the Elecrow wall-thickness rule."""

import json
import unittest

import numpy as np

from design import HERE, load_parameters
from printcheck import check_stl, mesh_topology, read_stl

GENERATED = HERE / "generated"
PARTS = ("RingBase", "Carrier", "ContactDeck", "Bezel")
CORPS = ("will", "fear", "rage", "avarice", "hope", "compassion", "love", "life")


def box_triangles(size, hollow=0.0):
    """Closed, outward-wound triangles of an axis-aligned box."""
    x, y, z = size
    v = np.array([[0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],
                  [0, 0, z], [x, 0, z], [x, y, z], [0, y, z]], float)
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return np.array([[v[a], v[b], v[c]] for a, b, c in faces])


def write_ascii_stl(path, triangles):
    lines = ["solid t"]
    for tri in triangles:
        n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        n = n / np.linalg.norm(n)
        lines.append("facet normal {} {} {}\nouter loop".format(*n))
        lines.extend("vertex {} {} {}".format(*p) for p in tri)
        lines.append("endloop\nendfacet")
    lines.append("endsolid t")
    path.write_text("\n".join(lines), encoding="utf-8")


class CheckerTests(unittest.TestCase):
    def check(self, size):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "box.stl"
            write_ascii_stl(path, box_triangles(size))
            return check_stl(path, 1.05)

    def test_thin_plate_fails(self):
        report = self.check((10, 10, 0.6))
        self.assertFalse(report["passes"])
        self.assertAlmostEqual(report["min_thickness_mm"], 0.6, places=2)

    def test_thick_block_passes(self):
        report = self.check((10, 10, 1.2))
        self.assertTrue(report["passes"], report)

    def test_open_mesh_is_rejected(self):
        tris = box_triangles((10, 10, 5))[:-2]
        self.assertFalse(mesh_topology(tris)[0])


class GeneratedPartsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.limit = load_parameters()["min_printed_wall"]
        cls.report = json.loads((GENERATED / "validation.json").read_text(encoding="utf-8"))

    def test_rule_is_above_elecrow_flag(self):
        self.assertGreaterEqual(self.limit, 1.0)

    def test_cassette_parts_meet_wall_rule(self):
        for part in PARTS:
            with self.subTest(part=part):
                report = check_stl(GENERATED / (part + ".stl"), self.limit)
                self.assertTrue(report["passes"], report)
                self.assertGreaterEqual(report["min_thickness_mm"], self.limit)
                self.assertTrue(self.report["print_check"]["parts"][part]["passes"])

    def test_crowns_meet_wall_rule(self):
        crowns = json.loads((GENERATED / "crowns" / "crowns.json").read_text(encoding="utf-8"))
        relief = (crowns["crown"]["relief"], crowns["crown"]["relief_min_width"])
        for key in CORPS:
            with self.subTest(corps=key):
                report = check_stl(GENERATED / "crowns" / "Crown_{}.stl".format(key),
                                   self.limit, emboss=relief)
                self.assertTrue(report["passes"], report)
                self.assertEqual(len(read_stl(GENERATED / "crowns" / "Crown_{}.stl".format(key)))
                                 > 0, True)


if __name__ == "__main__":
    unittest.main()
