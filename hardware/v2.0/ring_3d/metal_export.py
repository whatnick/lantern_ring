"""Assemble the hybrid metal/plastic print package into generated/metal/.

Reads the already generated STL/STEP files (run lantern_ring.py then crowns.py
first), re-checks every metal part with printcheck, and writes:

    generated/metal/01_metal/            RingBase + crowns (STL + STEP)
    generated/metal/02_plastic_insulating/  Carrier, ContactDeck, Bezel
    generated/metal/reference/           full assembly STEP
    generated/metal/manifest.json        volumes, wall checks, cost estimate
    generated/metal/README.md            ordering notes
    generated/lantern_ring_v2_metal.zip  the folder, ready to upload

Needs only NumPy (plus the standard library); no FreeCAD.
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import printcheck  # noqa: E402

GENERATED = HERE / "generated"
OUT = GENERATED / "metal"
METAL_PARTS = ["RingBase"]
PLASTIC_PARTS = ["Carrier", "ContactDeck", "Bezel"]
# Elecrow's public quote formula (page script, 2026-10): CNY per gram, per-part minimum
# in CNY, density g/cm3, order minimum in CNY. total = max(parts, minimum) * 0.9 / 6.35 * 1.1.
ELECROW_METALS = {
    "Stainless Steel A316L": {"cny_g": 2.0, "part_min": 150, "order_min": 30, "density": 7.98},
    "AlSi10Mg Aluminum Alloy": {"cny_g": 3.5, "part_min": 150, "order_min": 30, "density": 2.82},
    "Ti6Al4V Titanium Alloy": {"cny_g": 20.5, "part_min": 180, "order_min": 30, "density": 4.52},
}
CNY_PER_USD = 6.35
RATE = 1.1
DISCOUNT = 0.9
# Indicative USD per cm3 for cast brass/bronze (generic industry range, not an Elecrow service).
PRICE_PER_CM3 = {"bronze_or_brass_cast": (20, 60)}
RELIEF = (0.6, 0.4)


def elecrow_usd(volumes_cm3, material):
    """Price for printing the given part volumes (cm3) as separate items, per Elecrow's formula."""
    spec = ELECROW_METALS[material]
    total_cny = 0.0
    for volume in volumes_cm3:
        weight_cost = spec["cny_g"] * spec["density"] * volume
        total_cny += max(weight_cost, spec["part_min"])
    usd = max(round(100 * total_cny * RATE / CNY_PER_USD) / 100, spec["order_min"]) * DISCOUNT
    return round(usd, 2)


def crown_names():
    return sorted(p.stem for p in (GENERATED / "crowns").glob("Crown_*.stl"))


