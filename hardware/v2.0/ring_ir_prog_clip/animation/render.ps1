param(
    [string]$FreeCADPython = "C:\Program Files\FreeCAD 0.19\bin\python.exe",
    [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    [switch]$SkipCAD,
    [switch]$StillsOnly
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot
$out = Join-Path $root "generated\assembly"
if (-not $SkipCAD) {
    & $FreeCADPython (Join-Path $root "assembly_model.py")
    if ($LASTEXITCODE) { throw "FreeCAD assembly validation failed" }
}
& $Blender -b -t 6 -P (Join-Path $PSScriptRoot "assemble.py") -- --stills
if ($LASTEXITCODE) { throw "Blender stills failed" }
if ($StillsOnly) { return }
& $Blender -b -t 6 -P (Join-Path $PSScriptRoot "assemble.py")
if ($LASTEXITCODE) { throw "Blender animation failed" }
$frames = Join-Path $PSScriptRoot "build\frame_%04d.png"
& ffmpeg -y -loglevel error -framerate 20 -i $frames -frames:v 360 -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart (Join-Path $out "clip_assembly.mp4")
if ($LASTEXITCODE) { throw "MP4 encode failed" }
& ffmpeg -y -loglevel error -framerate 20 -i $frames -frames:v 360 -vf "fps=10,scale=660:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" (Join-Path $out "clip_assembly.gif")
if ($LASTEXITCODE) { throw "GIF encode failed" }
Write-Host "Wrote $out\clip_assembly.mp4 and .gif"
