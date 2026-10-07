"""Run with FreeCAD's Python after a successful build, in a fresh process."""

import json
import unittest

from lantern_ring import App, bop_check, HERE, PRINT_PARTS, RingFeature, object_config, validate_geometry


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
            centre_z = p["bore_top"] - (original + 1.0) / 2
            point = App.Vector(original / 2 + 0.2, 0, centre_z)
            self.assertFalse(self.doc.RingBase.Shape.isInside(point, 1e-6, False))
            bop_check(self.doc.RingBase.Shape)
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

    def test_band_is_open_with_rounded_tips_and_insulated_nested_crown(self):
        p = json.loads(object_config(self.doc.Parameters))
        base = self.doc.RingBase.Shape
        centre_z = p["bore_top"] - p["finger_diameter"] / 2
        for y in (-5.4, 0, 5.4):
            self.assertFalse(base.isInside(App.Vector(0, y, centre_z - 9.25), 1e-6, True))
        # Tapered shank: about 8.25 mm wide at the bore centre height, 11 mm at the crest.
        for y in (-3.6, 0, 3.6):
            self.assertTrue(base.isInside(App.Vector(9.75, y, centre_z), 1e-6, False))
        for y in (-4.6, 4.6):
            self.assertFalse(base.isInside(App.Vector(9.75, y, centre_z), 1e-6, True))
        self.assertTrue(base.isInside(App.Vector(0, 0, 0.55), 1e-6, False))
        self.assertFalse(base.isInside(App.Vector(0, 0, 0.2), 1e-6, False))

    def test_gap_angle_recomputes_elastic_arms(self):
        parameters = self.doc.Parameters
        original = parameters.BandGapAngle.Value
        before = self.doc.RingBase.Shape.Volume
        try:
            parameters.BandGapAngle = 70
            self.doc.recompute()
            self.assertLess(self.doc.RingBase.Shape.Volume, before)
            bop_check(self.doc.RingBase.Shape)
        finally:
            parameters.BandGapAngle = original
            self.doc.recompute()
        self.assertAlmostEqual(before, self.doc.RingBase.Shape.Volume, places=5)

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
