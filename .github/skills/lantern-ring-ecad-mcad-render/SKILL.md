---
name: lantern-ring-ecad-mcad-render
description: Export actual Lantern Ring KiCad boards into checked FreeCAD assemblies and Blender assembly animations, including the IR programming clip, pad/net verification, coordinate frames, provenance and measured versus estimated geometry.
---

# Lantern Ring ECAD / MCAD / render flow

Use this skill for actual PCB visuals, programming-clip reconstruction and
assembly animations. Read `hardware\v2.0\ring_ir_prog_clip\development.md`.
For enclosure or battery-contact changes also use `lantern-ring-freecad`.
Run commands from the repository root; use backslash filesystem paths on Windows.

## Source hierarchy and tool-neutral invariants

- The existing IR PCB is authoritative for outline, thickness, pads, nets,
  mask openings and component clearances. Do not move its pads to suit a jig.
  Preserve the stable PCB, schematic, routing and Gerbers.
- `parameters.json` and `generate.py` define the custom adapter PCBs;
  `build.ps1` generates them. Never hand-edit their generated electrical outputs.
- `assembly_parameters.json` separates photographed caliper readings from
  estimated kit geometry. `assembly_model.py` creates reference kit CAD;
  it is not an electrically routed replacement for the stock kit boards.
- Photos, local CAD renders and AI concepts have different provenance. Keep
  `images\sources.json`, measurement uncertainties and source hashes intact.
  A measured overall length does not establish hinge, mounting or spring travel.
  Keep the older `clip_kit.measured` and pogo flags false until actually measured.
- Use millimetres, explicit origins and explicit face orientation. Preserve
  outline holes/windows, pad centres/sizes, nets, mask openings, thickness and
  component envelopes across ECAD/MCAD tools, rather than depending on one API.
  Independently parse the saved board text in portable tests to detect exporter
  errors; do not validate an exporter only against its own output.

## IR contact geometry and wiring

The six signal pads form a 3.05 mm grid, not 2.54 mm. TP3 is
KiCad `(136.5504,115.7986)`. Rear-up IR coordinates are
`u=TP3.x-x`, `v=y-TP3.y`; assembly coordinates are
`X=v-lower_tip_v`, `Y=u`, with `lower_tip_v=-2.9` in the current generated frame.
Adapter PCBs instead use `u=x-150`, `v=y-100`. Do not apply the mono-ring frame
or blindly mirror all boards.

TP1=PB0/MOSI, TP2=PB1/MISO, TP3=PB2/SCK, TP6=PB5/RESET.
TP9 is off-grid VCC; TP4/PB3 and TP5/PB4 are spare, not routed to ISP.
The standard 2.54 mm ISP header is not the pogo grid:
J1 pins 1..6 are MISO, VCC, SCK, MOSI, RESET, GND.
J1 on the custom probe is a top-side SMD 2x3 male header for female Dupont leads.
Its mating posts are on a 2.54 mm grid, but its splayed solder-land rows are
5.05 mm apart. Never mistake the solder-land row spacing for mating pitch.
The lower guide copy remains unpopulated, without header through-holes.
Seven upper pins contact TP1..TP6 and TP9. Order two probe PCBs: the top is
populated; the lower copy is an unpopulated guide.
Ground is on the front: ISP J1.6 -> probe J2 -> insulated wire -> anvil J1 ->
flat ENIG P8 -> front TP8. The fence is mechanical only. Remove the CR2032
before programming; never backfeed or solder a primary cell.
`hardware\v2.0\ring_ir_prog_clip\programming.md` gives cable orientation,
signal directions and power checks. The current IR adapter is classic AVR ISP,
not SWD; another target needs its own pad/net mapping and routing. A debugger's
VTref is normally a voltage-sense input, not a target-power output.

A centred stock 2.54 mm grid misses outer centres by about 0.570 mm diagonally.
The custom nominal 0.9 mm tips on 1 mm pads have only 0.05 mm edge margin,
less than the assumed 0.15 mm registration uncertainty. Neither virtual
alignment nor a successful render qualifies physical electrical contact.

## Actual board surfaces versus checked solids

`export_ir_visual.py` runs in KiCad Python and exports actual F/B copper,
mask-opening and silkscreen polygons, pad/net coordinates and source hashes to
`generated\assembly\ir_board_layers.json` and `clip_board_layers.json`.
KiCad 10 uses `ConvertBrdLayerToPolygonalContours` with polygon simplification;
preserve outline and hole contours when translating to another tool.

The exporter also writes actual populated and board-only KiCad STEP files to
`generated\kicad_step`, with origin `(150,100)` and source/artifact/model hashes.
Resolve `KICAD10_3DMODEL_DIR` explicitly in the exporter environment. The full
probe STEP must contain its real SMD header; fail if it is missing, never replace
it with a generic header box. The standard model is used for geometry, not an
approved MPN or a cable-retention qualification.

