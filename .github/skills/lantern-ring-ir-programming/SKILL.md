---
name: lantern-ring-ir-programming
description: Program the Lantern Ring ATtiny85 through its real pogo clip and Arduino Uno ArduinoISP, using the reported working 5 V target rail, contact/voltage checks, stable identity, complete backups, minimal clock-fuse changes and independent full readback.
---

# Real IR ring programming flow

Use for programming or diagnosing the physical IR clip, not for the mono PCB,
SWD, mechanical redesign or arbitrary AVR targets. Read
`hardware\v2.0\ring_ir_prog_clip\programming.md` and
`programming-evidence.json`. Work from the repository root with Windows
filesystem paths. A documentation request does not authorize serial access,
erasing, fuse writes or programming.

## Evidence and limits

- On 2026-11-10 ArduinoISP on COM6 successfully programmed the ATtiny85:
  signature `0x1e930b`, 5320 firmware bytes, 8192-byte complete flash readback
  matching the intended image/erased tail, and unchanged 512-byte EEPROM.
- Both memories were blank and backed up/verified before writing. LF changed
  from `0x62` to `0xE2`; HF `0xDF`, EF `0xFF` and LOCK `0xFF` were preserved.
- Earlier all-zero signatures cleared after contact alignment. Do not force
  an invalid signature or diagnose a dead chip from `0x000000` alone.
- The user subsequently reported the **5 V target rail working in practice**.
  The documented setup uses Uno 5V and its matching 5 V ISP signals. This is
  distinct from the earlier verified run's reported 3.3 V supply. Do not claim
  a separately measured/verified 5 V run, IR function, contact life, retention
  or current/temperature qualification from that evidence.

## Physical hookup and power

Remove the CR2032; never backfeed, charge or solder a primary cell. Disconnect
USB and target power before changing leads, seating or opening the clip.
Use one target supply, not joined Uno/external outputs. Check PCB power and
the source/load current budget: firmware may drive IR LEDs on reset.

| Lead | Uno | Populated probe J1 | Target |
| --- | --- | --- | --- |
| Grey | D12 / MISO | 1 | P2 -> rear TP2 / PB1 |
| White | **5V** | 2 | P9 -> rear TP9 / VCC |
| Blue | D13 / SCK | 3 | P3 -> rear TP3 / PB2 |
| Purple | D11 / MOSI | 4 | P1 -> rear TP1 / PB0 |
| Brown | D10, not Uno RESET | 5 | P6 -> rear TP6 / PB5 |
| Black | GND | 6 | Probe J2 -> insulated wire -> anvil J1 -> front TP8 |

Rear pads face up, components/LEDs down. The top-view header rows are
`2 VCC / 4 MOSI / 6 GND` above `1 MISO / 3 SCK / 5 RESET`, extended front
edge up. The mating-face view is mirrored. Confirm pin 1, not cable colour.
Header mating pitch is 2.54 mm; solder lands are not the mating posts.
The pogo grid is 3.05 mm with off-grid VCC. Leave the lower guide unpopulated;
TP4/PB3 and TP5/PB4 are spare. Front TP8 needs the separate inter-jaw wire.

For a power-only test, unplug D10-D13 while unpowered, retaining supply/GND.
Clip the meter black COM lead to Uno GND and use an insulated fine red V tip
through the anvil window on C1/C2: pad 1 VCC should read about **5 V**, pad 2
GND about **0 V**. C2 faces opposite C1; their facing ends are GND.
Never use current/continuity mode on a powered board. Reconnect signals only
with power off. A 3.3 V alternative requires proper SPI level translation
(including MISO handling) or a matching host; Uno 3V3 does not lower its I/O.

## Host and target settings

With the target disconnected, upload
`File > Examples > 11.ArduinoISP > ArduinoISP` normally to **Arduino Uno**.
Close Serial Monitor. COM6 was the recorded port; verify the current port,
do not scan or program another user's device. Resolve the installed
Arduino CLI, avrdude executable and its matching `avrdude.conf` explicitly.
Typical tool locations are under the Arduino IDE installation and
`$env:LOCALAPPDATA\Arduino15\packages\arduino\tools`.

The verified core was `attiny:avr` 1.0.2:
Board `ATtiny25/45/85`, Processor `ATtiny85`, Clock `Internal 8 MHz`,
Programmer **Arduino as ISP**, not `ArduinoISP`, and
**Sketch > Upload Using Programmer**. There is no external clock component
on this board. The firmware delay loop expects 8 MHz.

