param(
    [string]$FreeCADPython = "C:\Program Files\FreeCAD 0.19\bin\python.exe",
    [string]$KiCadPython = "C:\Program Files\KiCad\10.0\bin\python.exe",
    [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    [switch]$SkipCAD,
    [switch]$StillsOnly
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot
$out = Join-Path $root "generated\assembly"
if (-not $SkipCAD) {
    & $KiCadPython (Join-Path $root "export_ir_visual.py")
    if ($LASTEXITCODE) { throw "KiCad IR board layer export failed" }
    & $FreeCADPython (Join-Path $root "fit_check.py") --no-render
    if ($LASTEXITCODE) { throw "FreeCAD STEP header fit failed" }
    & $FreeCADPython (Join-Path $root "assembly_model.py")
    if ($LASTEXITCODE) { throw "FreeCAD assembly validation failed" }
}
& $Blender -b -t 6 -P (Join-Path $PSScriptRoot "assemble.py") -- --stills
if ($LASTEXITCODE) { throw "Blender stills failed" }
if ($StillsOnly) { return }
& $Blender -b -t 6 -P (Join-Path $PSScriptRoot "assemble.py") -- --prepare
if ($LASTEXITCODE) { throw "Blender scene preparation failed" }
# Bound Eevee GPU-resource lifetime on Windows by rendering short fresh-process batches.
$blend = Join-Path $out "clip_assembly.blend"
$prefix = Join-Path $PSScriptRoot "build\frame_"
for ($start = 1; $start -le 440; $start += 30) {
    $end = [Math]::Min(440, $start + 29)
    & $Blender -b $blend -t 6 -o $prefix -s $start -e $end -a
    if ($LASTEXITCODE) { throw "Blender animation frames $start-$end failed" }
}
$frames = Join-Path $PSScriptRoot "build\frame_%04d.png"
& ffmpeg -y -loglevel error -framerate 20 -i $frames -frames:v 440 -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart (Join-Path $out "clip_assembly.mp4")
if ($LASTEXITCODE) { throw "MP4 encode failed" }
& ffmpeg -y -loglevel error -framerate 20 -i $frames -frames:v 440 -vf "fps=10,scale=660:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" (Join-Path $out "clip_assembly.gif")
if ($LASTEXITCODE) { throw "GIF encode failed" }
Write-Host "Wrote $out\clip_assembly.mp4 and .gif"
