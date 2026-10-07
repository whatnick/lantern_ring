# Lantern Ring contributor instructions

This is an open-hardware electronic jewellery project, licensed under OSHW TAPR
as linked in the root README. Preserve historical designs and their assets.

## Repository map

- `hardware/v1.0`: legacy multi-colour PCB, native FreeCAD assembly and logo STLs.
- `hardware/v2.0/ring_mono`: current mono-colour PCB and existing fabrication data.
- `hardware/v2.0/ring_pcb_IR`: separate ATtiny85/IR design, not the mono contact map.
- `hardware/v2.0/ring_pcb_dotstar`: incomplete APA102 experiment, not production.
- `hardware/v2.0/ring_3d`: v2 keyed bayonet cassette source and generated artifacts.
- `firmware/Arduino-TV-B-Gone`: legacy firmware; keep unrelated behaviour unchanged.
- `software/materialator`: independent STL volume/metal-weight experiment.
- `docs/design`: electrical proposals and repository review notes.
- `docs/design/contact-roadmap`: concept renders, Nano Banana prompts/client and
  metal/contact ideation; not manufacturing CAD. Preserve image provenance and
  distinguish local FreeCAD output from AI-generated images.

## Mechanical work

Read `hardware/v2.0/ring_3d/README.md` and load the
`lantern-ring-freecad` repository skill for enclosure/contact changes.
`parameters.json` is the dimension source; `design.py` derives the real PCB
interface; `lantern_ring.py` builds editable FreeCAD features and validates them.
Do not hand-edit generated FCStd/STEP/STL files, resize a board to fit an assumed
envelope, or reuse the v1 octagon/contact assignments for another board.

Use millimetres. CAD +Y is KiCad -Y. Battery + face is up; the central rear
exposed mono PCB circle is VCC, and front TP1 is `/GND`. Two spring contacts
touch opposite battery faces. Keep cell negative face isolated from its positive
rim, insulate SMT base joints/wires and preserve preload below maximum stroke.
The compact build uses 0965 SMT pins: upper base directly soldered to rear VCC,
one ground lead, three permanent joints. Measure the legacy native setting and
band before envelope changes; preserve the 11 mm band width and 1 mm band wall.
Keep `legacy-comparison.png` and measured reference hashes current. The short
pins require measured +/-0.05 mm cell/finished-stack budgets; do not assume
unmeasured prints meet them or describe the 24.9 mm socket as an exact 22 mm fit.
The finger band is now split into rounded PA12 arms with a 60-degree bottom
gap; do not restore a rigid closed loop. Hollow 30-45 degree conical shoulder
walls brace the crown onto the band, and the shank tapers from 11 mm to 6 mm
with comfort-fit rounded edges; keep the pockets hollow. Its elastic-fit study is a curvature
screen, not a verified size range or force/creep model. Keep the battery well
closed and a continuous >=0.5 mm floor above the nested finger bore. Measure
the highest LED, not just the bezel, when checking above-finger profile.
Metal versions need separately designed spring arms and continuous insulation.
The carrier, not the PCB, takes twist load. Preserve the asymmetric key, track
shelves and mandatory anti-unlock screw.
PCB printing clearance permits reversed insertion: align TP1 to the ground-wire
relief instead of treating the board outline as an electrical orientation key.

Use standard-library Python 3.8+ for portable interface tests. Run CAD with
FreeCAD's bundled Python, not the system interpreter:

```powershell
& hardware\v2.0\ring_3d\build.ps1
python -m unittest discover -s hardware\v2.0\ring_3d -p "test_design.py"
```

On Windows use backslash filesystem paths. Do not add dependencies unless
necessary. Check source, native CAD and exports together, including
`generated/validation.json`. An invalid solid/export or collision is a failure,
not an exception to suppress. Editable dimensions must actually recompute.
Never describe virtual checks as physical fit or electrical qualification.

## Electrical and Git discipline

Preserve the schematics, routing and committed Gerbers unless the electrical
task requires changes. After an electrical change, run the installed
`kicad-cli pcb drc` and `kicad-cli sch erc` and inspect every report; regenerate
fabrication data only from the revised board. Avoid committing editor-local
`.kicad_prl` changes caused by validation tools. Keep baseline warnings distinct
from new errors and do not claim the DotStar experiment is routed.

Never solder directly to or charge a primary CR2032. No physical design is
release-ready until contact load/current/temperature, cell safety and mechanical
retention have been tested. Do not assume coin-cell resistance is an LED limiter.

Review before merging. Preserve unmerged feature work as explicitly experimental
when appropriate; don't delete branches until their tips are reachable from
`main`. Never discard user edits or rewrite history to manufacture a clean tree.
Keep unrelated firmware/software fixes separate from enclosure work.
