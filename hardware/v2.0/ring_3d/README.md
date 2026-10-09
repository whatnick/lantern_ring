# Lantern Ring v2: keyed twist-lock hardware

**Prototype, not a physically qualified product.** This design replaces the
monolithic v1 assembly with a removable PCB/battery cassette. It drops in, turns
30 degrees counterclockwise as viewed from above, and locks under three bayonet shelves.
One lug is wider to enforce orientation. The PCB sits in a profiled pocket in the
contact deck; **turn the cassette/bezel, never the PCB**.

![Assembled CAD](generated/assembly.png)
![Exploded CAD](generated/exploded.png)

![Assembly animation](generated/lantern_ring_v2_assembly.gif)

[Assembly animation MP4](generated/lantern_ring_v2_assembly.mp4): the exploded
stack drops into the carrier, the cassette inserts and twist-locks 30 degrees
under the Green Lantern (willpower) crown, and the LEDs light the crown lens.

![Same-scale comparison with the legacy ring](generated/legacy-comparison.png)

![Open-band elastic-fit curvature study](generated/flex-fit.png)

The [contact and metal-body roadmap](../../../docs/design/contact-roadmap/README.md)
explores solderless PCB pressure contacts and a floating metal shell with an
insulating cassette. Those renders are concepts, not replacement manufacturing
geometry or qualified electrical interfaces.

## Files and compatibility

`generated/Lantern_Ring_v2.FCStd` is the native editable FreeCAD assembly.
`Lantern_Ring_v2.step` includes printed parts and reference PCB, LED envelopes,
CR2032, pogo pins, the positive solder land and nominal insulated ground wire
route. Individual STEP files retain
assembly coordinates; individual STLs are in insertion orientation with their
lowest point on Z=0. `parameters.json` and `design.py` are the portable design
specification; `lantern_ring.py` is the FreeCAD implementation.

The supported board is **`../ring_mono/ring_mono.kicad_pcb` only**:
17.78 x 19.05 mm, 1.6 mm thick, with a ten-vertex asymmetric outline. This is not
the v1 17.78 mm octagon. The generator reads actual Edge.Cuts, pad nets and the
rear mask opening, rather than using a library bounding box that includes the
outline stroke. IR, v1 multi-colour and the unfinished DotStar board need their
own measured contact decks; they are not drop-in electrically compatible.

Default dimensions: **18.5 mm unloaded finger bore, 11 mm band width, 24.9 mm
maximum crown diameter and 11.2204 mm printed crown height above Z=0**.
The LEDs extend to Z=11.7204. The bore apex is raised to Z=0.3, so the true
**LED-inclusive profile above the finger is 11.4204 mm**, versus 12.7204 mm
for the previous closed-band design. Removing surplus negative-contact clearance
and reducing the bezel from 1.2 to 0.6 mm lowers the actual crown; the image
has not just been repositioned or rescaled.
The upper bezel is 23.4 mm across. These replace the oversized 36.4 mm diameter /
22.4 mm stack; neither PCB nor cell has been scaled.
Legacy 15.5/16.5/18.5/19.5 mm bore sizes can be regenerated; 15.5/16.5 mm
bores must reduce `fit_expansion` to 0.7 mm to stay within the free-arm strain screen.

### Measured legacy envelope and remaining difference

The reference is `hardware/v1.0/ring_3d/Lantern_Ring_Assembly.FCStd`:
`Tube001` (`setting`) has outer radius 11 mm and height 5 mm above the PCB
datum; `Tube019` (`ring_loop_185`) has a 9.25 mm bore radius, 10.25 mm outer radius
and 11 mm width. The compact band restores that **1 mm wall**, too.
The legacy 18.5 mm body STL is approximately 23.14 mm wide and 27.90 mm high.
README photographs corroborate the shallow crown/broad-band proportions, but
are not calibrated rulers. The generator measures these native objects and
records their source hashes; the comparison uses the real legacy mesh and new
printed solids at the **same scale**, with finger-bore centres aligned.

