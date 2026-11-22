# Experimental RGBW driver firmware

This bare-metal ATtiny85 firmware targets both experimental
[single](../../hardware/v2.0/ring_pcb_RGBW/README.md) and
[dual](../../hardware/v2.0/ring_pcb_RGBW_dual/README.md) MOSFET boards. It is
compiled and host-tested, **not flashed or tested on either RGBW board**.
The existing IR/TV-B-Gone firmware is separate.

## Colour setup

Edit `config.h` and rebuild. Channel values are PWM commands from 0 (off) to
255 (continuously on), not calibrated brightness or a guaranteed colour.

| Build mode | Behaviour |
| --- | --- |
| `fixed` | Uses `RGBW_FIXED_R/G/B/W` regardless of JP1; default green `(0, 96, 0, 0)`. Change the four values and reflash for any firmware-defined mix. |
| `jumper` | Samples PB3 once at startup. JP1 open uses `RGBW_OPEN_R/G/B/W` (default green); JP1 bridged to GND uses `RGBW_BRIDGED_R/G/B/W` (default red `(96, 0, 0, 0)`). |

JP1 is a normally open **0402 solder-bridge footprint**, not an installed
pin header. The external 100k pull-up defines the open state. Power off and
remove the cell before changing the bridge; power-cycle to latch a new setting.
PB3 is never driven. Only two hardware states are implemented; no ADC ladder,
runtime palette changes or automatic effects are provided.

PB0/OC0A is red, PB1/OC0B green, PB4/OC1B blue, and PB2 white. Timer0 fast PWM
and Timer1 synchronous PWM use the CPU clock divided by 64: at an actual 8 MHz
clock their nominal frequency is 488.3 Hz. Timer1 overflow and compare-A
interrupts generate white PWM; 0 and 255 explicitly disconnect PWM and drive
the pin low/high. Intermediate white pulses include interrupt latency and
jitter, particularly near the endpoints. Timers are owned by this standalone
firmware; Arduino `millis()`, `delay()` and `analogWrite()` must not be added
without redesigning timer ownership. ISP uses PB0/PB1/PB2 while reset is
asserted, so gate transitions may occur during programming.

## Build and verification

Requires the already-installed Arduino AVR GCC toolchain (or pass `-AvrBin`
with its `avr-gcc.exe`, `avr-objcopy.exe` and `avr-size.exe`). On Windows:

```powershell
& firmware\rgbw-driver\build.ps1 -Mode fixed
& firmware\rgbw-driver\build.ps1 -Mode jumper
python -m unittest discover -s firmware\rgbw-driver\tests -p test_firmware.py
```

The host tests require `g++`; they compile the driver against mock registers,
not an AVR timing simulator. The build outputs ignored `build\rgbw-fixed.hex`
and `build\rgbw-jumper.hex`. Build after editing `config.h`. The build assumes
an **actual 8 MHz internal oscillator without CKDIV8**, and does not write
firmware or fuses. If the device is still at 1 MHz, PWM is eight times slower.
Confirm clock configuration and device operating voltage first; do not disable
RESET or ISP. Follow the [IR clip programming and backup procedure](../../hardware/v2.0/ring_ir_prog_clip/programming.md),
but verify contact and signal levels on the RGBW board independently. Remove
the CR2032 before ISP; never backfeed or charge it.

## Before use

Verify actual waveform polarity, frequency, endpoint duties, PB3 selection and
ISP on an assembled board with a scope, then measure individual and mixed
channel currents, cell voltage, temperature, runtime and colour. The
ATtiny85-20MU requires its specified supply/clock operating range; an 8 MHz
clock is not qualified throughout a discharging CR2032's voltage range.
Blue/green/white may dim or stop as voltage falls. These are experimental
designs: neither virtual checks nor firmware tests qualify battery safety,
mechanical retention, clip fit or wearable use.
