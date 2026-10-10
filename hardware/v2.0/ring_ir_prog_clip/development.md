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