Factory LF `0x62` selects the internal oscillator divided to 1 MHz. The IDE
clock menu changes compilation, not fuses. Read actual fuses first. This
core's Burn Bootloader erases the chip and writes fuses, not a bootloader;
the recorded CLI flow changed only LF and did not blindly rewrite all fuses.
Do not disable RESET/SPI or select an external clock.

## Execute only after explicit programming authorization

Use a persistent work directory outside the repository for logs, binaries,
backups and the exact upload image. Do not commit them. Define `$cli`,
`$avrdude`, `$conf`, `$repo`, `$work` and `$port` from verified local paths.
Keep all `.hex`/`.bin` arguments below relative to `$work` to avoid path
ambiguity. Stop on any nonzero tool exit; never use `-F` or `-V`.

1. Compile the unchanged firmware and archive the produced HEX:

   ```powershell
   & $cli compile --fqbn 'attiny:avr:ATtinyX5:cpu=attiny85,clock=internal8' --build-path $work (Join-Path $repo 'firmware\Arduino-TV-B-Gone')
   ```

   Check the exit status, HEX checksums and target size. Record source/image
   hashes; do not assume future builds remain 5320 bytes.

2. With the closed clip and stable power, read identity and complete backups:

   ```powershell
   Set-Location -LiteralPath $work
   & $avrdude "-C$conf" -c stk500v1 -p t85 -P $port -b 19200 -n -v -A '-Uflash:r:flash-before.bin:r' '-Ueeprom:r:eeprom-before.bin:r' '-Ulfuse:r:lfuse-before.txt:h' '-Uhfuse:r:hfuse-before.txt:h' '-Uefuse:r:efuse-before.txt:h' '-Ulock:r:lock-before.txt:h'
   ```

   Require `0x1e930b`, full 8192/512-byte files and readable fuse values.
   Verify those backups against a second read-only connection:

   ```powershell
   & $avrdude "-C$conf" -c stk500v1 -p t85 -P $port -b 19200 -n -A '-Uflash:v:flash-before.bin:r' '-Ueeprom:v:eeprom-before.bin:r'
   ```

3. Determine preservation needs before the flash erase. Nonblank EEPROM may
   be erased unless EESAVE preserves it: restore and verify the backup as
   appropriate. Do not assume it is blank because the recorded chip was.
   With stable identity and verified backups, the recorded blank-chip write
   was:

   ```powershell
   & $avrdude "-C$conf" -c stk500v1 -p t85 -P $port -b 19200 -v '-Uflash:w:Arduino-TV-B-Gone.ino.hex:i' '-Ulfuse:w:0xe2:m'
   ```

   This auto-erases flash and verifies both writes. Include the LF operation
   only when deliberately changing the expected `0x62` internal-clock setup;
   omit it for a chip already at `0xE2`. Diagnose other configurations first.
   Preserve HF/EF/LOCK, rather than resetting them to example values.

4. Open a fresh read-only connection and read complete flash, EEPROM and all
   fuses/lock again. Compare the **whole** flash byte-for-byte with the HEX
   expanded to 8192 bytes with erased `0xFF` tail; verify unchanged/restored
   EEPROM and intended fuses. A successful compiler or write message alone
   is not completion. Record checksums, results and any partial failure.

5. Power off and detach programmer leads before reinstalling the CR2032.
   Report firmware/readback success separately from physical IR-function
   testing and electrical qualification.

ArduinoISP uses 19200 baud. Its printed `Vtarget: 0.0 V` is a placeholder,
not a measurement. Its `SPI_CLOCK` is compiled into the Uno sketch; do not
assume avrdude `-B` adjusts it. An Uno auto-reset issue may require a 10 uF
capacitor from **Uno** RESET (+) to GND (-), fitted unpowered after loading
ArduinoISP and removed before uploading to the Uno again.

## Revision discipline

The probe, anvil and fence are one generated design at minor revision v0.2.
Overwrite their existing canonical KiCad filenames via `parameters.json` or
`generate.py` and `build.ps1 -Fab`; never hand-edit generated boards or create
a second v0.2 directory/project. Preserve the IR board and all ISP pad/net
assignments. Use `lantern-ring-ecad-mcad-render` for board/CAD changes, and
keep all zero-violation reports, fit checks and exports consistent. Successful
programming does not turn estimated jaw/pogo geometry into measured geometry.
