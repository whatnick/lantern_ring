---
name: lantern-ring-freecad
description: Rebuild and modify Lantern Ring v2 FreeCAD hardware, including the keyed bayonet PCB cassette, CR2032 pogo contacts, insulation, print exports, and mechanical validation.
---

# Lantern Ring FreeCAD reconstruction

The contact/material ideation roadmap is `docs/design/contact-roadmap/README.md`.
Its copper-foil, plated-leaf and metal-shell illustrations are not validated
replacement geometry. Keep the metal shell floating and retain a continuous
insulating contact/battery insert unless a separately reviewed design changes it.

Use this skill for Lantern Ring enclosure, PCB fit, battery contacts, FreeCAD
regeneration, printing or mechanical review. Work from
`hardware/v2.0/ring_3d/README.md`, `parameters.json`, `design.py` and
`lantern_ring.py`; the values below are reconstruction invariants, not permission
to replace measured geometry with a generic circle.

## Tool-neutral design invariants

- The supported mono PCB has a **17.78 x 19.05 x 1.6 mm** ten-vertex profile.
  Derive vertices from its real Edge.Cuts. KiCad (136.906, 83.185) is CAD XY zero;
  convert `(x, y)` to `(x - 136.906, 83.185 - y)`. Do not mirror the board.
- Front TP1 `/GND` is CAD (-0.0254, +7.493). Rear exposed VCC is
  CAD (0, +0.381), radius 2.962124. Preserve net/filled-copper/mask verification.
  Other board variants have different contact assignments.
- Four prints: band/socket RingBase, bayonet Carrier, removable ContactDeck
  and screw-retained Bezel. The **entire cassette rotates**, not bare PCB edges.
- Three lugs at 0/120/240 degrees have widths 24/14/14 degrees. Slots add
  2 degrees per flank; 30-degree counterclockwise twist seats them under shelves.
  The wide lug cannot enter either narrow slot. A radial M1 x 2 screw at the
  locked wide lug prevents accidental counterrotation; it is mandatory.
- The PCB pocket is profiled, not a positive 180-degree orientation key at
  printing clearance. Align front TP1 to the bezel's ground-wire relief.
- Measure legacy `Tube001` setting (22 mm diameter / 5 mm above PCB) and
  `Tube019` band (18.5 mm bore / 11 mm width) from the v1 native assembly.
  Use README photos for proportions, not calibrated dimensions. Keep the
  generated same-scale mesh/solid comparison and reference hashes current.
- Compact outer socket radius 12.45; socket 10.85; carrier 10.65; lug reach 11.45;
  groove reach 11.65 mm. Preserve at least 0.8 mm remaining outer track wall,
  radial running clearance and positive axial retention.
  Upper bezel diameter is 23.4 mm; band width remains 11 mm and wall 1 mm. This is still
  larger/taller than the original direct-contact body: do not claim exact fit
  or scale the cell/PCB to hide the difference.
- Cell is CR2032, **+ up**, nominal radius 10 and thickness 3.2 mm.
  Its positive top and case/rim must remain isolated from the inset negative
  bottom face. Negative tip is centred; upper positive tip is at the VCC XY.
- Use two Mill-Max 0965-0-15-20-80-14-11-0 SMT pins, opposite-facing, or rederive
  **every** bore/shoulder/mount/stack dimension for a replacement. Free height
  2.54, working compression 0.3048, full stroke 0.6096, barrel diameter 1.626,
  base 1.829 x 0.7112, no projecting tail, tip diameter 1.067 mm.
- Battery bottom/top Z = 3.9352/7.1352. Negative flange datum Z = 1.7;
  positive flange datum Z = 9.3704. PCB bottom/top = 9.4204/11.0204;
  bezel top = 12.2204 mm. Pin length tolerance +/-0.1524 plus **measured**
  +/-0.05 each cell/finished stack permits 0.0524..0.5572 mm compression.
  Do not assume ordinary prints or unsorted cells meet those budgets.
- Insulated ground lead fits below the PCB, outside the battery pocket.
  Nonconductive epoxy secures the pins without entering plungers. Black wire
  (jacket <=0.4 mm) passes through the side duct to front ground.
  Upper SMT base solders directly to rear VCC through a 0.05 mm solder land:
  three permanent joints, no red wire, no battery soldering. Do not claim a
  solderless PCB interface. Store black service slack in the underside groove.
  Two M1 x 4 bezel screws sit outside the battery extraction cylinder.
  Qualify the 0.5 mm well wall, 0.8 mm track wall, M1 threads and 1 mm lugs with
  a controlled PA12 process; these are not qualified coarse-FDM dimensions.
- The 20 mm cell cannot pass through the smaller PCB pocket. Remove the bezel
  and lift PCB/deck together using wire slack before extracting the battery.

## FreeCAD execution

Run the root-relative PowerShell commands:

```powershell
& hardware\v2.0\ring_3d\build.ps1
python -m unittest discover -s hardware\v2.0\ring_3d -p "test_design.py"
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_3d\test_freecad.py
```

For GUI regeneration run `build.FCMacro`. Import the local `lantern_ring`
module before restoring the FeaturePython document for editing. The three
exposed dimension overrides on `Parameters` recompute all affected shapes;
the full configuration is JSON. Transfer final GUI settings back to
`parameters.json` and regenerate **all** exports. Saved PCB geometry is a
snapshot: PCB changes require regeneration, not just FCStd recompute.

STLs are print-oriented and bed-aligned; STEP is in assembly coordinates.
Keep solid BOP checks, pairwise unintended-interference checks, insertion/twist
pose sweeps, incorrect-key rejection, locked pullout rejection, cell extraction,
tip/face contact tests and native/export roundtrips. Pogo/lead termination
overlap is intentional; no other collision is acceptable.

FreeCAD 0.19 / OCC 7.5 pitfalls: importing `FreeCAD` must precede `Part`;
refining the complex socket/carrier with `removeSplitter()` can damage curve-on-surface
geometry. Preserve its valid unrefined solid. STEP reader numerical checks use
an explicit 1e-5 mm tolerance, with unchanged volume and pre-normalization
topological validity. Weld duplicate mesh vertices, then require watertightness;
do not fill holes or discard faces to make a failed mesh appear printable.

## Completion criteria

Commit parameter/source changes alongside FCStd, assembly/per-part STEP,
per-part watertight STL, preview PNGs and the validation report. Ordinary Python
tests must pass and the report must match PCB/source hashes. Maintain assembly,
contact BOM, sourcing link and prototype limitations in the hardware README.

Virtual validation is not bench qualification. Require first-print fit,
adhesive/screw retention, wear/drop tests, wire-slack battery replacement,
loaded continuity/contact resistance, current/temperature and reverse/short
checks before wearing or release. No charging of a primary CR2032; adult
prototype only, with no battery-compartment certification claim.
