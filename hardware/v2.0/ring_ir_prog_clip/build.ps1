param(
    [string]$KiCadBin = 'C:\Program Files\KiCad\10.0\bin',
    [string]$FreeCADPython,
    [switch]$Fab,
    [switch]$SkipFit
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$cli = Join-Path $KiCadBin 'kicad-cli.exe'
$py = Join-Path $KiCadBin 'python.exe'
$env:KICAD10_3DMODEL_DIR = Join-Path (Split-Path $KiCadBin) 'share\kicad\3dmodels'
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
    $projectBytes = [System.IO.File]::ReadAllBytes("$base.kicad_pro")
    try {
        $drcArgs = @('pcb', 'drc', '--severity-all', '--format', 'json', '-o', (Join-Path $gen "$($b.Name)_drc.json"))
        if ($b.Sch) {
            & $cli sch upgrade --force "$base.kicad_sch" | Out-Null
            if ($LASTEXITCODE) { throw "Schematic upgrade failed: $($b.Name)" }
            & $cli sch erc --severity-all --format json -o (Join-Path $gen "$($b.Name)_erc.json") "$base.kicad_sch" | Out-Null
            if ($LASTEXITCODE) { throw "ERC failed: $($b.Name)" }
            & $cli sch export pdf -o (Join-Path $gen "$($b.Name)_schematic.pdf") "$base.kicad_sch" | Out-Null
            if ($LASTEXITCODE) { throw "Schematic PDF failed: $($b.Name)" }
            $drcArgs += '--schematic-parity'
        }
        & $cli @drcArgs "$base.kicad_pcb" | Out-Null
        if ($LASTEXITCODE) { throw "DRC failed: $($b.Name)" }
        foreach ($side in 'top', 'bottom') {
            $layers = if ($side -eq 'top') { 'F.Cu,F.Silkscreen,Edge.Cuts' } else { 'B.Cu,B.Silkscreen,Edge.Cuts' }
            $svgArgs = @('pcb', 'export', 'svg', '--mode-single', '--page-size-mode', '2',
                         '--exclude-drawing-sheet', '--layers', $layers,
                         '-o', (Join-Path $gen "$($b.Name)_${side}_2d.svg"))
            if ($side -eq 'bottom') { $svgArgs += '--mirror' }
            & $cli @svgArgs "$base.kicad_pcb" | Out-Null
            if ($LASTEXITCODE) { throw "2D PCB export failed: $($b.Name) $side" }
            & $cli pcb render --side $side --width 1600 --height 1600 --quality high --zoom 0.9 `
                -o (Join-Path $gen "$($b.Name)_$side.png") "$base.kicad_pcb" | Out-Null
            if ($LASTEXITCODE) { throw "PCB render failed: $($b.Name) $side" }
        }
        & $cli pcb export step --force --subst-models -o (Join-Path $gen "$($b.Name).step") "$base.kicad_pcb" | Out-Null
        if ($LASTEXITCODE) { throw "KiCad STEP export failed: $($b.Name)" }
        if ($Fab) {
            $fabDir = Join-Path (Join-Path $here 'fab') $b.Name
            Remove-Item $fabDir -Recurse -Force -ErrorAction SilentlyContinue
            New-Item -ItemType Directory $fabDir -Force | Out-Null
            & $cli pcb export gerbers --layers 'F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts' `
                --subtract-soldermask -o "$fabDir\" "$base.kicad_pcb" | Out-Null
            if ($LASTEXITCODE) { throw "Gerber export failed: $($b.Name)" }
            & $cli pcb export drill --format excellon --excellon-separate-th -o "$fabDir\" "$base.kicad_pcb" | Out-Null
            if ($LASTEXITCODE) { throw "Drill export failed: $($b.Name)" }
            Compress-Archive -Path "$fabDir\*" -DestinationPath "$fabDir.zip" -Force
        }
    } finally {
        [System.IO.File]::WriteAllBytes("$base.kicad_pro", $projectBytes)
    }
}
& $py (Join-Path $here 'check_reports.py')
if ($LASTEXITCODE) { throw 'ERC/DRC report check failed' }

& $py (Join-Path $here 'export_ir_visual.py')
if ($LASTEXITCODE) { throw 'KiCad layer/STEP export failed' }

if (-not $SkipFit) {
    if (-not $FreeCADPython) {
        $candidates = Get-ChildItem "$env:ProgramFiles\FreeCAD*\bin\python.exe" -ErrorAction SilentlyContinue
        if (-not $candidates) { throw 'FreeCAD Python not found. Pass -FreeCADPython or -SkipFit.' }
        $FreeCADPython = ($candidates | Sort-Object FullName -Descending | Select-Object -First 1).FullName
    }
    & $FreeCADPython (Join-Path $here 'fit_check.py')
    if ($LASTEXITCODE) { throw 'FreeCAD fit check failed' }
}