`fit_check.py` maps STEP `(x,y)` to assembly `(-y-lower_tip_v,x)` and mounts the
header by its solder-foot plane. `assembly_model.py` uses actual STEP board
cores for the custom render; the core is 1.51 mm inside the nominal 1.6 mm
copper/mask stack, centred without scaling. Contact/stack checks in the separate
fit model still use nominal finished-board envelopes; layer surfaces stay at
the finished faces. Preserve this distinction rather than stretching a STEP.
The body/contact colour split uses the standard SMD model's 0.76 mm standoff
and 2.54 mm body height; STEP-derived post centres must verify mating pitch.

FreeCAD intersects copper and mask openings with actual substrate faces;
mask is substrate minus openings. Clip every surface to the checked face,
including drills and component windows, not an enclosing rectangle.
`PCB_*` are IR layers; `ProbePCB_*`, `GuidePCB_*`, `AnvilPCB_*` and `FencePCB_*`
are adapter layers. Front is up on the adapters, rear is up on the IR board.

Layer meshes are intentionally open surfaces labelled `visual_surface_only`,
not extra physical board thickness. Do not require watertightness for them or
include them in solid interference/STEP-volume checks. Physical parts must
remain valid solids and watertight meshes. Never suppress invalid solids,
delete intersecting faces or fill holes to manufacture a passing result.
Blender adds only a +/-0.04 mm display separation and does not bevel surfaces.
It must not move mechanical contact datums.

## Execution and validation

For an electrical generator/configuration change:

```powershell
& hardware\v2.0\ring_ir_prog_clip\build.ps1 -Fab
```

Inspect all probe/anvil/fence DRC and schematic ERC reports: zero violations of
any severity, then a passing FreeCAD fit. Regenerate fabrication only from the
revised board. Do not commit validation-induced `.kicad_prl` editor noise.

For reconstruction or visual changes:

```powershell
& 'C:\Program Files\KiCad\10.0\bin\python.exe' hardware\v2.0\ring_ir_prog_clip\export_ir_visual.py
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_ir_prog_clip\fit_check.py
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_ir_prog_clip\assembly_model.py
python -m unittest discover -s hardware\v2.0\ring_ir_prog_clip -p "test_*.py"
& hardware\v2.0\ring_ir_prog_clip\animation\render.ps1 -SkipCAD
```

Without `-SkipCAD`, rendering first exports layers and rebuilds CAD.
Use FreeCAD's bundled Python, importing `FreeCAD` before `Part`; system Python
runs the portable interface tests. Those tests also run in
`.github\workflows\hardware-interface.yml`.

Keep FCStd, assembly STEP, per-part STL, manifests and
`generated\assembly\validation.json` consistent with source hashes. Check all
four variants, static solid pairs, STEP validity/volume, pad overlap and the
13-pose 0..6 degree hinge sweep. Only intentional header/pin embedding is
excluded. The CAD rebuilds its estimated helical spring at each pose and checks
coil gap and interference; this is not force, FEA, fatigue or spring-end analysis.
Hash text with the existing newline-normalizing helpers, binary artifacts raw;
exclude `.FCStd1` backups and temporary files from artifact manifests.

## Rendering and delivery

Use the CAD meshes rather than manually redrawing the boards in Blender.
Upper probe/guide layers follow the hinge; anvil/fence stay with the lower jaw.
The IR board and all its layers lift/seat together. The flexible ground lead
uses exported pad endpoints and an illustrative service loop: do not claim
flexible-cable clearance from rigid CAD checks. Exploded flights explain parts;
they are not certified assembly trajectories or tool-access checks.

`animation\render.ps1` produces eight stills and a 440-frame, 20 fps, 22-second
MP4/GIF plus `.blend`. Stills use Cycles; animation uses Eevee. On Windows,
long Eevee runs encountered a GPU-texture access violation: prepare once, then
use fresh Blender processes for 30-frame batches as the wrapper does.
Do not silently accept missing frames or reuse stale renders after source edits.
The primary assembly/explosion uses the actual custom IR STEP adapter with SMD
header; keep generic pitch-study segments explicitly separate.

Inspect `ir_adapter_exploded.png`, `ir_adapter.png` and `ir_actual_pcb.png` for
correct board sides, holes, contacts and captions. Check the MP4 with ffprobe
and full ffmpeg decode. Commit source, CAD, media, provenance and directly
related docs together. `animation\build` is ignored intermediate output; remove
only that exact inspected directory after delivery, never a broad wildcard.
Physical jaw/pin measurements, first-fit, retention, continuity and successful
programming remain required before claiming the adapter works in hardware.
