# RGBW MOSFET options: routed comparison

Compare the [four-single-MOSFET design](../../hardware/v2.0/ring_pcb_RGBW/README.md)
with the [two-dual-MOSFET design](../../hardware/v2.0/ring_pcb_RGBW_dual/README.md).

Both alternatives preserve the IR outline, 1.6 mm board thickness, TP1-TP9
geometry/nets and contact-mask windows, and keep four independent LED
resistors and gate networks. Both use four copper layers. These are virtual
results, not fabrication or physical clip qualifications.

| Metric | Four single DMG1012T | Two dual NTZD3154N |
| --- | ---: | ---: |
| MOSFET packages / fitted parts | 4 / 22 | 2 / 20 |
| MOSFET package body, nominal | 0.8 x 1.6 mm each | 1.2 x 1.6 mm each |
| Combined body area, nominal | 5.12 mm2 | 3.84 mm2 |
| Sum of courtyard bounding rectangles, including line widths | 20.21 mm2 | 9.56 mm2 |
| Segments / vias in these routed files | 136 / 35 | 169 / 39 |
| Copper track centreline length | 171.71 mm | 190.00 mm |
| Smallest anvil-opening screen margin | 0.189 mm, R5 | 0.189 mm, R5 |
| Closest rear pogo pad centre to foreign via copper edge | 0.823 mm, TP5 | 0.823 mm, TP5 |
| Native ERC / DRC / parity / unconnected | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

The ~10.65 mm2 courtyard-bounding-box reduction is a package-placement
comparison, **not an increase in usable board area**: the board outline is
unchanged and the dual placement needed longer traces and four more vias.
These routing results are particular to the current layouts/router run,
not a guaranteed property of either topology. The 0402 gate and current
resistors remain; six 0.5 mm-pitch pins per dual package may complicate
assembly/rework. A package fault can affect two channels.
The via spacing is a nominal geometric screen, not proof of pogo contact:
the nominal 0.45 mm probe-tip radius leaves 0.373 mm to the nearest
foreign via edge before registration error, solder mask tolerances and
actual conductive tip shape are considered.

The onsemi device specifies a **0.9 ohm maximum** RDS(on) at 1.8 V and
350 mA, compared with the single Diodes device's **0.7 ohm maximum** at
the same test conditions. Maximum gate-source voltage is +/-7 V versus
the single device's +/-6 V. At the design's conservative 2.526 mA
per-channel shorted-LED bound, the difference between those resistance
figures corresponds to approximately 0.51 mV and 1.3 microwatts; this is
illustrative, because the stated resistance is specified at 350 mA, not
validated for this exact low-current operating point.

Typical input capacitance is 80 pF per dual channel (150 pF maximum at the
datasheet's 16 V test voltage) versus 60.67 pF typical per single channel;
this makes ISP/PWM switching worth checking in hardware. The gate input
leakage maximum is +/-5 uA at VGS +/-4.5 V for the dual device, versus
1 uA for the single. With a 1k series / 100k pulldown, 5 uA is the same
order as the pull-down current near threshold: do **not** infer a guaranteed
off state from the high-voltage leakage limit. Verify leakage and turn-off
across supply and temperature, particularly during ISP reset, with real
devices before use.

Both options have a 0.189 mm nominal smallest screen margin, already too
small to establish physical clip clearance. The QFN exposed-pad via,
actual solder height, clip jaw/pogo dimensions, battery load/current/
temperature and RGBW firmware remain unqualified. The dual option is
promising for fewer placements, but the simpler original remains the
reference until both options have assembly and electrical measurements.

Sources: [onsemi NTZD3154N/D Rev 5](https://www.onsemi.com/pdf/datasheet/ntzd3154n-d.pdf)
and [Diodes DMG1012T DS31783 Rev 8-2](https://www.diodes.com/assets/Datasheets/DMG1012T.pdf).
The dual's ordering table marks some suffixed variants discontinued; verify
the exact NTZD3154NT1G purchasing availability. No stock or quote is assumed.
