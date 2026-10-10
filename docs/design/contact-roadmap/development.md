# Contact roadmap development

Source and development notes for local FreeCAD concept illustrations and
optional Nano Banana image generation. The concepts do not replace the v2
manufacturing CAD.

## Local FreeCAD concepts

- `render_concepts.py` renders the four local concept images.
- `test_roadmap.py` checks the local illustration outputs.
- `images/local-freecad/manifest.json` records local render provenance.
- `contact-paths.svg` is the authored contact/isolation topology diagram.

Rebuild and test with FreeCAD's bundled Python:

```powershell
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' docs\design\contact-roadmap\render_concepts.py
python -m unittest discover -s docs\design\contact-roadmap -p "test_roadmap.py"
```

## Optional Nano Banana generation

Generation is not currently verified: no authenticated image API access is
available. The five prompts are in `prompts.json`; `generate_nano_banana.py`
has offline request/response tests and calls the
[Gemini image API](https://ai.google.dev/gemini-api/docs/image-generation).
The default model is Nano Banana 2, `gemini-3.1-flash-image-preview`, as listed
by the [official Gemini CLI extension](https://github.com/gemini-cli-extensions/nanobanana).

From the repository root:

```powershell
python docs\design\contact-roadmap\generate_nano_banana.py --dry-run
# Set an API key securely in the environment; never add it to a tracked file.
python docs\design\contact-roadmap\generate_nano_banana.py
# Use a fresh output directory for reviewed iterations.
python docs\design\contact-roadmap\generate_nano_banana.py --stage 04-floating-metal --output docs\design\contact-roadmap\images\nano-banana-metal-iteration-2
```

Only authored text prompts are sent. Calls may incur provider charges. The
client accepts `NANOBANANA_API_KEY` and documented Gemini/Google fallback key
variables; it does not print or commit keys. Authentication, model availability
and quota are required. Errors are explicit. Successful runs write images and
a provenance manifest; review all output before embedding it because generated
imagery can depict unsafe or impossible electrical/mechanical relationships.
Do not use it to select dimensions or prove compliance.
