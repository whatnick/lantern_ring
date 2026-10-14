---
name: lantern-ring-freecad
description: Rebuild and modify Lantern Ring v2 FreeCAD hardware, including the keyed bayonet PCB cassette, CR2032 pogo contacts, insulation, print exports, and mechanical validation.
---

# Lantern Ring FreeCAD reconstruction

The contact/material ideation roadmap is `docs/design/contact-roadmap/README.md`.
Its copper-foil, plated-leaf and metal-shell illustrations are not validated
replacement geometry. Keep the metal shell floating and retain a continuous
insulating contact/battery insert unless a separately reviewed design changes it.

The ATtiny85 IR board's programming fixture is a KiCad generator, not FreeCAD:
see `hardware/v2.0/ring_ir_prog_clip/README.md`. Do not reuse the mono-board
contact map for it.

Use this skill for Lantern Ring enclosure, PCB fit, battery contacts, FreeCAD
regeneration, printing or mechanical review. Work from
`hardware/v2.0/ring_3d/README.md`, `parameters.json`, `design.py` and
`lantern_ring.py`; the values below are reconstruction invariants, not permission
to replace measured geometry with a generic circle.

## Tool-neutral design invariants

- The supported mono PCB has a **17.78 x 19.05 x 0.8 mm** (read the board thickness from the PCB; do not assume 1.6) ten-vertex profile.
  Derive vertices from its real Edge.Cuts. KiCad (136.906, 83.185) is CAD XY zero;
  convert `(x, y)` to `(x - 136.906, 83.185 - y)`. Do not mirror the board.
- Front TP1 `/GND` is CAD (-0.0254, +7.493). Rear exposed VCC is
  CAD (0, +0.381), radius 2.962124. Preserve net/filled-copper/mask verification.
  Other board variants have different contact assignments.
- Four prints: band/socket RingBase, bayonet Carrier, removable ContactDeck
  and screw-retained Bezel. The **entire cassette rotates**, not bare PCB edges.
- Three lugs at 0/120/240 degrees have widths 24/14/14 degrees. Slots add
  2 degrees per flank; 30-degree counterclockwise twist seats them under shelves.
  The wide lug cannot enter either narrow slot. The radial M1 anti-unlock screw was
  removed (its pilot broke the 1 mm wall rule); locking is pogo preload plus friction,
  and a detent is an open item.
- The PCB pocket is profiled, not a positive 180-degree orientation key at
  printing clearance. Align front TP1 to the bezel's ground-wire relief.
- Measure legacy `Tube001` setting (22 mm diameter / 5 mm above PCB) and
  `Tube019` band (18.5 mm bore / 11 mm width) from the v1 native assembly.
  Use README photos for proportions, not calibrated dimensions. Keep the
  generated same-scale mesh/solid comparison and reference hashes current.
- Compact outer socket radius 13.75; socket 11.85; carrier 11.5; lug reach 12.45;
  groove reach 12.65 mm. Preserve at least 1.05 mm remaining outer track wall,
  radial running clearance and positive axial retention.
  Upper bezel diameter is 27.1 mm; band width remains 11 mm and wall is 1.1 mm. This is still
  larger/taller than the original direct-contact body: do not claim exact fit
  or scale the cell/PCB to hide the difference.
- The band is OPEN at the bottom: two 1.1 mm PA12 arms, 60-degree missing sector,
  0.5 mm-radius caps and unloaded tip gap 8.7 mm. Build from continuous arcs
  and end-cap arcs, not tangent unions that leave nonwatertight mesh seams.
  Raise the bore apex to Z=0.3 and cut it from the crown underside: the band
  centre is `0.3 - bore/2`. Preserve a continuous >=1.05 mm insulating floor.
  Opening is in the finger band only, never through the battery compartment.
  `BandGapAngle` is an editable native property.
- Hollow 1.2 mm conical shoulder walls (`shoulder_angle` 30-45 deg from the crown
  axis, default 40) run from the 13.75 mm crown rim to the band, like the legacy
  slanted side plates; keep the front-to-back pockets open (material, powder
  removal). `design.shoulder()` gives the meet point (67.5 deg from crest).
- Lower shank tapers on one plane per side from 11 mm at the crest to
  `band_tip_width` 6 mm, then `makeFillet(band_edge_radius=0.35)` on all band
  edges for a comfort-fit profile. A kinked taper makes the fillet invalid. OCC
  fillets here are C0 BSplines: use `bop_check()` (tolerates only C0 flags) and
  `exact_bounds()` (BoundBox is loose on BSplines) rather than relaxing checks.