| Measured default 18.5 mm body | Legacy | Compact v2 |
| --- | ---: | ---: |
| Setting / upper bezel diameter | 22 mm | 23.4 mm |
| Maximum body width | ~23.14 mm | 24.9 mm |
| Overall printed-body height | ~27.90 mm | ~29.11 mm |
| Band width / wall | 11 / 1 mm | 11 tapering to 6 / 1 mm |
| Crown-to-band bracing | ~12-17 deg near-vertical plates, hollow | 40 deg hollow conical shoulders |

This is **not an exact 22 mm replacement**: the keyed polymer tracks need a
24.9 mm socket, 2.9 mm wider than the historical setting. The face lip is now
2.2 mm above the PCB underside, rather than 5 mm. Two spring contacts still add
4.4704 mm of working axial height around the unscaled 3.2 mm cell, so the
complete enclosure remains taller than the old direct-contact body. The old
5 mm face height and the new 11.2204 mm base-to-top stack have different datums
and must not be presented as equivalent measurements. Matching the complete
old envelope would require a different contact architecture, not uniform scaling.

### Open-bottom material-spring fit

The closed loop is replaced by **two continuous 1 mm-thick PA12 arms**, with a
60-degree bottom opening and 0.5 mm-radius end caps across the band width.
The unloaded tip gap is 8.75 mm. The top sits low on the circular finger
arc: the raised bore cuts into the crown underside, while a **continuous 0.5 mm
floor separates skin from the contact well**. Only the finger band is open; the
battery compartment is not.

### Braced shoulders and tapered comfort-fit band

Like the legacy body's slanted side plates, **hollow 1 mm conical shoulder walls**
brace the 24.9 mm crown overhang onto the band. Each wall leaves the crown
underside at its 12.45 mm rim and descends **40 degrees from the crown axis**
(`shoulder_angle`, validated 30-45 degrees), meeting the band 4.09 mm below the
crown, 61.7 degrees from its crest. The walls lean less steeply than the old
~12-17-degree plates, so they meet the band higher, keeping long free spring
arms. At 50 degrees from horizontal, they print without supports. The
triangular pockets between walls and band remain open front-to-back, saving
material and allowing powder removal.

