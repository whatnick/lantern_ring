param(
    [string]$FreeCADPython,
    [string]$Output = (Join-Path $PSScriptRoot 'generated')
)

$ErrorActionPreference = 'Stop'
if (-not $FreeCADPython) {
    $candidates = Get-ChildItem "$env:ProgramFiles\FreeCAD*\bin\python.exe" -ErrorAction SilentlyContinue
    if (-not $candidates) {
        throw 'FreeCAD Python not found. Pass -FreeCADPython with the bundled python.exe path.'
    }
    $FreeCADPython = ($candidates | Sort-Object FullName -Descending | Select-Object -First 1).FullName
}
& $FreeCADPython (Join-Path $PSScriptRoot 'lantern_ring.py') --output $Output
if ($LASTEXITCODE -ne 0) {
    throw "FreeCAD build failed with exit code $LASTEXITCODE"
}
