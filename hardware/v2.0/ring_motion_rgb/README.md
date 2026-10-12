# Motion/RGB ring board (prototype baseline)

This is a **separate v2 board variant**; it does not replace or modify
`ring_mono`. The generated PCB preserves the mono board's exact 17.78 x
19.05 mm, 1.6 mm outline and battery-contact copper geometry. It also places
the pogo pads and front-side ground anvil at the same coordinates as the
existing `ring_pcb_IR` programming target, so the current clip can be used
without a new probe guide.

## Proposed circuit

- ATtiny84A-MU (QFN-20), programmed in-circuit through the existing AVR
  ISP-6 clip. The clip-compatible net names `PB0`, `PB1`, `PB2`, and `PB5`
  are **functional ISP aliases**, not the ATtiny84A's native port labels:
  MOSI is PA5, MISO PA6, SCK PA4, and RESET PB3.
- ST LIS2DW12TR accelerometer, I2C mode, with INT1 routed to the MCU. CS is
  tied high, SA0 low (address 0x18), and unused interrupt/NC pads are left
  unconnected.
- One common-cathode Inolux IN-S128TATRGB RGB LED and three 1 kOhm
  current-limit resistors. The shared cathode goes to GND; each MCU output
  sources its channel current through a jumper and resistor.
- Three open solder bridges select the enabled R/G/B channels. This gives
  seven non-zero channel combinations, not arbitrary analog color ratios;
  firmware PWM can tune intensity after the desired channel set is bridged.
- 100 nF local bypass capacitors and a 10 kOhm reset pull-up.

The 1 kOhm LED resistors are a conservative starting point for coin-cell
pulse loading, not a validated current specification. Measure CR2032 voltage
sag, LED current, and cell recovery before choosing production resistor
values or pulse durations.

Primary component references: [ST LIS2DW12 datasheet](https://www.st.com/resource/en/datasheet/lis2dw12.pdf)
and [Inolux IN-S128TATRGB datasheet](https://www.inolux-corp.com/datasheet/SMDLED/RGB%20Top%20View/IN-S128TATRGB_V1.1.pdf).

## Current status

`generate_board.py` creates a **placed, electrically net-assigned, 4-layer
layout baseline** from the existing mono PCB; `generate_schematic.py` creates
the matching KiCad schematic (ERC: 0 errors, 0 warnings, netlist matches the
PCB). The board is **not yet routed** and is not ready to fabricate. The
stackup is F.Cu (GND anvil plane), In1.Cu (signal), In2.Cu (GND plane) and
B.Cu (VCC battery-contact plane). A keepout rule area keeps vias and tracks out
of the exposed rear battery contact. Rules are 0.15 mm track/clearance and
0.5/0.25 mm vias. In particular:

- route the MCU, RGB channels, and sensor bus; refill zones and achieve zero
  DRC errors/unconnected items. FreeRouting 2.5.0 (JVM jar) leaves about 10
  connections or dangling vias unresolved, so the placement is meant for manual
  routing and review;
- qualify the RGB LED's optical output and current for the transparent crown;
- confirm the LIS2DW12 and ATtiny84A-MU pinouts against the official
  datasheets and vendor package drawings;
- tune the accelerometer wake threshold and pulse/color behavior on the
  assembled ring, then measure CR2032 pulse sag;
- add firmware, BOM fields, and manufacturing checks before release.

The current DRC reports only the unrouted connections (expected before
routing) and two TP1/TP2 footprint-library mismatch warnings. Placement DRC
shows no pad overlaps, but the LED, QFN and 0402 parts are tightly packed. A
FreeCAD STEP fit check found no PCB intersections with the
RingBase, Carrier, ContactDeck, Bezel, or eight crown variants. The minimum
modeled component-to-crown clearance is 0.195 mm. The missing ATtiny84A QFN
STEP model is conservatively represented by a 4 x 4 x 1.0 mm body proxy; this
is a CAD envelope check, not a physical fit or tolerance qualification.

Run generation with KiCad 10's bundled Python and run the interface tests with
system Python:

```powershell
& "C:\Program Files\KiCad\10.0\bin\python.exe" `
  hardware\v2.0\ring_motion_rgb\generate_board.py
python -m unittest discover -s hardware\v2.0\ring_motion_rgb -p "test_*.py"
```

Export the board to STEP and check its fit using FreeCAD's bundled Python:

```powershell
& "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb export step `
  --output "$env:TEMP\ring_motion_rgb.step" `
  hardware\v2.0\ring_motion_rgb\ring_motion_rgb.kicad_pcb
& "C:\Program Files\FreeCAD 0.19\bin\python.exe" `
  hardware\v2.0\ring_motion_rgb\check_fit.py `
  "$env:TEMP\ring_motion_rgb.step" `
  --json hardware\v2.0\ring_motion_rgb\fit-report.json
```

The interface tests verify outline, battery-contact, programming-pad, and
ground-anvil compatibility. The STEP check validates the current modeled
clearances only; neither tool qualifies electrical routing, clip force, print
tolerances, or physical fit.
