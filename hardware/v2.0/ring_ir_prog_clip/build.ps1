param(
    [string]$KiCadBin = 'C:\Program Files\KiCad\10.0\bin',
    [switch]$Fab
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$cli = Join-Path $KiCadBin 'kicad-cli.exe'
$py = Join-Path $KiCadBin 'python.exe'
$gen = Join-Path $here 'generated'
New-Item -ItemType Directory $gen -Force | Out-Null

& $py (Join-Path $here 'generate.py')
if ($LASTEXITCODE) { throw 'generate.py failed' }

$boards = @(
    @{ Name = 'ring_ir_prog_probe'; Dir = 'probe'; Sch = $true },
    @{ Name = 'ring_ir_prog_anvil'; Dir = 'anvil'; Sch = $true },
    @{ Name = 'ring_ir_prog_fence'; Dir = 'fence'; Sch = $false }
)
foreach ($b in $boards) {
    $base = Join-Path (Join-Path $here $b.Dir) $b.Name
    $drcArgs = @('pcb', 'drc', '--severity-all', '--format', 'json', '-o', (Join-Path $gen "$($b.Name)_drc.json"))
    if ($b.Sch) {
        & $cli sch upgrade --force "$base.kicad_sch" | Out-Null
        & $cli sch erc --severity-all --format json -o (Join-Path $gen "$($b.Name)_erc.json") "$base.kicad_sch" | Out-Null
        & $cli sch export pdf -o (Join-Path $gen "$($b.Name)_schematic.pdf") "$base.kicad_sch" | Out-Null
        $drcArgs += '--schematic-parity'
    }
    & $cli @drcArgs "$base.kicad_pcb" | Out-Null
    foreach ($side in 'top', 'bottom') {
        & $cli pcb render --side $side --width 900 --height 900 --quality basic `
            -o (Join-Path $gen "$($b.Name)_$side.png") "$base.kicad_pcb" | Out-Null
    }
    & $cli pcb export step --force --subst-models -o (Join-Path $gen "$($b.Name).step") "$base.kicad_pcb" | Out-Null
    if ($Fab) {
        $fabDir = Join-Path (Join-Path $here 'fab') $b.Name
        Remove-Item $fabDir -Recurse -Force -ErrorAction SilentlyContinue
        New-Item -ItemType Directory $fabDir -Force | Out-Null
        & $cli pcb export gerbers --layers 'F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts' `
            --subtract-soldermask -o "$fabDir\" "$base.kicad_pcb" | Out-Null
        & $cli pcb export drill --format excellon --excellon-separate-th -o "$fabDir\" "$base.kicad_pcb" | Out-Null
        Compress-Archive -Path "$fabDir\*" -DestinationPath "$fabDir.zip" -Force
    }
}
# kicad-cli may touch editor-local state; it is not design source.
Get-ChildItem $here -Recurse -Include *.kicad_prl, *-backups, fp-info-cache | Remove-Item -Recurse -Force

& $py (Join-Path $here 'check_reports.py')
if ($LASTEXITCODE) { throw 'ERC/DRC report check failed' }
