# Arduino TV-B-Gone development

Source-file references and build notes for the legacy ATtiny85 Arduino port.
The firmware was last documented in 2016; verify toolchain compatibility
before changing or distributing a build.

## Source files

- `Arduino-TV-B-Gone.ino` contains the Arduino sketch and its version history.
- `main.h` configures the pin assignments, debug output and timing.
- `WORLD_IR_CODES.h` contains the regional IR power-code database.

Use the Arduino IDE to build for the intended ATtiny85 hardware. The sketch
expects the external IR LED, trigger button and optional region switch wiring
described in the user README. Confirm the MCU clock before changing
`DELAY_CNT`; timing must be tested on the target hardware.

The code lineage, original licensing and external background links are
documented in the user README. Preserve upstream attribution and license terms
when modifying or redistributing this code.
