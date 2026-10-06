"""Generate roadmap ideation images with Google's Nano Banana image API."""

import argparse
import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import urllib.error
import urllib.request


HERE = Path(__file__).resolve().parent
API = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
KEY_NAMES = ("NANOBANANA_API_KEY", "NANOBANANA_GEMINI_API_KEY",
             "NANOBANANA_GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")


def load_prompts(path=HERE / "prompts.json"):
    prompts = json.loads(Path(path).read_text(encoding="utf-8"))
    if not prompts.get("common") or not prompts.get("stages"):
        raise ValueError("Prompt manifest needs common instructions and stages")
    if not re.fullmatch(r"gemini-[a-zA-Z0-9.-]+", prompts["model"]):
        raise ValueError("Invalid Gemini model identifier")
    ids = [stage["id"] for stage in prompts["stages"]]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[a-z0-9-]+", name) for name in ids):
        raise ValueError("Stage identifiers must be unique, safe filenames")
    if any(not stage.get("title") or not stage.get("prompt") for stage in prompts["stages"]):
        raise ValueError("Each stage needs a title and prompt")
    return prompts


def request_for(common, stage):
    return {
        "contents": [{"role": "user", "parts": [{"text": common + "\n\n" + stage["prompt"]}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }


def extract_png(response):
    candidates = response.get("candidates", [])
    for candidate in candidates:
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData", {})
            if inline.get("mimeType") != "image/png":
                continue
            try:
                data = base64.b64decode(inline["data"], validate=True)
            except (KeyError, ValueError, binascii.Error) as error:
                raise ValueError("API returned invalid image data") from error
            if (len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n"
                    or data[12:16] != b"IHDR"):
                raise ValueError("API response is not a PNG image")
            width, height = struct.unpack(">II", data[16:24])
            if width <= 0 or height <= 0 or b"IEND" not in data[-20:]:
                raise ValueError("API returned an incomplete PNG image")
            return data, width, height
    raise ValueError("API returned no PNG image; check model access, quota or safety filtering")


def generate(prompts, output, api_key, transport=urllib.request.urlopen):
    if not api_key:
        raise ValueError("Nano Banana API key is missing")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    # A failed rerun must not leave a success-shaped manifest for mixed images.
    if manifest_path.exists():
        raise FileExistsError("Output already contains a manifest; choose a new --output directory")
    if any((output / (stage["id"] + ".png")).exists() for stage in prompts["stages"]):
        raise FileExistsError("Image exists; choose a fresh output directory")
    records = []
    for stage in prompts["stages"]:
        destination = output / (stage["id"] + ".png")
        request = urllib.request.Request(
            API.format(prompts["model"]),
            data=json.dumps(request_for(prompts["common"], stage)).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        try:
            with transport(request, timeout=180) as result:
                response = json.loads(result.read())
        except urllib.error.HTTPError as error:
            # Never log request headers or raw API error bodies containing credentials.
            raise RuntimeError("Nano Banana HTTP {}; check authentication, model access and quota".format(error.code)) from None
        except urllib.error.URLError:
            raise RuntimeError("Nano Banana network request failed") from None
        data, width, height = extract_png(response)
        destination.write_bytes(data)
        records.append({
            "file": destination.name,
            "stage": stage["id"],
            "title": stage["title"],
            "width": width,
            "height": height,
            "sha256": hashlib.sha256(data).hexdigest(),
            "prompt_sha256": hashlib.sha256(
                (prompts["common"] + "\n\n" + stage["prompt"]).encode("utf-8")).hexdigest(),
        })
        print("Generated {}".format(destination.name))
    manifest = {
        "generator": "Google Gemini image API / Nano Banana",
        "model": prompts["model"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "AI ideation only; not validated CAD or physically qualified hardware",
        "images": records,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "images" / "nano-banana")
    parser.add_argument("--stage", help="Generate just one stage by id")
    parser.add_argument("--dry-run", action="store_true", help="Validate prompts; no API request")
    args = parser.parse_args()
    prompts = load_prompts()
    if args.stage:
        prompts["stages"] = [s for s in prompts["stages"] if s["id"] == args.stage]
        if not prompts["stages"]:
            parser.error("Unknown stage")
    if args.dry_run:
        for stage in prompts["stages"]:
            print("{}: {}".format(stage["id"], stage["title"]))
        return
    key = next((os.environ[name] for name in KEY_NAMES if os.environ.get(name)), None)
    if key is None:
        parser.exit(2, "Nano Banana unavailable: set NANOBANANA_API_KEY in the environment; never commit it.\n")
    try:
        generate(prompts, args.output, key)
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, "Image generation failed: {}\n".format(error))


if __name__ == "__main__":
    main()
