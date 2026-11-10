param(
    [string]$Fritzing = 'C:\Program Files\Fritzing\Fritzing.exe',
    [string]$FreeCADPython = 'C:\Program Files\FreeCAD 0.19\bin\python.exe'
)
$ErrorActionPreference = 'Stop'
& python (Join-Path $PSScriptRoot 'generate_harness.py') --fritzing (Split-Path $Fritzing)
if ($LASTEXITCODE) { throw 'Harness generation failed' }
foreach ($view in 'breadboard', 'schematic') {
    $path = Join-Path $PSScriptRoot "arduino_isp_harness_$view.svg"
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
}
$process = Start-Process -FilePath $Fritzing -ArgumentList @('-svg', "`"$PSScriptRoot`"") -PassThru -Wait
if ($process.ExitCode) { throw "Fritzing SVG export failed: $($process.ExitCode)" }
foreach ($view in 'breadboard', 'schematic') {
    $path = Join-Path $PSScriptRoot "arduino_isp_harness_$view.svg"
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing Fritzing export: $path" }
}
$pcb = Join-Path $PSScriptRoot 'arduino_isp_harness_pcb.svg'
if (Test-Path -LiteralPath $pcb) { Remove-Item -LiteralPath $pcb }
$previousPlatform = $env:QT_QPA_PLATFORM
try {
    $env:QT_QPA_PLATFORM = 'offscreen'
    & $FreeCADPython (Join-Path $PSScriptRoot 'preview.py')
    if ($LASTEXITCODE) { throw 'Harness PNG export failed' }
} finally {
    $env:QT_QPA_PLATFORM = $previousPlatform
}
