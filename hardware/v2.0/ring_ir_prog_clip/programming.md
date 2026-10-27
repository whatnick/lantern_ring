# Programming-clip wiring: AVR ISP and SWD

The clip is a passive contact fixture, not a programmer, voltage converter or
protocol adapter. The current probe is wired for the **ATtiny85 IR ring's
six-wire AVR ISP interface**. It does not give that MCU SWD support.
Other PCBs need their own verified pad pattern, signal mapping and clearances.
The custom adapter has not yet been physically qualified for programming.

## Current IR ring: connect AVR ISP

Use an ATtiny85-compatible ISP programmer, for example a correctly configured
USBasp, AVRISP or Arduino running ArduinoISP. Connect six female Dupont leads
to the **top-side SMD J1 male header** on the populated probe. The mating posts
are 2.54 mm apart; the wider SMD solder lands are not connector-pin centres.
Leave J1 unpopulated on the second probe PCB used as the lower guide.

Looking down onto the populated probe, with its extended front edge at the top
and the pogo grid / jaw mounting slots towards the bottom:

```text
             extended front edge

           2 VCC    4 MOSI    6 GND
           1 MISO   3 SCK     5 RESET
           ^
           confirm the silkscreen pin-1 mark

                 pogo grid
             jaw slots / hinge
```

This is the board-top view, not the cable's mating-face view. The header is
unshrouded and not keyed: confirm the `1` mark and continuity instead of relying
on cable colours or assuming an IDC connector's orientation.

| Programmer signal | Probe J1 | Fixture path | IR ring target |
| --- | --- | --- | --- |
| MISO / programmer data input | 1 | P2 pogo | TP2 / PB1, data out of target |
| Target VCC, with power arrangement checked below | 2 | P9 pogo | TP9 / VCC |
| SCK / programmer clock output | 3 | P3 pogo | TP3 / PB2 |
| MOSI / programmer data output | 4 | P1 pogo | TP1 / PB0, data into target |
| RESET / active-low reset output | 5 | P6 pogo | TP6 / PB5 |
| GND / common signal return | 6 | J2 -> insulated wire -> anvil J1 -> exposed ENIG P8 | Front TP8 / GND |

**The ground wire between the jaws is essential.** Solder it from probe J2 to
anvil J1, leaving insulated service slack for opening. The upper pogos cannot
reach front-side TP8. The anvil's flat P8 contact must actually touch that bar.
P4/TP4/PB3 and P5/TP5/PB4 are spare positions, deliberately not routed to J1;
they are not extra ISP signals or a second ground.

Insert the ring **LEDs/components down, rear test pads up**, with its front
ground bar over anvil P8. The existing pogo centres remain on the 3.05 mm signal
grid, with off-grid VCC. Do not confuse these dimensions with J1's 2.54 mm pitch.

### Power and first connection

1. **Remove the CR2032 before connecting the programmer.** Never backfeed,
   recharge or solder a primary coin cell. Power off the programmer's target
   supply and any external target supply while attaching or changing leads.
2. With everything unpowered, check continuity for every row of the table,
   including J1.6 to front TP8 with the clip closed. Check for shorts between
   neighbouring pins and VCC/GND. Do not infer this from a clean DRC or render.
3. Decide which single source powers the target. For programmer-powered use,
   enable a supported target supply and confirm its voltage and current limit.
   For externally powered use, disable/disconnect the programmer's supply
   output as its manual requires. Never tie two supply outputs together.
4. Match **both supply and signal levels** to the target and programmer
   specifications. A USBasp power jumper does not necessarily change its I/O
   voltage. The passive probe provides no regulation or level shifting.
5. Connect GND, the correctly configured VCC/reference connection, then signal
   leads while power is off. Provide strain relief on the cable: pulling on
   Dupont leads can peel the SMD header's solder pads.
6. Seat and close the clip, then apply current-limited power. Start at a slow ISP
   clock supported by the target's running clock; do not assume a fast setting
   works with a factory-divided or otherwise slow AVR clock.

For a compatible USBasp/avrdude installation, this is a read-only first check:

