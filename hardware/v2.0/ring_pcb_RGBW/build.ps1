param(
    [string]$KiCadBin = 'C:\Program Files\KiCad\10.0\bin',
    [string]$FreeCADPython = 'C:\Program Files\FreeCAD 0.19\bin\python.exe',
    [string]$FreeroutingJar,
    [switch]$Rebuild,
    [switch]$Render
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$gen = Join-Path $here 'generated'
$base = Join-Path $here 'ring_pcb_RGBW'
$cli = Join-Path $KiCadBin 'kicad-cli.exe'
$py = Join-Path $KiCadBin 'python.exe'
$env:KICAD10_3DMODEL_DIR = Join-Path (Split-Path $KiCadBin) 'share\kicad\3dmodels'

function Invoke-Checked {
    param([string]$Tool, [string[]]$Arguments)
    & $Tool @Arguments
    if ($LASTEXITCODE) { throw "$Tool failed: $Arguments" }
}

if ($Rebuild) {
    if (-not $FreeroutingJar -or -not (Test-Path -LiteralPath $FreeroutingJar -PathType Leaf)) {
        throw '-Rebuild requires a local Freerouting 2.5.0 jar; no cloud router is used.'
    }
    Invoke-Checked $FreeCADPython @((Join-Path $here 'create_led_model.py'))
    Invoke-Checked $py @((Join-Path $here 'generate.py'))
    $placement = Get-Content (Join-Path $gen 'placement-drc.json') -Raw | ConvertFrom-Json
    if ($placement.violations.Count -or $placement.schematic_parity.Count) {
        throw 'Placement must pass DRC/parity before routing.'
    }
    if ($placement.unconnected_items | Where-Object { $_.items.description -match '\[(GND|VCC)\]' }) {
        throw 'Power planes and fanout must be connected before signal-only routing.'
    }
    foreach ($name in 'ring_pcb_RGBW.ses', 'router-result.json') {
        $file = Join-Path $gen $name
        if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file }
    }
    Invoke-Checked 'python' @((Join-Path $here 'route_local.py'), $FreeroutingJar)
    Invoke-Checked $py @((Join-Path $here 'finish_route.py'))
}
Invoke-Checked $cli @('sch', 'erc', '--severity-all', '--exit-code-violations', '--format', 'json',
    '-o', (Join-Path $gen 'erc.json'), "$base.kicad_sch")
Invoke-Checked $cli @('pcb', 'drc', '--severity-all', '--schematic-parity',
    '--exit-code-violations', '--format', 'json', '-o', (Join-Path $gen 'drc.json'), "$base.kicad_pcb")
if ($Render) {
    if (-not $Rebuild) {
        Invoke-Checked $FreeCADPython @((Join-Path $here 'create_led_model.py'))
    }
    Invoke-Checked $cli @('sch', 'export', 'pdf', '-o', (Join-Path $gen 'schematic.pdf'), "$base.kicad_sch")
    foreach ($side in 'top', 'bottom') {
        $layers = if ($side -eq 'top') { 'F.Cu,F.Silkscreen,Edge.Cuts' } else { 'B.Cu,B.Silkscreen,Edge.Cuts' }
        $args2d = @('pcb', 'export', 'svg', '--mode-single', '--page-size-mode', '2',
            '--exclude-drawing-sheet', '--layers', $layers, '-o', (Join-Path $gen "${side}_routing.svg"))
        if ($side -eq 'bottom') { $args2d += '--mirror' }
        Invoke-Checked $cli ($args2d + "$base.kicad_pcb")
        Invoke-Checked $cli @('pcb', 'render', '--side', $side, '--width', '1600', '--height', '1600',
            '--quality', 'high', '--zoom', '0.9', '-o', (Join-Path $gen "$side.png"), "$base.kicad_pcb")
    }
    foreach ($plane in @(@('ground_plane', 'In1.Cu'), @('supply_plane', 'In2.Cu'))) {
        Invoke-Checked $cli @('pcb', 'export', 'svg', '--mode-single', '--page-size-mode', '2',
            '--exclude-drawing-sheet', '--layers', "$($plane[1]),Edge.Cuts",
            '-o', (Join-Path $gen "$($plane[0]).svg"), "$base.kicad_pcb")
    }
    Invoke-Checked $cli @('pcb', 'render', '--side', 'top', '--rotate', '35,0,30', '--width', '1600',
        '--height', '1600', '--quality', 'high', '--zoom', '0.85',
        '-o', (Join-Path $gen 'isometric.png'), "$base.kicad_pcb")
    Invoke-Checked $cli @('pcb', 'export', 'step', '--force', '--subst-models', '--user-origin', '150x100mm',
        '-o', (Join-Path $gen 'populated.step'), "$base.kicad_pcb")
    Invoke-Checked $FreeCADPython @((Join-Path $here 'check_cad.py'))
}
Invoke-Checked 'python' @((Join-Path $here 'check_reports.py'))
Invoke-Checked 'python' @('-m', 'unittest', 'discover', '-s', $here, '-p', 'test_rgbw.py')
