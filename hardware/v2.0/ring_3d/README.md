# Lantern Ring v2: keyed twist-lock hardware

**Prototype, not a physically qualified product.** This design replaces the
monolithic v1 assembly with a removable PCB/battery cassette. It drops in, turns
30 degrees counterclockwise as viewed from above, and locks under three bayonet shelves.
One lug is wider to enforce orientation. The PCB sits in a profiled pocket in the
contact deck; **turn the cassette/bezel, never the PCB**.

![Assembled CAD](generated/assembly.png)
![Exploded CAD](generated/exploded.png)

The [contact and metal-body roadmap](../../../docs/design/contact-roadmap/README.md)
explores solderless PCB pressure contacts and a floating metal shell with an
insulating cassette. Those renders are concepts, not replacement manufacturing
geometry or qualified electrical interfaces.

## Files and compatibility

`generated/Lantern_Ring_v2.FCStd` is the native editable FreeCAD assembly.
`Lantern_Ring_v2.step` includes printed parts and reference PCB, LED envelopes,
CR2032, pogo pins and nominal insulated wire routes. Individual STEP files retain
assembly coordinates; individual STLs are in insertion orientation with their
lowest point on Z=0. `parameters.json` and `design.py` are the portable design
specification; `lantern_ring.py` is the FreeCAD implementation.

The supported board is **`../ring_mono/ring_mono.kicad_pcb` only**:
17.78 x 19.05 mm, 1.6 mm thick, with a ten-vertex asymmetric outline. This is not
the v1 17.78 mm octagon. The generator reads actual Edge.Cuts, pad nets and the
rear mask opening, rather than using a library bounding box that includes the
outline stroke. IR, v1 multi-colour and the unfinished DotStar board need their
own measured contact decks; they are not drop-in electrically compatible.

Default dimensions: 18.5 mm finger bore, 7 mm band width, 36.4 mm crown diameter,
22.4 mm crown height above the base plane. The crown is intentionally chunky:
it reserves room for two opposite-face spring contacts, insulated wires and
service access rather than hiding these inside a nominal battery-sized cavity.
Legacy 15.5/16.5/18.5/19.5 mm bore sizes can be regenerated.

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
`FingerDiameter`, `PCBClearance` or `LockAngle` and recompute to update the solids.
`Configuration` holds the other dimensions as JSON. Run the macro once in a
new FreeCAD session **before opening an existing FCStd for parametric editing**,
so FreeCAD can restore `lantern_ring.RingFeature`. The saved geometry and STEP
remain viewable without the Python module. GUI edits do not update exported
manufacturing files: copy intended settings into `parameters.json` and rebuild.

The PCB interface stored in FCStd is a snapshot. Regenerate from the KiCad file
after any PCB change. Commit source, native CAD, exports and `validation.json`
together; do not hand-edit generated geometry.

## Printed parts and purchased parts

| Item | Quantity | Specification |
| --- | ---: | --- |
| RingBase | 1 | Band and keyed bayonet socket |
| Carrier | 1 | Insulated battery well, negative pogo seat, lead channel, lugs |
| ContactDeck | 1 | Positive pogo seat and actual PCB pocket |
| Bezel | 1 | PCB-edge clamp and open optical window |
| Spring contact | 2 | Mill-Max **0906-1-15-20-75-14-11-0** |
| CR2032 | 1 | Primary 3 V cell, nominal 20 x 3.2 mm |
| Insulated flexible wire | 2 | 30 AWG or similar, **jacket OD <=0.8 mm**, red/black |
| Bezel screw | 3 | M1.6 x 8 mm plastic-compatible thread, pan head OD <=3.4 mm |
| Anti-unlock screw | 1 | M2 x 4 mm plastic-compatible thread, low-profile head |
| Pin-retaining adhesive | Small amount | Nonconductive, electronics-compatible epoxy |

Use PETG or PA12 for the load-bearing parts, not brittle decorative resin.
Start with 0.15-0.20 mm layers, at least four perimeters, and 100% infill around
the bayonet lugs. RingBase needs appropriate supports under the crown and track
roofs; its Z=0 STL position is not a promise of support-free printing. The deck
and bezel are naturally base-down. Deburr/smooth skin-facing band edges and all
track mouths. Do not paint contact pockets or functional sliding surfaces.

Nominal clearances: 0.30 mm carrier/socket radial, 0.25 mm PCB per edge, 0.25 mm
deck/pocket radial, 0.30 mm cell radial, 0.30 mm lug/track axial, 2 degrees at
each lug flank. Measure a first print and calibrate for the printer; do not force
an interference fit against the PCB or battery. Ream small holes as necessary.
The 1.75 mm barrel bore must remain smaller than the 1.829 mm flange: do not
drill through the retaining shoulder. Epoxy is required to retain the pins under
spring load; printed shoulders alone do not secure both directions.

## Electrical interface and soldering

**CR2032 positive (+) face UP.** Positive case/rim belongs to VCC; the inset
negative face points down. Never rely on the rim as a ground contact.

