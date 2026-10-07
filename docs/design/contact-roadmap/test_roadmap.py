import base64
import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import urllib.error
import xml.etree.ElementTree as ET
import zlib

from generate_nano_banana import HERE, extract_png, generate, load_prompts, request_for


def check_png(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not PNG")
    cursor = 8
    types = []
    while cursor < len(data):
        length = struct.unpack(">I", data[cursor:cursor + 4])[0]
        kind = data[cursor + 4:cursor + 8]
        payload = data[cursor + 8:cursor + 8 + length]
        crc = struct.unpack(">I", data[cursor + 8 + length:cursor + 12 + length])[0]
        if crc != zlib.crc32(kind + payload):
            raise ValueError("PNG checksum mismatch")
        types.append(kind)
        cursor += 12 + length
    if cursor != len(data) or types[0] != b"IHDR" or types[-1] != b"IEND" or b"IDAT" not in types:
        raise ValueError("Incomplete PNG")


class RoadmapTests(unittest.TestCase):
    def setUp(self):
        self.prompts = load_prompts()
        self.data = (HERE / "images" / "local-freecad" / "01-serviceable-pogo.png").read_bytes()
        self.response = {"candidates": [{"content": {"parts": [
            {"text": "Concept only"},
            {"inlineData": {"mimeType": "image/png",
                            "data": base64.b64encode(self.data).decode("ascii")}},
        ]}}]}

    def test_prompt_stages_cover_contact_and_metal_progression(self):
        self.assertEqual(len(self.prompts["stages"]), 5)
        self.assertEqual(self.prompts["model"], "gemini-3.1-flash-image-preview")
        self.assertIn("TWO independent contact circuits", self.prompts["common"])
        for dimension in ("24.9 mm", "23.4 mm", "11 mm", "11.42 mm"):
            self.assertIn(dimension, self.prompts["common"])
        self.assertIn("OPEN the band BOTTOM", self.prompts["common"])
        self.assertIn("0.5 mm floor", self.prompts["common"])
        self.assertIn("No red wire", self.prompts["stages"][0]["prompt"])
        metal = next(s for s in self.prompts["stages"] if s["id"] == "04-floating-metal")
        self.assertIn("FLOATING", metal["prompt"])
        self.assertIn("anodizing", metal["prompt"])
        self.assertEqual(request_for("common", {"prompt": "stage"})["contents"][0]["parts"],
                         [{"text": "common\n\nstage"}])

    def test_local_provenance_and_complete_images(self):
        manifest = json.loads((HERE / "images" / "local-freecad" / "manifest.json").read_text())
        self.assertEqual(len(manifest["images"]), 4)
        self.assertIn("BLOCKED", manifest["nano_banana_status"])
        cad = HERE.parents[2] / "hardware" / "v2.0" / "ring_3d"
        for name, expected in manifest["cad_source_sha256"].items():
            self.assertEqual(hashlib.sha256((cad / name).read_text(encoding="utf-8").encode()).hexdigest(),
                             expected, "Regenerate roadmap after changing CAD")
        self.assertEqual(hashlib.sha256((HERE / "render_concepts.py").read_text(encoding="utf-8").encode()).hexdigest(),
                         manifest["renderer_sha256"])
        for record in manifest["images"]:
            data = (HERE / "images" / "local-freecad" / record["file"]).read_bytes()
            check_png(data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
            self.assertIn("NOT Nano Banana", record["status"])

    def test_contact_schematic_is_valid_svg(self):
        root = ET.parse(HERE / "contact-paths.svg").getroot()
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        text = "".join(root.itertext())
        self.assertIn("preload UP", text)
        self.assertIn("preload DOWN", text)
        self.assertIn("electrically floating", text)

    def test_api_extracts_real_png(self):
        data, width, height = extract_png(self.response)
        self.assertEqual(data, self.data)
        self.assertEqual(width, 800)
        self.assertGreater(height, 500)

    def test_no_image_invalid_base64_or_wrong_signature_fails(self):
        cases = [
            {},
            {"candidates": [{"content": {"parts": [{"text": "No image"}]}}]},
            {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": "!!"}}]}}]},
            {"candidates": [{"content": {"parts": [{"inlineData": {
                "mimeType": "image/png", "data": base64.b64encode(b"not an image").decode()}}]}}]},
        ]
        for response in cases:
            with self.subTest(response=response), self.assertRaises(ValueError):
                extract_png(response)

    def test_api_request_and_success_provenance_without_network(self):
        calls = []

        def transport(request, timeout):
            calls.append((request, timeout))
            return io.BytesIO(json.dumps(self.response).encode())

        with tempfile.TemporaryDirectory() as output, redirect_stdout(io.StringIO()):
            manifest = generate(self.prompts, output, "unit-test-key", transport)
            self.assertEqual(len(calls), 5)
            self.assertEqual(len(manifest["images"]), 5)
            self.assertIn("Nano Banana", manifest["generator"])
            self.assertNotIn("unit-test-key", json.dumps(manifest))
            request, timeout = calls[0]
            self.assertEqual(timeout, 180)
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.get_header("X-goog-api-key"), "unit-test-key")
            self.assertNotIn("key=", request.full_url)
            self.assertEqual(json.loads(request.data)["generationConfig"]["responseModalities"],
                             ["TEXT", "IMAGE"])
            for record in manifest["images"]:
                check_png((Path(output) / record["file"]).read_bytes())

    def test_missing_auth_existing_outputs_and_provider_failure(self):
        with tempfile.TemporaryDirectory() as output:
            with self.assertRaisesRegex(ValueError, "key"):
                generate(self.prompts, output, "")
            destination = Path(output) / (self.prompts["stages"][-1]["id"] + ".png")
            destination.write_bytes(self.data)
            with self.assertRaises(FileExistsError):
                generate(self.prompts, output, "unit-test-key")
        with tempfile.TemporaryDirectory() as output:
            def denied(request, timeout):
                raise urllib.error.HTTPError(request.full_url, 403, "unit-test-key", {}, None)
            with self.assertRaisesRegex(RuntimeError, "HTTP 403") as error:
                generate(self.prompts, output, "unit-test-key", denied)
            self.assertNotIn("unit-test-key", str(error.exception))
            self.assertFalse((Path(output) / "manifest.json").exists())

    def test_prompt_validation_rejects_path_traversal(self):
        prompts = copy.deepcopy(self.prompts)
        prompts["stages"][0]["id"] = "../bad"
        with tempfile.TemporaryDirectory() as output:
            path = Path(output) / "prompts.json"
            path.write_text(json.dumps(prompts))
            with self.assertRaises(ValueError):
                load_prompts(path)


if __name__ == "__main__":
    unittest.main()
