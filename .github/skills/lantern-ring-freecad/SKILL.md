---
name: lantern-ring-freecad
description: Rebuild and modify Lantern Ring v2 FreeCAD hardware, including the keyed bayonet PCB cassette, CR2032 pogo contacts, insulation, print exports, and mechanical validation.
---

# Lantern Ring FreeCAD reconstruction

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
  The wide lug cannot enter either narrow slot. A radial M2 x 4 screw at the
  locked wide lug prevents accidental counterrotation; it is mandatory.
- The PCB pocket is profiled, not a positive 180-degree orientation key at
  printing clearance. Align front TP1 to the bezel's ground-wire relief.
- Default outer crown radius 18.2; socket 15.3; carrier 15.0; lug reach 16.6;
  groove reach 16.95 mm. Preserve at least 1.2 mm remaining outer track wall,
  radial running clearance and positive axial retention.
- Cell is CR2032, **+ up**, nominal radius 10 and thickness 3.2 mm.
  Its positive top and case/rim must remain isolated from the inset negative
  bottom face. Negative tip is centred; upper positive tip is at the VCC XY.
- Use two Mill-Max 0906-1-15-20-75-14-11-0 pins, opposite-facing, or rederive
  **every** bore/shoulder/tail/stack dimension for a replacement. Free height
  4.496, working compression 0.711, full stroke 1.397, barrel diameter 1.499,
  flange 1.829 x 0.406, tail 0.432 x 1.753, tip diameter 1.067 mm.
- Battery bottom/top Z = 8.0/11.2. Negative flange datum Z = 4.215;
  positive flange datum Z = 14.985. PCB bottom/top = 17.8/19.4;
  bezel top = 22.4 mm. A +/-0.55 mm conservative combined stack gives
  0.161..1.261 mm compression: always retain preload and avoid bottoming out.
- Insulated tails and leads fit below the PCB, outside the battery pocket.
  Nonconductive epoxy secures the pins without entering plungers. Black wire
  passes through the side duct to front ground; red connects to rear VCC.
  Four permanent joints for a bare-pin loom; no battery soldering. Do not claim
  a solderless PCB interface. Store black service slack in the underside groove.
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
refining the complex socket with `removeSplitter()` can damage curve-on-surface
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