```text
avrdude -c usbasp -p t85 -B 10 -n
```

`-B 10` requests a 10 microsecond programming bit-clock period (about 100 kHz).
If the programmer reports that it cannot set SCK, resolve that limitation
instead of assuming the requested clock was applied. A classic ATtiny85 should
report signature **0x1e930b**. This command is an example, not a recorded hardware
test. Require repeatable signature reads before writing a verified firmware
image. Do not bypass a signature mismatch or casually change clock, RESET,
SPI-programming or debugWIRE fuse settings; loss of ISP access can require a
different recovery method. This clip is not a high-voltage programming fixture.

Turn off target power before opening/removing the fixture, and remove signal
and power leads before disconnecting the common ground.

## Another PCB using AVR ISP

Map the target MCU's actual **MOSI, MISO, SCK, RESET, VCC and GND** signals to the
same ISP-6 functions above. MCU GPIO names and physical pad positions will be
different; a pad called `TP1` does not universally mean MOSI or ground.

Derive a new probe/guide and, if required, anvil/fence from that board's real
outline, pads, nets and component heights. Update the generator's mapping,
placement and routing for the new target, then run ERC, DRC and mechanical
checks. The current generator includes IR-specific grid/routing guards; editing
only the pitch or renaming labels does not create a universal adapter.
Do not order the current IR fabrication ZIPs for a differently spaced board.

Use a programmer and programming method supported by that particular MCU.
Classic AVR ISP is not interchangeable with UPDI, TPI, JTAG or SWD.

## Another PCB using SWD

Use a target-compatible **SWD debugger/programmer**, such as an appropriate
ST-Link, CMSIS-DAP or J-Link, with a separately mapped target-specific adapter.
Connect by the programmer's documented **signal names**, not by AVR J1 numbers:

| SWD programmer connection | Target connection | Purpose |
| --- | --- | --- |
| SWDIO | SWDIO | Bidirectional debug/programming data |
| SWCLK | SWCLK | Clock from programmer |
| GND | Target GND | Common reference and signal return |
| VTref / Vtarget sense | Target MCU I/O supply rail | Input telling the debugger the target's logic voltage; normally not a power output |
| nRESET / NRST, if supported | MCU reset input | Reset and connect-under-reset recovery; strongly useful where available |
| SWO, optional | MCU SWO trace output | Optional trace, not required for ordinary SWD programming |

**VTref is not automatically a power supply.** A debugger may have a separate,
explicitly enabled target-power output, or may not supply the target at all.
Wire and configure it according to that exact debugger's manual, retaining
the single-power-source rule. A board's battery voltage may differ from its
MCU I/O rail; sense the correct rail and avoid phantom powering through data pins.

A standard Cortex 10-pin debug connector commonly uses **1.27 mm** pitch;
other debugger connectors may be 2.54 mm with different pin assignments.
Neither is pin-compatible merely because it fits the Dupont wires.
Do not plug a SWD cable directly onto this AVR-labelled J1. Six contacts can
carry the SWD signals in the table for a newly designed adapter, but such an
adapter needs its own labels, routing and documented cable pinout.

As with ISP, start unpowered, check end-to-end continuity and shorts, verify
logic voltage, then apply power and read the device identity using the MCU
vendor's supported tool. Start with a conservative SWD clock and require
repeatable connections before flash writes. Security/readout protection and
recovery operations can erase firmware; do not treat them as wiring tests.

## References and design evidence

- [Current PCB front drawing](generated/ring_ir_prog_probe_top_2d.svg),
  [rear drawing](generated/ring_ir_prog_probe_bottom_2d.svg) and
  [probe schematic](generated/ring_ir_prog_probe_schematic.pdf).
- [ISP pin/net source](parameters.json) and
  [regeneration / validation](development.md).
- [SEGGER interface descriptions](https://www.segger.com/products/debug-probes/j-link/technology/interface-description/)
  explain SWD signals, target-voltage reference and separate power outputs.
  Use the manual for the exact programmer model to identify physical pin numbers.
