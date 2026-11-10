"""Independently check the saved Fritzing cable graph against the KiCad boards."""

import pathlib
import unittest
import xml.etree.ElementTree as ET
import zipfile

from test_prog_clip import PROBE, TARGET, footprints

HERE = pathlib.Path(__file__).resolve().parent / "harness"
EXPECTED = [
    ("1", "connector55", "TP2", "PB1", "#238b45"),
    ("2", None, "TP9", "VCC", "#d62728"),
    ("3", "connector56", "TP3", "PB2", "#1768c4"),
    ("4", "connector54", "TP1", "PB0", "#c99b00"),
    ("5", "connector53", "TP6", "PB5", "#e87500"),
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
            # Never silently feed a 5 V Uno output into an unqualified coin-cell target.
            self.assertFalse(any(("1", cid) in graph for cid in ("connector85", "connector86", "connector87")))

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
            for label in ("PROGRAMMING CLIP", "RING IR PCB", "SELECTED TARGET SUPPLY", "REMOVE CR2032"):
                self.assertIn(label, text)

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


if __name__ == "__main__":
    unittest.main()
