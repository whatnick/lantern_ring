"""Independently check the saved Fritzing cable graph against the KiCad boards."""

import hashlib
from html.parser import HTMLParser
import json
import pathlib
import re
import unittest
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile

from test_prog_clip import PROBE, TARGET, footprints

HERE = pathlib.Path(__file__).resolve().parent / "harness"
EXPECTED = [
    ("1", "connector55", "TP2", "PB1", "#707070"),
    ("2", "connector87", "TP9", "VCC", "#ffffff"),
    ("3", "connector56", "TP3", "PB2", "#1768c4"),
    ("4", "connector54", "TP1", "PB0", "#7b3fb3"),
    ("5", "connector53", "TP6", "PB5", "#8c564b"),
    ("6", "connector89", "TP8", "GND", "#202020"),
]


class HarnessTests(unittest.TestCase):
    def test_native_fritzing_graph_has_six_correct_isolated_nets_in_both_views(self):
        root = ET.parse(HERE / "arduino_isp_harness.fz").getroot()
        instances = {i.get("modelIndex"): i for i in root.findall("instances/instance")}
        self.assertEqual(instances["1"].get("moduleIdRef"), "arduino_Uno_Rev3(fix)")
        probe, target = footprints(PROBE), footprints(TARGET)
        for view in ("breadboardView", "schematicView"):
            graph = {}

            def link(a, b):
                graph.setdefault(a, set()).add(b)
                graph.setdefault(b, set()).add(a)

            def reachable(start):
                found, pending = set(), [start]
                while pending:
                    node = pending.pop()
                    if node not in found:
                        found.add(node)
                        pending.extend(graph.get(node, ()))
                return found

            for model, instance in instances.items():
                for conn in instance.findall("views/" + view + "/connectors/connector"):
                    a = (model, conn.get("connectorId"))
                    for peer in conn.findall("connects/connect"):
                        b = (peer.get("modelIndex"), peer.get("connectorId"))
                        link(a, b)
                        back = instances[b[0]].findall(
                            "views/" + view + "/connectors/connector[@connectorId='%s']/connects/connect" % b[1])
                        self.assertTrue(any(p.get("modelIndex") == model and p.get("connectorId") == a[1]
                                            for p in back), (view, a, b))
                if instance.get("moduleIdRef") == "WireModuleID":
                    link((model, "connector0"), (model, "connector1"))
                elif instance.get("moduleIdRef", "").startswith("lantern-ring-"):
                    part = ET.parse(HERE / "parts" / ("part." + instance.get("path"))).getroot()
                    for bus in part.findall("buses/bus"):
                        nodes = [n.get("connectorId") for n in bus.findall("nodeMember")]
                        for cid in nodes[1:]:
                            link((model, nodes[0]), (model, cid))
            groups = []
            for number, host, tp, net, color in EXPECTED:
                self.assertEqual(probe["J1"]["pads"][number][1], "/" + net)
                self.assertEqual(target[tp]["pads"]["1"][1], net)
                group = reachable(("2", "connector" + number))
                self.assertIn(("4", "connector" + number), group)
                self.assertIn(("5", "connector1") if host is None else ("1", host), group)
                for other in groups:
                    self.assertFalse(group & other, (view, "shorted ISP nets"))
                groups.append(group)
                for model, cid in group:
                    inst = instances[model]
                    if inst.get("moduleIdRef") == "WireModuleID":
                        self.assertEqual(inst.find("views/" + view + "/wireExtras").get("color"), color)
            self.assertTrue({("2", "connector16"), ("3", "connector1"), ("3", "connector2"),
                             ("4", "connector6"), ("5", "connector2")} <= groups[-1])
            self.assertIn(("5", "connector1"), groups[1])
            # Use one matching 5 V supply, never short Uno 3V3 to it.
            self.assertIn(("1", "connector87"), groups[1])
            self.assertFalse(any(("1", cid) in graph for cid in ("connector85", "connector86")))

    def test_bundle_contains_the_editable_sketch_parts_and_valid_connector_artwork(self):
        with zipfile.ZipFile(HERE / "arduino_isp_harness.fzz") as bundle:
            self.assertEqual(bundle.read("arduino_isp_harness.fz").replace(b"\r\n", b"\n"),
                             (HERE / "arduino_isp_harness.fz").read_bytes().replace(b"\r\n", b"\n"))
            for path in (HERE / "parts").iterdir():
                self.assertEqual(bundle.read(path.name).replace(b"\r\n", b"\n"),
                                 path.read_bytes().replace(b"\r\n", b"\n"))
                if path.suffix != ".fzp":
                    continue
                part = ET.fromstring(bundle.read(path.name))
                for view in ("breadboardView", "schematicView"):
                    image = part.find("views/" + view + "/layers").get("image")
                    asset = "svg." + image.replace("/", ".")
                    art = ET.fromstring(bundle.read(asset))
                    ids = {e.get("id") for e in art.iter() if e.get("id")}
                    for connector in part.findall("connectors/connector"):
                        mapping = connector.find("views/" + view + "/p")
                        self.assertIn(mapping.get("svgId"), ids)
        for view in ("breadboard", "schematic"):
            exported = ET.parse(HERE / ("arduino_isp_harness_" + view + ".svg")).getroot()
            text = " ".join(exported.itertext())
            for label in ("PROGRAMMING CLIP", "RING IR PCB", "UNO 5V TARGET SUPPLY", "REMOVE CR2032"):
                self.assertIn(label, text)
            outlined_white = []
            for group in exported.iter():
                strokes = [e for e in group if e.get("stroke")]
                if group.get("partID") and len(strokes) == 2 and strokes[1].get("stroke") == "#ffffff":
                    self.assertEqual(strokes[0].get("stroke"), "#607080")
                    self.assertGreater(float(strokes[0].get("stroke-width")), float(strokes[1].get("stroke-width")))
                    outlined_white.append(group)
            self.assertEqual(len(outlined_white), 3, "Every white VCC link needs a visible outline")

    def test_colour_reference_header_orientation_matches_actual_probe(self):
        svg = ET.parse(HERE / "wiring-reference.svg").getroot()
        text = {e.text: (float(e.get("x")), float(e.get("y")))
                for e in svg.iter() if e.tag.endswith("text") and e.get("x") and e.get("y")}
        header = footprints(PROBE)["J1"]["pads"]
        rows = [("1 MISO", "2 VCC"), ("3 SCK", "4 MOSI"), ("5 RESET", "6 GND")]
        for odd, even in rows:
            self.assertEqual(text[odd][0], text[even][0])
            self.assertGreater(text[odd][1], text[even][1])
            self.assertGreater(header[odd[0]][0][1], header[even[0]][0][1])
        self.assertLess(text["1 MISO"][0], text["3 SCK"][0])
        self.assertLess(text["3 SCK"][0], text["5 RESET"][0])

    def test_html_guide_links_images_and_cable_rows_match_the_target(self):
        class GuideParser(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.ids, self.links, self.images, self.rows = [], [], [], {}
                self.row = None

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if "id" in attrs:
                    self.ids.append(attrs["id"])
                if tag == "a":
                    self.links.append(attrs["href"])
                elif tag == "img":
                    self.images.append(attrs)
                elif tag == "tr":
                    self.row = attrs.get("data-j1")
                    if self.row:
                        self.rows[self.row] = []

            def handle_endtag(self, tag):
                if tag == "tr":
                    self.row = None

            def handle_data(self, data):
                if self.row:
                    self.rows[self.row].append(data)

        guide = HERE.parents[3] / "docs" / "arduino-isp-wiring-reference.html"
        parser = GuideParser()
        parser.feed(guide.read_text(encoding="utf-8"))
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertEqual(set(parser.rows), {str(n) for n in range(1, 7)})
        for link in parser.links + [img["src"] for img in parser.images]:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            if url.path:
                self.assertTrue((guide.parent / unquote(url.path)).is_file(), link)
            else:
                self.assertIn(url.fragment, parser.ids, link)
        self.assertEqual(len(parser.images), 2)
        for image in parser.images:
            self.assertTrue(image.get("alt"))
            self.assertFalse(urlsplit(image["src"]).scheme, "Guide images must work offline")
        probe, target = footprints(PROBE), footprints(TARGET)
        for number, host, tp, net, color in EXPECTED:
            row = " ".join(parser.rows[number])
            self.assertIn(tp, row)
            self.assertIn(target[tp]["pads"]["1"][1], row)
            self.assertIn(probe["J1"]["pads"][number][1].lstrip("/"), row)
        self.assertIn("Uno 5V", " ".join(parser.rows["2"]))

    def test_voltage_illustration_uses_actual_front_pads_and_window(self):
        repo = HERE.parents[3]
        svg = ET.parse(repo / "docs" / "images" / "ir-voltage-test.svg").getroot()
        ids = {e.get("id"): e for e in svg.iter() if e.get("id")}
        target = footprints(TARGET)
        for ref in ("C1", "C2"):
            self.assertEqual(target[ref]["layer"], "F.Cu")
            for number in ("1", "2"):
                node = ids[ref + "." + number]
                (x, y), net, (w, h) = target[ref]["pads"][number]
                self.assertEqual(node.get("data-ref"), ref)
                self.assertEqual(node.get("data-pad"), number)
                self.assertEqual(node.get("data-net"), net)
                self.assertAlmostEqual(float(node.get("x")) + float(node.get("width")) / 2, x)
                self.assertAlmostEqual(float(node.get("y")) + float(node.get("height")) / 2, y)
                self.assertAlmostEqual(float(node.get("width")), w)
                self.assertAlmostEqual(float(node.get("height")), h)
        geometry = json.loads((HERE.parent / "generated" / "geometry.json").read_text())
        u0, v0, u1, v1 = geometry["fit_inputs"]["anvil"]["window"]
        ox, oy = target["TP3"]["pads"]["1"][0]
        window = ids["anvil-window"]
        for key, expected in (("x", ox - u1), ("y", oy + v0),
                              ("width", u1 - u0), ("height", v1 - v0)):
            self.assertAlmostEqual(float(window.get(key)), expected)
        from test_prog_clip import edge_items
        outline = [(float(x), float(y)) for x, y in
                   re.findall(r"([-\d.]+),([-\d.]+)", ids["ir-outline"].get("points"))]
        self.assertEqual(outline, edge_items(TARGET)[1][0])

    def test_html_illustration_provenance_matches_committed_sources(self):
        repo = HERE.parents[3]
        sources = json.loads((repo / "docs" / "images" /
                              "arduino-isp-reference-sources.json").read_text())
        for table in (sources["asset_sha256"], sources["voltage_figure"]["source_sha256"]):
            for path, digest in table.items():
                normalized = (repo / path).read_text(encoding="utf-8").encode("utf-8")
                self.assertEqual(hashlib.sha256(normalized).hexdigest(), digest, path)
        physical = sources["physical_figure"]
        self.assertFalse(physical["source_pdf_committed"])
        self.assertTrue(physical["header_post_raycast_verified"])
        mesh_dir = repo / physical["mesh_directory"]
        meshes = json.loads((mesh_dir / "meshes.json").read_text())
        for entry in meshes:
            digest = hashlib.sha256((mesh_dir / entry["file"]).read_bytes()).hexdigest()
            self.assertEqual(digest, physical["mesh_sha256"][entry["name"]], entry["name"])

    def test_programming_evidence_preserves_memories_and_only_changes_clock_divider(self):
        evidence = json.loads((HERE.parent / "programming-evidence.json").read_text())
        run = evidence["verified_isp_run"]
        before, after = run["fuses_before"], run["fuses_after"]
        self.assertEqual({key for key in before if before[key] != after[key]}, {"lfuse"})
        self.assertEqual(int(before["lfuse"], 16) ^ int(after["lfuse"], 16), 0x80)
        self.assertEqual(run["sha256"]["expected_whole_flash"], run["sha256"]["flash_after"])
        self.assertEqual(run["sha256"]["eeprom_before"], run["sha256"]["eeprom_after"])
        self.assertLessEqual(run["flash_bytes_used"], run["flash_bytes_read_back"])
        self.assertIn("User report:", evidence["reported_5v_setup"]["source"])
        self.assertIn("not a separately", evidence["reported_5v_setup"]["limitations"])


if __name__ == "__main__":
    unittest.main()
