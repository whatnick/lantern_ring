# Lantern Ring v2 development

This document contains source-file references and regeneration commands for
the FreeCAD model, Lantern Corps crowns, and Blender renders. Run commands from
the repository root on Windows.

## Source and generated files

- `parameters.json` contains the mechanical stack and fit values.
- `design.py` reads the KiCad interface and validates design parameters.
- `lantern_ring.py` builds the FreeCAD assembly and checks geometry.
- `build.FCMacro` opens the model in the FreeCAD GUI.
- `crowns.py` builds the eight low-profile crowns from `logos/logos.json`;
  `--extract` traces the source emblems from the v1 FreeCAD document.
- `animation/export_parts.py` exports assembled parts and crown meshes for
  Blender.
- `animation/animate.py` produces the assembly animation and crown lineup.
- `animation/corps_swap.py` produces the crown-swap animation and hero still.
- `animation/render.ps1` and `animation/render_corps.ps1` run the render
  pipelines.

FreeCAD's bundled Python must run the CAD generators. The portable design and
crown tests use ordinary Python 3.8+. The checked-in CAD was generated with
FreeCAD 0.19 / OCC 7.5; rerun validation when changing FreeCAD versions.

## Rebuild and validate

```powershell
python -m unittest discover -s hardware\v2.0\ring_3d -p "test_design.py"
& hardware\v2.0\ring_3d\build.ps1
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_3d\test_freecad.py
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_3d\crowns.py
python -m unittest discover -s hardware\v2.0\ring_3d -p "test_crowns.py"
```

To re-trace the v1 logos before rebuilding the crowns, run:

```powershell
& 'C:\Program Files\FreeCAD 0.19\bin\python.exe' hardware\v2.0\ring_3d\crowns.py --extract
```

If FreeCAD auto-discovery chooses a different installation, pass the bundled
interpreter explicitly:

```powershell
& hardware\v2.0\ring_3d\build.ps1 -FreeCADPython 'C:\Program Files\FreeCAD 0.19\bin\python.exe'
```

For parametric GUI edits, run `build.FCMacro` in a new FreeCAD session before
opening an existing FCStd. Change the linked `Parameters` object and recompute.
Copy intended changes into `parameters.json` and rebuild; GUI edits do not
update exported manufacturing files. The PCB interface embedded in FCStd is a
snapshot, so regenerate after PCB changes. Do not hand-edit generated geometry.

## Render animations and images

Build the v2 parts and crowns before running either render script. The crown
swap pipeline consumes the crown meshes produced by the assembly export.

```powershell
& hardware\v2.0\ring_3d\animation\render.ps1
& hardware\v2.0\ring_3d\animation\render_corps.ps1
```

Use `-Preview` on either script for a draft. The assembly render produces
`generated/lantern_ring_v2_assembly.mp4`, `.gif`, and
`generated/crowns/lineup.png`. The Corps render produces
`generated/lantern_corps_swap.mp4`, `.gif`, and `generated/crowns/hero.png`.
Intermediate meshes, scenes and frames are written under `animation/build/`.

The assembly pipeline exports parts with `export_parts.py`, renders through
Blender 5 EEVEE, then encodes MP4/GIF with ffmpeg. If rebuilding the crowns,
run `crowns.py` before the assembly render so both animation pipelines use
current crown geometry.
