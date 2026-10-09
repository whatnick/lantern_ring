param(
    [string]$FreeCADPython = "C:\Program Files\FreeCAD 0.19\bin\python.exe",
    [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    [switch]$Preview,
    [switch]$SkipExport
)
# Exports the v2 parts and crowns (run crowns.py first), renders the Blender 5 assembly
# animation, encodes lantern_ring_v2_assembly.mp4/.gif into generated/ and renders
# generated/crowns/lineup.png.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$build = Join-Path $here "build"
$out = Join-Path (Split-Path $here) "generated"

if (-not $SkipExport) {
    & $FreeCADPython (Join-Path $here "export_parts.py")
    if ($LASTEXITCODE) { throw "FreeCAD export failed" }
}
Remove-Item (Join-Path $build "frames") -Recurse -ErrorAction SilentlyContinue
$blenderArgs = @("-b", "-P", (Join-Path $here "animate.py"), "--")
if ($Preview) { $blenderArgs += "--preview" }
& $Blender @blenderArgs
if ($LASTEXITCODE) { throw "Blender render failed" }
& $Blender -b -P (Join-Path $here "animate.py") -- --lineup
if ($LASTEXITCODE) { throw "Crown lineup render failed" }

$frames = Join-Path $build "frames\frame_%04d.png"
$mp4 = Join-Path $out "lantern_ring_v2_assembly.mp4"
$gif = Join-Path $out "lantern_ring_v2_assembly.gif"
ffmpeg -y -loglevel error -framerate 24 -i $frames -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart $mp4
if ($LASTEXITCODE) { throw "MP4 encode failed" }
ffmpeg -y -loglevel error -framerate 24 -i $frames -vf "fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" $gif
if ($LASTEXITCODE) { throw "GIF encode failed" }
Write-Host "Wrote $mp4 and $gif"
