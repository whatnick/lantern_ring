param(
    [string]$AvrBin = "$env:LOCALAPPDATA\Arduino15\packages\arduino\tools\avr-gcc\7.3.0-atmel3.6.1-arduino7\bin",
    [ValidateSet('fixed', 'jumper')]
    [string]$Mode = 'fixed'
)
$ErrorActionPreference = 'Stop'
$out = Join-Path $PSScriptRoot 'build'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$modeValue = if ($Mode -eq 'jumper') { 1 } else { 0 }
$elf = Join-Path $out "rgbw-$Mode.elf"
$hex = Join-Path $out "rgbw-$Mode.hex"
& (Join-Path $AvrBin 'avr-gcc.exe') -mmcu=attiny85 -DF_CPU=8000000UL "-DRGBW_MODE=$modeValue" `
    -std=gnu11 -Os -Wall -Wextra -Werror -o $elf (Join-Path $PSScriptRoot 'rgbw.c')
if ($LASTEXITCODE -ne 0) { throw 'AVR compilation failed' }
& (Join-Path $AvrBin 'avr-objcopy.exe') -O ihex -R .eeprom $elf $hex
if ($LASTEXITCODE -ne 0) { throw 'AVR HEX export failed' }
& (Join-Path $AvrBin 'avr-size.exe') -C --mcu=attiny85 $elf
if ($LASTEXITCODE -ne 0) { throw 'AVR size check failed' }
Write-Output "Built $hex; no device was programmed and no fuses were changed."