| Circuit path | Physical connection |
| --- | --- |
| Positive | Downward-facing upper pogo at CAD (0, +0.381) touches the + top face; red lead connects its tail to the rear exposed VCC circle |
| Negative | Upward-facing lower pogo at CAD (0, 0) touches the centre of the inset - bottom face; black lead follows the underside/side channel to front **TP1 `/GND`** |

CAD XY origin is KiCad (136.906, 83.185) mm. CAD +Y is KiCad -Y, without
mirroring the board. TP1 is CAD (-0.0254, +7.493). The rear exposed VCC circle
has radius 2.962124 mm; it is **not ground**.

The [manufacturer drawing](https://www.mill-max.com/products/datasheet/0906-1-15-20-75-14-11-0)
specifies 4.496 mm free height, 0.711 mm recommended compression, 1.397 mm full
stroke, 1.499 mm barrel, 1.829 mm flange, 0.432 x 1.753 mm solder tail and
1.067 mm rounded tip. The CAD includes these envelopes, not an arbitrary generic
pogo cylinder. Both tips are nominally compressed 0.711 mm. The conservative
print/cell/pin stack allows 0.161-1.261 mm compression, below full stroke.
Supplier dimensions and cell tolerances must be checked again for substitutions.

There is **no soldering to the battery** and no solder work for routine battery
replacement. A bare-pin loom needs four permanent joints: two wire-to-pin tails
and two wire-to-PCB pads. A supplier-prewired loom leaves only the two PCB joints.
This reduces repeated soldering; it does **not** claim fewer first-build joints
or a solderless retrofit to the unmodified PCB.

Start with approximately 12 mm red lead and 45-50 mm black lead, then trim during
dry assembly. Leave 8-10 mm black service slack folded in the 3 mm wide underside
channel so the board/deck can lift for cell replacement. The CAD wire shapes are
nominal jacket-routing envelopes, not bend-radius or service-loop simulations.
Use strain relief on insulated wire, never on plungers. Keep solder, epoxy and
flux off spring tips and out of barrels. Insulate exposed tail joints; route
the red tail loop in the cavity below the PCB. Nothing conductive may bridge
the cell's negative face to its positive case.

## Assembly and service

1. Dry-fit all four prints without a cell. Check the wide key, insertion,
   counterclockwise turn, end stop and anti-unlock screw alignment.
2. Install the lower pogo upward through the Carrier's underside counterbore;
   seat its flange and bond the barrel/flange without contaminating its travel.
   Install the upper pogo downward through the ContactDeck's counterbore in the
   same way. Let the adhesive cure fully.
3. Build/fit the insulated loom, with the battery absent. Connect black to
   front TP1 `/GND`, red to the exposed rear VCC circle. Check continuity from
   each tip to its intended pad and absence of a VCC/GND short.
4. Insert the cell **+ up**, lower the deck into the open carrier, and seat the
   PCB component-side up with TP1 aligned to the ground-wire relief. Keep slack in the underside
   channel and route black through the bezel's ground-pad relief.
5. Fit the bezel and three M1.6 x 8 screws into the carrier towers; tighten
   gently, without bending the PCB or stripping the plastic. They retain both
   PCB and deck. Check that the leads are not pinched.
6. Align the wide lug with its wide slot, lower the cassette until seated,
   turn counterclockwise 30 degrees, then install the M2 x 4 anti-unlock screw through
   the radial crown hole into the wide lug's pilot. **The screw is mandatory**:
   friction alone is not an anti-rotation latch.

The **cassette** has positive orientation keying (24/14/14-degree lugs), not the
bare PCB: printing clearance can accommodate a 180-degree reversed board in the
profiled pocket. Align TP1 to the bezel relief and verify the contact loom;
do not rely on the PCB outline alone to establish electrical orientation.

To replace the cell, remove the anti-unlock screw, turn the cassette back
30 degrees and lift it out. Remove the three bezel screws, lift the PCB/deck
together with the available wire slack, and lift the old cell from the open
well. Reassemble with a fresh cell; no contact joints are disturbed. The deck
must lift: a 20 mm battery cannot pass through the smaller PCB pocket.

## Validation and release gates

The generator fails on invalid parameter stacks, failed FreeCAD booleans,
unintended assembled interference, non-solid printed parts, or nonwatertight
STLs. It samples axial insertion, the complete twist, both incorrect key
orientations, locked axial withdrawal, cell extraction, and both battery tip
planes. STEP and STL files are re-imported, and FCStd is reopened/recomputed.
STEP volume must agree within 0.01 mm^3. OCC 7.5 STEP curve-on-surface checks
use an explicit 0.00001 mm numerical tolerance; this is not a print allowance.
`generated/validation.json` records the parameters, PCB hash and check results.
`test_freecad.py` restores the document in a fresh process and verifies that
finger bore, PCB clearance and twist-angle edits really recompute. The CI job
runs the portable tests and provenance checks; it does not run FreeCAD itself.

**Still required on the bench:** printer fit coupons/full first article, screw
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