- Material elasticity supplies fit spring-back, not an extra mechanical spring.
  `fit_expansion=1` is an unqualified screen. Preserve neutral-axis arc length
  for the illustration; `wall/2 * (1/R - 1/(R + expansion/2))` gives 0.250%
  nominal strain (0.272%), not root strain or allowable fatigue. Shoulders stiffen the
  root: `free_arm_strain` scales it by arm/free-arm angle (0.495%), with a 0.5%
  ceiling; 15.5/16.5 mm bores need `fit_expansion` 0.6. No qualified size range,
  spring force or wearable safety claim without PA12 coupon/force/creep tests.
- Cell is CR2032, **+ up**, nominal radius 10 and thickness 3.2 mm.
  Its positive top and case/rim must remain isolated from the inset negative
  bottom face. Negative tip is centred; upper positive tip is at the VCC XY.
- Use two Mill-Max 0965-0-15-20-80-14-11-0 SMT pins, opposite-facing, or rederive
  **every** bore/shoulder/mount/stack dimension for a replacement. Free height
  2.54, working compression 0.3048, full stroke 0.6096, barrel diameter 1.626,
  base 1.829 x 0.7112, no projecting tail, tip diameter 1.067 mm.
- Battery bottom/top Z = 4.1352/7.3352. Negative flange datum Z = 1.9;
  positive flange datum Z = 9.5704. PCB bottom/top = 9.6204/10.4204;
  bezel top = 11.5204 mm. Include the LEDs at Z=11.5204: true above-finger
  profile is 11.2204 mm, not just bezel height. Pin length tolerance +/-0.1524 plus **measured**
  +/-0.05 each cell/finished stack permits 0.0524..0.5572 mm compression.
  Do not assume ordinary prints or unsorted cells meet those budgets.
- Insulated ground lead fits below the PCB, outside the battery pocket.
  Nonconductive epoxy secures the pins without entering plungers. Black wire
  (jacket <=0.4 mm) passes through the side duct to front ground.
  Upper SMT base solders directly to rear VCC through a 0.05 mm solder land:
  three permanent joints, no red wire, no battery soldering. Do not claim a
  solderless PCB interface. Store black service slack in the underside groove.
  Two M1 x 4 bezel screws sit outside the battery extraction cylinder.
  Qualify the 1.1 mm well wall, 1.05 mm track wall, M1 threads and 1.2 mm lugs with
  a controlled PA12 process; these are not qualified coarse-FDM dimensions.
- The 20 mm cell cannot pass through the smaller PCB pocket. Remove the bezel
  and lift PCB/deck together using wire slack before extracting the battery.

## Print-wall (DRC) rule

- Elecrow rejected walls under 1 mm. Every printed wall must be >= `min_printed_wall`
  (1.0) with a 0.05 mm design margin: nominal walls are >= 1.05 mm because the
  exact 1.00 value was still flagged. `design.validate_parameters` enforces this
  for the track, pillars, well, floors, plate, band and shoulders.
- `printcheck.py` is the STL DRC (numpy only): `python printcheck.py generated\*.stl`.
  The build and crown generators call `check_stl` and fail on thin walls;
  `test_printcheck.py` gates committed STLs in CI. Crown relief strokes are held to
  `relief_min_width` 0.4 mm; plate, skirt and lens stay >= 1.05 mm.
- Fill solid rather than thinning cavities; use open grooves and through slots
  instead of covered channels. Re-run `lantern_ring.py` then `crowns.py` after any
  edit (provenance hashes) and keep the thin-wall region out of the cassette stack.

## FreeCAD execution

Run the root-relative PowerShell commands:

```powershell
& hardware\v2.0\ring_3d\build.ps1
python -m unittest discover -s hardware\v2.0\ring_3d -p "test_design.py"
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_3d\test_freecad.py
```

For GUI regeneration run `build.FCMacro`. Import the local `lantern_ring`
module before restoring the FeaturePython document for editing. The four
exposed dimension overrides on `Parameters` recompute all affected shapes;
the full configuration is JSON. Transfer final GUI settings back to
`parameters.json` and regenerate **all** exports. Saved PCB geometry is a
snapshot: PCB changes require regeneration, not just FCStd recompute.

STLs are print-oriented and bed-aligned; STEP is in assembly coordinates.
Keep solid BOP checks, pairwise unintended-interference checks, insertion/twist
pose sweeps, incorrect-key rejection, locked pullout rejection, cell extraction,
tip/face contact tests and native/export roundtrips. Pogo/lead termination
overlap is intentional; no other collision is acceptable.
Check the open bottom across the entire band width, the retained finger-side
floor and highest-LED profile. Regenerate `flex-fit.png` with its unqualified
curvature-screen labels, never present it as deformation FEA.

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

Virtual validation is not bench qualification. Require split-arm force/recovery,
root strain, sustained-deflection creep and fatigue tests as well as first-print fit,
adhesive/screw retention, wear/drop tests, wire-slack battery replacement,
loaded continuity/contact resistance, current/temperature and reverse/short
checks before wearing or release. No charging of a primary CR2032; adult
prototype only, with no battery-compartment certification claim.