def copy_pair(src_dir, name, dest):
    dest.mkdir(parents=True, exist_ok=True)
    for ext in (".stl", ".step"):
        shutil.copy2(src_dir / (name + ext), dest / (name + ext))


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    metal_dir = OUT / "01_metal"
    plastic_dir = OUT / "02_plastic_insulating"
    parts = []
    for name in METAL_PARTS:
        copy_pair(GENERATED, name, metal_dir)
        report = printcheck.check_stl(metal_dir / (name + ".stl"), 1.0)
        parts.append(("metal", name, report))
    for name in crown_names():
        copy_pair(GENERATED / "crowns", name, metal_dir)
        report = printcheck.check_stl(metal_dir / (name + ".stl"), 1.0, emboss=RELIEF)
        parts.append(("metal", name, report))
    for name in PLASTIC_PARTS:
        copy_pair(GENERATED, name, plastic_dir)
        report = printcheck.check_stl(plastic_dir / (name + ".stl"), 1.0)
        parts.append(("plastic", name, report))
    ref = OUT / "reference"
    ref.mkdir(parents=True)
    shutil.copy2(GENERATED / "Lantern_Ring_v2.step", ref / "Lantern_Ring_v2_assembly.step")

    metal_cm3 = {n: r["volume_mm3"] / 1000 for k, n, r in parts if k == "metal"}
    base = metal_cm3["RingBase"]
    crown_avg = sum(v for n, v in metal_cm3.items() if n.startswith("Crown_")) / max(1, len(metal_cm3) - 1)
    manifest = {
        "note": "Hybrid set: metal RingBase and crowns, plastic insulating parts. Indicative prices only.",
        "wall_rule_mm": 1.0,
        "crown_relief_detail_min_mm": RELIEF[1],
        "parts": [{"group": k, "part": n, "volume_cm3": round(r["volume_mm3"] / 1000, 3),
                   "size_mm": r["size_mm"], "min_wall_mm": r["min_thickness_mm"],
                   "watertight": r["watertight"], "passes": r["passes"]} for k, n, r in parts],
        "estimate_usd_elecrow_formula": {
            material: {
                "ringbase_plus_crown_as_separate_items": elecrow_usd([base, crown_avg], material),
                "all_five_parts_as_separate_items": elecrow_usd(
                    [r["volume_mm3"] / 1000 for k, n, r in parts if n in METAL_PARTS + PLASTIC_PARTS] + [crown_avg],
                    material),
                "ringbase_plus_crown_as_one_combined_file": elecrow_usd([base + crown_avg], material),
            } for material in ELECROW_METALS},
        "estimate_usd_per_ring_cast_brass_bronze": {
            proc: {"ringbase": [round(base * lo, 1), round(base * hi, 1)],
                   "ringbase_plus_one_crown": [round((base + crown_avg) * lo, 1),
                                               round((base + crown_avg) * hi, 1)]}
            for proc, (lo, hi) in PRICE_PER_CM3.items()},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUT / "README.md").write_text(README)

    zip_path = GENERATED / "lantern_ring_v2_metal.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(OUT).as_posix())
    failed = [n for _, n, r in parts if not r["passes"]]
    for k, n, r in parts:
        print("{:8s} {:24s} {:7.3f} cm3  min wall {:.3f} mm  {}".format(
            k, n, r["volume_mm3"] / 1000, r["min_thickness_mm"], "PASS" if r["passes"] else "FAIL"))
    print("wrote", OUT, "and", zip_path)
    return 1 if failed else 0


