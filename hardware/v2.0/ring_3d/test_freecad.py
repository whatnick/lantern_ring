"""Run with FreeCAD's Python after a successful build, in a fresh process."""

import json
import unittest

from lantern_ring import App, HERE, PRINT_PARTS, RingFeature, object_config, validate_geometry


class NativeDocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = App.openDocument(str(HERE / "generated" / "Lantern_Ring_v2.FCStd"))

    @classmethod
    def tearDownClass(cls):
        App.closeDocument(cls.doc.Name)

    def test_proxies_restore_under_importable_module(self):
        for name in PRINT_PARTS:
            self.assertIsInstance(self.doc.getObject(name).Proxy, RingFeature)

    def test_finger_size_recomputes_real_bore(self):
        parameters = self.doc.Parameters
        original = parameters.FingerDiameter.Value
        before = self.doc.RingBase.Shape.Volume
        try:
            parameters.FingerDiameter = original + 1.0
            self.doc.recompute()
            self.assertNotAlmostEqual(before, self.doc.RingBase.Shape.Volume, places=3)
            p = json.loads(object_config(parameters))
            centre_z = -(original + 1.0) / 2 - p["band_wall"] / 2
            point = App.Vector(original / 2 + 0.2, 0, centre_z)
            self.assertFalse(self.doc.RingBase.Shape.isInside(point, 1e-6, False))
            self.doc.RingBase.Shape.check(True)
        finally:
            parameters.FingerDiameter = original
            self.doc.recompute()
        self.assertAlmostEqual(before, self.doc.RingBase.Shape.Volume, places=5)

    def test_pcb_clearance_recomputes_contact_deck(self):
        parameters = self.doc.Parameters
        original = parameters.PCBClearance.Value
        before = self.doc.ContactDeck.Shape.Volume
        try:
            parameters.PCBClearance = original + 0.1
            self.doc.recompute()
            self.assertLess(self.doc.ContactDeck.Shape.Volume, before)
            self.doc.ContactDeck.Shape.check(True)
        finally:
            parameters.PCBClearance = original
            self.doc.recompute()
        self.assertAlmostEqual(before, self.doc.ContactDeck.Shape.Volume, places=5)

    def test_twist_angle_recomputes_socket_and_whole_cassette(self):
        parameters = self.doc.Parameters
        original = parameters.LockAngle.Value
        try:
            parameters.LockAngle = original + 5.0
            self.doc.recompute()
            p = json.loads(object_config(parameters))
            pcb = json.loads(parameters.PCBInterface)
            parts = {name: self.doc.getObject(name).Shape for name in
                     ("RingBase", "Carrier", "ContactDeck", "Bezel", "PCB", "Battery",
                      "PositivePogo", "NegativePogo", "PositiveLead", "NegativeLead", "LEDs")}
            validate_geometry(p, pcb, parts)
        finally:
            parameters.LockAngle = original
            self.doc.recompute()


if __name__ == "__main__":
    unittest.main()
