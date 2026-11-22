"""Compile and exercise the real driver against mock AVR registers."""
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


class DriverTest(unittest.TestCase):
    def test_board_channel_and_selector_allocation(self):
        root = HERE.parents[2]
        for variant in ("ring_pcb_RGBW", "ring_pcb_RGBW_dual"):
            path = root / "hardware" / "v2.0" / variant / "parameters.json"
            params = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual({c["colour"]: c["gpio"] for c in params["channels"]},
                             {"R": "PB0", "G": "PB1", "B": "PB4", "W": "PB2"})
            netlist = ET.parse(path.parent / "generated" / "netlist.xml").getroot()
            nets = {(node.attrib["ref"], node.attrib["pin"]): net.attrib["name"]
                    for net in netlist.findall("nets/net") for node in net.findall("node")}
            for terminal, net in ((("U1", "2"), "PB3"), (("TP4", "1"), "PB3"),
                                  (("JP1", "1"), "PB3"), (("JP1", "2"), "GND"),
                                  (("R13", "1"), "VCC"), (("R13", "2"), "PB3")):
                self.assertEqual(nets[terminal], net, (variant, terminal))

    def test_fixed_and_jumper_configuration_and_pwm(self):
        compiler = os.environ.get("CXX", "g++")
        for mode in (0, 1):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                exe = Path(tmp) / ("test.exe" if os.name == "nt" else "test")
                subprocess.run([compiler, "-std=gnu++11", "-Wall", "-Wextra", "-Werror",
                                "-DF_CPU=8000000UL", "-DRGBW_MODE=%d" % mode,
                                "-I", str(HERE / "mock"), str(HERE / "test_driver.cpp"),
                                "-o", str(exe)], check=True)
                subprocess.run([str(exe)], check=True)

    def test_invalid_mode_and_channel_fail_compilation(self):
        compiler = os.environ.get("CXX", "g++")
        for override, message in (("-DRGBW_MODE=2", "RGBW_MODE must be"),
                                  ("-DRGBW_FIXED_R=256", "channel values must be")):
            with self.subTest(override=override), tempfile.TemporaryDirectory() as tmp:
                result = subprocess.run(
                    [compiler, "-std=gnu++11", "-DF_CPU=8000000UL", override,
                     "-I", str(HERE / "mock"), "-fsyntax-only", str(HERE / "test_driver.cpp")],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)


if __name__ == "__main__":
    unittest.main()