README = """# Lantern Ring v2 - hybrid metal/plastic package

Generated by `metal_export.py`; do not edit by hand.

| Folder | Order as | Why |
|---|---|---|
| `01_metal/` | Metal (see Elecrow materials below) | RingBase takes the wear (band and bayonet lugs); crowns are the premium cosmetic part |
| `02_plastic_insulating/` | Plastic (e.g. Elecrow resin/nylon) | Carrier, ContactDeck and Bezel hold the pogo pins and battery and must insulate the positive path |
| `reference/` | not for printing | Full assembly STEP for fit checks |

## Elecrow metal materials (elecrow.com/3d-printing-service.html)

Elecrow prints three metals: Stainless Steel A316L (7.98 g/cm3), AlSi10Mg aluminium
(2.82) and Ti6Al4V titanium (4.52). All are grainy grey as printed, accuracy
+/-0.3 mm per 100 mm, and Elecrow publishes no metal minimum-wall figure, so ask.
It does not list brass or bronze; those need a casting service.

Elecrow prices by weight with a per-part minimum, then 10% off:
`max(CNY/g x density x cm3, part minimum)`, x1.1 / 6.35 to USD, order minimum USD 30
(27 after the discount).
Stainless and aluminium: 2.0 and 3.5 CNY/g, part minimum 150 CNY (about USD 23.4 after
the discount). Titanium: 20.5 CNY/g, part minimum 180 CNY (about USD 28.1).

Every part here is under 2 cm3, far below the weight threshold (about 9.4 cm3 for
stainless), so each separate file costs the part minimum regardless of size:

| Item | 316L | AlSi10Mg | Ti6Al4V |
|---|---|---|---|
| RingBase + one crown (2 files) | about $46.8 | about $46.8 | about $56.2 |
| All five parts (5 files) | about $117 | about $117 | about $140 |

Ask Elecrow whether several parts nested in one STL count as one item. All five parts
total about 5.6 cm3, under the 9.4 cm3 threshold, so a single combined file would hit
only the USD 27 order minimum in 316L or aluminium (about USD 42 for RingBase plus crown
in titanium). Treat these as estimates and confirm by email (service@elecrow.com).

Choosing a material: 316L is the default (cheapest, corrosion resistant, takes plating
and PVD). AlSi10Mg is light and anodises green, but it is softer and wears faster.
Ti6Al4V is strong and light but costs the most and is hard to colour.

## Finishing and colour (green)

| Method | Fits | Notes |
|---|---|---|
| Powder coat | any | Opaque, adds 50-100 um per face. Mask contacts and bayonet faces. |
| Anodise | aluminium only | Translucent metallic green, thin, wear resistant. |
| PVD / ion plating | 316L, brass | 1-3 um, hardest wearing, limited green tones, vendor minimums. |
| Cerakote / ceramic spray | any | Wide greens, thin. Mask contacts. |
| Enamel in the logo relief | crowns | Two-tone crown, polish high spots. Fiddly, premium. |
| Patina + lacquer | brass, bronze | Verdigris, cheap, not durable unless sealed. |

Printed metal is rough (about Ra 6-10 um): tumble or polish before coating. Allow for
coating thickness in the bayonet clearance, and keep the negative contact area and
pogo seats bare or plated.

## Colour and paint options for every material

Elecrow's own colour statements (page text; surface treatment is charged extra):

| Material | Colour as printed | Colour route |
|---|---|---|
| Photosensitive resin 9400, Genl | smooth white | "oil injection" colouring (spray paint) offered |
| Yellow high-toughness resin | light yellow | same |
| Transparent / translucent resin | clear / frosted | keep clear for the LED lens; tint with clear dye or lacquer |
| Black resin | grey-black | paint over, or leave |
| Nylon, nylon + glass fibre, high-performance nylon | grey-white, grainy | dye bath or paint after priming |
| PLA / PETG | black, white (default), orange, blue, red, green selectable - add a note to the order | choose green at order time, no paint needed |
| Stainless A316L, AlSi10Mg, Ti6Al4V | grainy grey | metal finishes below |

Paint systems for printed parts you finish yourself:

| System | Use on | Notes |
|---|---|---|
| Spray primer + acrylic or enamel spray (e.g. Lantern green) | resin, nylon, PLA, metal | Sand 400-800 grit, prime, 2-3 thin coats, clear coat. Adds about 30-60 um. |
| Airbrushed acrylic / lacquer | resin, nylon, crowns | Best for the two-tone logo and a green gradient. |
| Fabric / nylon dye (e.g. green) | nylon only | Penetrates, so no dimensional change. Dye before assembly. |
| Alcohol or resin-compatible tint in clear resin | clear resin | Colours the lens without blocking light. Test on a sample first. |
| Metallic paint / rub-n-buff (green-gold, verdigris) | any | Fast crown highlights on raised logo detail. |
| Glow or UV paint | crown logo | Charges from the LED; a nice night effect. |
| Epoxy / UV-resin fill in the logo relief | crowns | Fill, then scrape high spots for a crisp inlay. |
| Clear coat (gloss or matt) | all painted parts | Protects against hand wear. Skip on contact faces. |

Rules for this ring: keep paint off the pogo seats, battery contact faces and bayonet
sliding faces (mask with tape or a plug); keep the lens and LED window unpainted; and
allow 0.05-0.1 mm per painted face in the bayonet clearance, or leave the bayonet
unpainted. Painting the print does not change the Elecrow thickness check.

## Small-scale production routes

- Investment casting from a printed wax or resin pattern: 10-200 units, no tooling,
  brass or bronze (about USD 20-60 per cm3, indicative).
- Die-cast zinc: tooling roughly USD 3-10k, worth it above about 1-2k units.
- Metal injection moulding: tooling like die casting, for tiny detail at volume.

## Notes
- Upload the STEP files if the bureau accepts them; STLs are the same geometry.
- Wall rule is 1.0 mm everywhere (conservative for metal). Raised crown logo detail is held to 0.4 mm; check this against the bureau's minimum embossed feature.
- Nothing has been tolerance-tuned for metal.
- A metal RingBase touches the Carrier. Keep it electrically isolated from the pogo pins, or add an insulating liner, before using it as a circuit return. Plate any contact face (nickel or gold) to avoid galvanic corrosion.
- `manifest.json` holds volumes, wall checks and the price estimates above.
"""

if __name__ == "__main__":
    raise SystemExit(build())