Following common ring-profile practice (see
[MOH London ring profiles](https://www.mohlondon.com/guidance/design-basics/ring-profiles)),
the shank tapers on its lower side: one plane per side narrows the band from the
legacy **11 mm crest to 6 mm at the open tips** (`band_tip_width`). The long
edges are rounded to a **0.35 mm comfort-fit radius** (`band_edge_radius`).
The narrower, lower arms also make bending stress more uniform along the spring.
Net RingBase volume falls from 1194.3 to 1164.8 mm^3 (-2.5%), despite the
added bracing. OCC produces C0-continuity BSpline fillet faces; the validator
accepts only those flags, while every other BOP error, watertight-mesh check
and STEP round trip remains strict.

Elastic bending of these free arms supplies spring-back and fit preload; there
is no additional metal spring or adjustment screw. Start with a nominal bore
close to the measured finger size. A slightly smaller unloaded bore can supply
preload only after fit/force testing; do not force an undersized print onto a
finger or use elastic travel to compensate for a wrong ring size.

`fit_expansion = 1.0` is a **screening target**, not a certified 18.5-19.5 mm
size range. The illustration preserves neutral-axis arc length while widening
the opening to about 74.6 degrees. The simple curvature estimate
`strain = wall/2 * (1/R - 1/(R + expansion/2))`, with `R = (bore + wall)/2`,
gives approximately **0.250%** outer-fibre strain. The shoulders stiffen the
root, so a second screen assumes only the 88.3-degree free arm takes the same
tip rotation: `0.250% x 150 / 88.3 =` **0.425% free-arm strain**. Both omit root stress
concentration, contact loads, nonlinear geometry, residual print stresses,
anisotropy, creep and fatigue. It is not FEA or a spring-force prediction.
The 0.5% screen ceiling is a conservative design input, **not a published
PA12 cyclic allowable**.

Use a controlled ductile PA12 process for this spring geometry. The
[EOS PA 2200 material reference](https://store.eos.info/products/pa-2200-polyamide-12)
is a material-selection starting point, not a guarantee of elastic recovery.
Print an actual split-band coupon in the intended build orientation and finish,
cycle it on 18.5/19.0/19.5 mm gauges, and measure force, permanent set and recovery
before a worn trial. Repeat after warm/humid conditioning and sustained
deflection. Stop if the roots whiten/crack, the band takes a set, or fit is
painful/restricts circulation. No claimed skin compatibility or wear safety.
Do not copy the same thickness into resin, PLA or a metal body: their spring
stiffness and failure modes differ. Metal needs separately engineered arms.

## Rebuild and edit

On Windows, from the repository root:

```powershell
python -m unittest discover -s hardware\v2.0\ring_3d -p "test_design.py"
& hardware\v2.0\ring_3d\build.ps1
# If auto-discovery chooses the wrong FreeCAD installation:
& hardware\v2.0\ring_3d\build.ps1 -FreeCADPython 'C:\Program Files\FreeCAD 0.19\bin\python.exe'
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_3d\test_freecad.py
```

FreeCAD's **bundled Python**, not ordinary Python, must run the CAD generator.
No pip packages are needed: previews use FreeCAD's bundled NumPy and Qt.
The tool-neutral tests use ordinary Python 3.8+.
The initial artifacts were generated with FreeCAD 0.19 / OCC 7.5; rerun all
checks when moving to another version.

For GUI use, open and run `build.FCMacro` from this directory. It imports the
local feature module and builds the assembly. The native file contains
`Part::FeaturePython` parts linked to a `Parameters` object: change
`FingerDiameter`, `PCBClearance`, `LockAngle` or `BandGapAngle` and recompute
to update the solids. `bore_top` in the configuration is the bore-apex Z above
the original crown base plane; the default Z=0.3 retains the 0.5 mm floor and
meets the above-finger profile budget.
`Configuration` holds the other dimensions as JSON. Run the macro once in a
new FreeCAD session **before opening an existing FCStd for parametric editing**,
so FreeCAD can restore `lantern_ring.RingFeature`. The saved geometry and STEP
remain viewable without the Python module. GUI edits do not update exported
manufacturing files: copy intended settings into `parameters.json` and rebuild.

The PCB interface stored in FCStd is a snapshot. Regenerate from the KiCad file
after any PCB change. Commit source, native CAD, exports and `validation.json`
together; do not hand-edit generated geometry.

### Assembly animation (Blender 5)

`animation/render.ps1` exports every part from the FreeCAD model in its
assembled pose (`export_parts.py`, which also meshes the crown STEPs, so run
`crowns.py` first), builds and renders the scene in Blender 5 (`animate.py`,
EEVEE), encodes `generated/lantern_ring_v2_assembly.mp4` and `.gif` with ffmpeg
and renders the `generated/crowns/lineup.png` crown lineup:

```powershell
& hardware\v2.0\ring_3d\animation\render.ps1            # 1280x720, about 10 minutes
& hardware\v2.0\ring_3d\animation\render.ps1 -Preview   # 640x360 draft
# Single frames for review, written to animation\build\stills:
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b -P hardware\v2.0\ring_3d\animation\animate.py -- --preview --stills 1 100 200
```

The animation uses the Will (Green Lantern) crown in place of the plain bezel.
Colours are illustrative: the lower body is shown as emerald metal and the
crown as frosted translucent plastic. `animation/build/` holds the
intermediate meshes, `.blend` file and frames, and is not committed.

## Lantern Corps crowns (low-profile top piece)

![Lantern Corps crown lineup](generated/crowns/lineup.png)

The v1 emblem stood a 2 mm logo on 5 mm risers: 6.5 mm above the setting.
`crowns.py` replaces it with a **crown**: the validated bezel (same PCB-edge
clamp, M1 x 4 screws and ground-lead relief), a skirt that clears the LEDs by
0.2 mm, a 0.4 mm diffuser lens and a 0.6 mm raised logo. The crown top is
**2.3 mm above the PCB and 1.2 mm above the tallest LED** (12.62 mm profile
above the finger). Each crown is printed in one piece from translucent material
and is swapped by removing the two bezel screws.

Logos are traced from the per-corps sketches in
`hardware/v1.0/ring_3d/Lantern_Ring_Assembly.FCStd` into tool-neutral
`logos/logos.json` (closed even-odd loops in mm, centred on the ring axis) and
`logos/<corps>.svg`. They are pre-rotated by the 30-degree lock angle so they
read in the v1 orientation once locked, and clipped to the 23.4 mm bezel.

| Crown | Corps | Light | Volume (mm³) |
| --- | --- | --- | ---: |
| `will` | Green Lantern Corps | willpower | 497 |
| `fear` | Sinestro Corps | fear | 499 |
| `rage` | Red Lantern Corps | rage | 477 |
| `avarice` | Orange Lantern (Agent Orange) | avarice | 509 |
| `hope` | Blue Lantern Corps | hope | 520 |
| `compassion` | Indigo Tribe | compassion | 476 |
| `love` | Star Sapphires | love | 474 |
| `life` | White / Black Lantern | life and death | 491 |

`generated/crowns/Crown_<corps>.step` is in the cassette insertion frame (rotate
+30 degrees about Z for the locked pose; OCC 7.5 cannot round-trip the
rotated faceted solid). `Crown_<corps>.stl` is oriented **logo face down** for
printing: the relief prints first and the lens bridges it. `crowns.json`
records the validation (single valid solid, no interference with the locked
cassette, LED clearance, bezel diameter) and source hashes; `test_crowns.py`
checks it in CI.

```powershell
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_3d\crowns.py            # rebuild crowns
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_3d\crowns.py --extract  # re-trace logos from v1
python -m unittest discover -s hardware/v2.0/ring_3d -p "test_crowns.py"
```

**Not printed yet.** Lens light spread, 0.6 mm relief legibility and the 2.2 mm
counterbores that notch the crown rim need a test print.

## Printed parts and purchased parts

| Item | Quantity | Specification |
| --- | ---: | --- |
| RingBase | 1 | Braced, tapered comfort-fit split band and nested keyed bayonet socket |
| Carrier | 1 | Insulated battery well, negative pogo seat, lead channel, lugs |
| ContactDeck | 1 | Positive pogo seat and actual PCB pocket |
| Bezel | 1 | PCB-edge clamp and open optical window |
| Crown (optional) | 1 | Replaces Bezel: translucent Lantern Corps logo top piece, see [crowns](#lantern-corps-crowns-low-profile-top-piece) |
| Spring contact | 2 | Mill-Max **0965-0-15-20-80-14-11-0**, surface mount ([alternatives](../../../docs/design/pogo-pin-comparison.md)) |
| CR2032 | 1 | Primary 3 V cell, nominal 20 x 3.2 mm |
| Insulated flexible wire | 1 | Fine-stranded wire, **jacket OD <=0.4 mm**, black |
| Bezel screw | 2 | M1 x 4 mm plastic-compatible thread, head OD <=2 mm |
| Anti-unlock screw | 1 | M1 x 2 mm plastic-compatible thread, low-profile head |
| Pin-retaining adhesive | Small amount | Nonconductive, electronics-compatible epoxy |

Use a dimensionally controlled PA12 process for the compact parts, not brittle
decorative resin. The battery well has a 0.5 mm wall and the outer track wall is
0.8 mm: this is **not a drop-in coarse FDM print**. Qualify these small walls,
the 1 mm lugs, 0.6 mm bezel and M1 threads on coupons before printing the ring.
RingBase needs appropriate supports under the crown and track
roofs; its Z=0 STL position is not a promise of support-free printing. The deck
and bezel are naturally base-down. Deburr/smooth skin-facing band edges and all
track mouths. Do not paint contact pockets or functional sliding surfaces.

Nominal clearances: 0.20 mm carrier/socket radial, 0.25 mm PCB per edge,
0.15 mm cell radial, 0.20 mm lug/track axial, 2 degrees at
each lug flank. Measure a first print and calibrate for the printer; do not force
an interference fit against the PCB or battery. Ream small holes as necessary.
The 1.75 mm barrel bore must remain smaller than the 1.829 mm flange: do not
drill through the retaining shoulder. Epoxy is required to retain the pins under
spring load; printed shoulders alone do not secure both directions. The upper deck rests
on the carrier shoulder; its two side notches clear the external screw towers.

## Electrical interface and soldering

**CR2032 positive (+) face UP.** Positive case/rim belongs to VCC; the inset
negative face points down. Never rely on the rim as a ground contact.

| Circuit path | Physical connection |
| --- | --- |
| Positive | Downward-facing SMT pogo at CAD (0, +0.381) touches the + top face; its base is soldered directly to the rear exposed VCC circle |
| Negative | Upward-facing lower SMT pogo at CAD (0, 0) touches the centre of the inset - bottom face; black lead joins its base to front **TP1 `/GND`** |

CAD XY origin is KiCad (136.906, 83.185) mm. CAD +Y is KiCad -Y, without
mirroring the board. TP1 is CAD (-0.0254, +7.493). The rear exposed VCC circle
has radius 2.962124 mm; it is **not ground**.

The [manufacturer drawing, page 24](https://www.mill-max.com/sites/default/files/external/assets/2020-04/ultra_low_profile_spring_pins_rev._04.14.20.pdf)
specifies 2.54 mm free height, 0.3048 mm mid-stroke, 0.6096 mm full stroke,
1.626 mm barrel, 1.829 mm base, 0.7112 mm base height and 1.067 mm tip.
There is **no projecting solder tail**. The CAD uses a conservative stepped
external envelope (body height = free height minus full stroke), not internal
pin construction. A 0.05 mm solder land models the direct positive PCB joint.
Both tips are nominally compressed 0.3048 mm. The combined budget is
**+/-0.2524 mm**, allowing 0.0524-0.5572 mm compression.
Supplier dimensions and cell tolerances must be checked again for substitutions.

The pin length allowance is the manufacturer's +/-0.006 inch (+/-0.1524 mm).
The other allowances are **requirements**, not assumed printer or CR2032
capabilities: measure/sort cells to +/-0.05 mm and finish/shim the assembled
contact stack to +/-0.05 mm. Ordinary +/-0.2 mm printing/cell allowances would
lose preload or bottom out these short pins. Do not use a build outside those
measured budgets. The first-build qualification must measure each pin's free
height and both actual compressed gaps.

There is **no soldering to the battery** and no solder work for routine battery
replacement. The compact assembly needs **three permanent joints**: upper SMT
pin to rear VCC, black wire to lower pin base, and black wire to TP1. This removes
the red wire and one joint compared with the previous four-joint loom; it is
not a solderless retrofit to the unmodified PCB.

Start with approximately 35-40 mm black lead, then trim during dry assembly.
Leave 8-10 mm black service slack folded in the 3 mm wide underside
channel so the board/deck can lift for cell replacement. The CAD wire shapes are
nominal jacket-routing envelopes, not bend-radius or service-loop simulations.
Use strain relief on insulated wire, never on plungers. Keep solder, epoxy and
flux off spring tips and out of barrels. Insulate the lower base joint. Nothing conductive may bridge
the cell's negative face to its positive case.

## Assembly and service

1. Dry-fit all four prints without a cell. Check the wide key, insertion,
   counterclockwise turn, end stop and anti-unlock screw alignment.
2. Install the lower pogo upward through the Carrier's underside counterbore;
   seat its flange and bond the barrel/flange without contaminating its travel.
   Solder the upper SMT pin base squarely to the PCB's rear VCC land, then
   lower it into the deck counterbore. Its spring points down. Secure its barrel
   to the deck without loading the solder pad in service. Let adhesive cure fully.
3. Build/fit the black lead, with the battery absent. Connect it to
   front TP1 `/GND` and the lower SMT base. Check continuity from
   each tip to its intended pad and absence of a VCC/GND short.
4. Insert the cell **+ up**, lower the deck into the open carrier, and seat the
   PCB component-side up with TP1 aligned to the ground-wire relief. Keep slack in the underside
   channel and route black through the bezel's ground-pad relief.
5. Fit the bezel and two M1 x 4 screws into the carrier towers; tighten
   gently, without bending the PCB or stripping the plastic. They retain both
   PCB and deck. Check that the leads are not pinched.
6. Align the wide lug with its wide slot, lower the cassette until seated,
   turn counterclockwise 30 degrees, then install the M1 x 2 anti-unlock screw through
   the radial crown hole into the wide lug's pilot. **The screw is mandatory**:
   friction alone is not an anti-rotation latch.

The **cassette** has positive orientation keying (24/14/14-degree lugs), not the
bare PCB: printing clearance can accommodate a 180-degree reversed board in the
profiled pocket. Align TP1 to the bezel relief and verify the contact loom;
do not rely on the PCB outline alone to establish electrical orientation.

To replace the cell, remove the anti-unlock screw, turn the cassette back
30 degrees and lift it out. Remove the two bezel screws, lift the PCB/deck
together with the available wire slack, and lift the old cell from the open
well. Reassemble with a fresh cell; no contact joints are disturbed. The deck
must lift: a 20 mm battery cannot pass through the smaller PCB pocket.

## Validation and release gates

The generator fails on invalid parameter stacks, failed FreeCAD booleans,
unintended assembled interference, non-solid printed parts, or nonwatertight
STLs. It samples axial insertion, the complete twist, both incorrect key
orientations, locked axial withdrawal, cell extraction, and both battery tip
planes. STEP and STL files are re-imported, and FCStd is reopened/recomputed.
It also checks the full-width bottom opening, retained finger-side floor and
the LED-inclusive above-finger height. STEP volume must agree within 0.01 mm^3.
OCC 7.5 STEP curve-on-surface checks
use an explicit 0.00001 mm numerical tolerance; this is not a print allowance.
`generated/validation.json` records the parameters, PCB hash and check results.
`test_freecad.py` restores the document in a fresh process and verifies that
finger bore, bottom-opening angle, PCB clearance and twist-angle edits really
recompute. The CI job
runs the portable tests and provenance checks; it does not run FreeCAD itself.

**Still required on the bench:** split-arm force/recovery, root strain, creep/
fatigue and gauge-fit testing; printer fit coupons/full first article; screw
pullout, adhesive retention, lock wear/drop resistance, pin force/travel across
actual cell tolerances, wire-slack service trial, contact resistance under load,
LED current and temperature, and short/reverse-insertion checks with a
current-limited source before inserting a cell. This revision has not been
printed or tested electrically.

The mono PCB has no explicit LED series-current limiter; do not assume battery
internal resistance or the pogo pin's ampere rating makes it safe. Qualify the
chosen LEDs/cell and add an appropriate current-limiting circuit if needed
before wearing or distributing the assembly. The enclosure is not waterproof,
does not charge cells, and provides no automatic reverse-polarity protection.
**Never charge a CR2032**, including with the repository's speculative Qi ideas.
Coin cells are an ingestion hazard: this is an adult prototype, not a toy.
Screw retention is not a claim of compliance with battery-compartment standards.
