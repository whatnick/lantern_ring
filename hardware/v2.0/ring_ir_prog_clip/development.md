# IR programming clip development

This document contains source references and regeneration steps for the KiCad
probe/anvil/fence boards and their FreeCAD fit check. Run commands from the
repository root.

## Source files

- `parameters.json` contains PCB layout, clip-kit estimate and pogo dimensions.
- `generate.py` reads the target IR PCB and creates the probe, anvil and fence
  boards and their electrical schematics.
- `check_reports.py` validates ERC/DRC reports and records source provenance.
- `fit_check.py` builds and checks the clip stack in FreeCAD.
- `test_prog_clip.py` checks the PCB interfaces and generated fit report.
- `build.ps1` runs the complete KiCad and FreeCAD pipeline.
- `assembly_parameters.json` separates readable album measurements from estimated
  kit geometry and declares the 1.27/2.00/2.54 mm grids and custom IR variant.
- `assembly_interface.py` checks square-pad containment against the actual IR PCB
  geometry, with a stale-board hash gate.
- `assembly_model.py` reconstructs the photographed kit, uses the existing IR
  fixture geometry, and checks every solid pair (only the deliberate header/body
  embedding is excluded), 13 hinge poses and estimated spring compression.
- `animation/assemble.py` renders those same FreeCAD meshes in Blender, not a
  separately drawn approximation. The spring is visually scaled in Blender;
  the CAD check rebuilds its helix at each pose. Frame assembly flights are
  instructional, not an assembly-path collision certification.
- `images/sources.json` records album image URLs, indices and downloaded-image
  SHA256 hashes. The photographs are user supplied, not renders.
- `export_ir_visual.py` runs with KiCad Python to read actual pad centres and
  F/B copper, mask-opening and silkscreen polygons from the IR board and the
  probe/anvil/fence PCBs. FreeCAD maps them with the
  same board frame as the pogo contacts; these are visual surfaces, not extra
  physical solids included in interference or solid STEP round-trip checks.
  Surface meshes are intentionally open and labelled `visual_surface_only`.

The board geometry is derived from the v2 IR PCB's pads, nets, outline, front
mask opening and component courtyards. Estimated clip-kit geometry is based on
photos and the Adafruit 5434 family datasheet; it is not a measured fit.
Pin dimensions are likewise unmeasured. Update the configuration only after
measuring the physical clip and pogo pins, and mark the estimates as measured
in the configuration.

## Rebuild and validation

Requires KiCad 10 and FreeCAD 0.19 or newer:

```powershell
& hardware\v2.0\ring_ir_prog_clip\build.ps1 -Fab
python -m unittest discover -s hardware\v2.0\ring_ir_prog_clip -p "test_prog_clip.py"
```

The build runs the PCB generator, schematic/ERC/DRC checks, exports PDFs,
renders and STEP, and optionally exports Gerbers and Excellon drill files.
It then checks the reports and runs the FreeCAD fit verification. Use
`-SkipFit` only when intentionally bypassing the fit step.

The portable test does not require `pcbnew`; it verifies pogo positions and
nets, ISP-6 pinout, anvil ground contact, courtyard/window clearance, board
spacing, assembly fit and input provenance. Do not hand-edit generated KiCad
boards or fabrication files. Update the source parameters and rebuild.

After assembly, check that `avrdude -c usbasp -p t85` consistently reads the
ATtiny85 signature `0x1e930b` before securing the anvil stack in place.

## Album reconstruction and Blender animation

This pipeline is separate from `build.ps1`: it does not alter the IR board,
generated clip PCBs, ERC/DRC results or fabrication data. In particular, it does
not mark the older `clip_kit.measured` flag true based on partial measurements.
The source configuration remains explicit about unresolved dimensions.

```powershell
& 'C:\Program Files\KiCad\10.0\bin\python.exe' hardware\v2.0\ring_ir_prog_clip\export_ir_visual.py
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_ir_prog_clip\assembly_model.py
python -m unittest discover -s hardware\v2.0\ring_ir_prog_clip -p "test_assembly.py"
& hardware\v2.0\ring_ir_prog_clip\animation\render.ps1 -SkipCAD
```

Without `-SkipCAD`, rendering first rebuilds and validates the CAD. `-StillsOnly`
renders the seven preview PNGs. Requires KiCad 10, FreeCAD, Blender 5.2 and ffmpeg.
Full rendering writes `generated/assembly/clip_assembly.blend`, MP4 and GIF,
plus assembled/exploded/IR adapter/pitch stills. Frame PNGs are ignored in
`animation/build/`; final deliverables and CAD are versioned.

Each variant has an FCStd, STEP and per-component STL meshes in
`generated/assembly/<variant>/`. These are visualization/reference geometry,
not fabrication-approved replacement jaws or new electrically routed PCBs.
`generated/assembly/validation.json` records source/PCB hashes, static and
motion collisions, spring-coil gaps and FreeCAD tip/pad overlap fractions.
The IR variant uses the existing custom 3.05 mm signal pattern and off-grid
VCC, not a relabelled 2.54 mm stock grid. Stock grids cannot provide the front
GND contact, and the illustrated kit header must not be treated as ISP wiring.
The 22-second animation ends with actual KiCad board layers visible outside the
clip followed by insertion into the custom adapter. `ir_board_layers.json`
contains the independently extracted XY coordinates, layer polygons and hashes.
Its nominal 1.6 mm substrate is used for fit; thin visual layers are offsets for
rendering only and are not treated as additional mechanical thickness. Blender
adds another 0.04 mm layer separation to avoid depth-buffer fighting and does
not bevel open copper/mask/silk meshes. This does not move the CAD contacts.
The renderer uses fresh Blender processes for 30-frame batches to avoid the
Windows Eevee GPU-texture access violation seen during a long single run.

`clip_board_layers.json` records the actual adapter board hashes, pad nets,
coordinates and layer polygons. The second probe copy is the unpopulated guide.
Adapter `(u,v) = (x-150,y-100)` maps to assembly `(X,Y) = (v-lower_tip_v,u)`;
the IR board instead uses `(u,v) = (TP3.x-x,y-TP3.y)` because it is rear-up.
Layer surfaces are clipped to the checked substrate faces, including drill
holes and the anvil window. Do not substitute bounding rectangles.

The added custom-adapter exploded still and animation use the same meshes.
The GND service loop derives its endpoints from probe J2 and anvil J1 in the
exported pad data, with the upper endpoint following the hinge. It represents
ISP J1.6 -> probe J2 -> wire -> anvil J1 -> P8 -> front TP8. Its interpolated
shape is illustrative and excluded from rigid-solid collision claims.
The electrical boards, routing and fabrication outputs are unchanged.

The repository skill
[lantern-ring-ecad-mcad-render](../../../.github/skills/lantern-ring-ecad-mcad-render/SKILL.md)
captures the reusable source/frame, electrical, mechanical and rendering gates.
