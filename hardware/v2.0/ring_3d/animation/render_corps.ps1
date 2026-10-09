param(
    [string]$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    [switch]$Preview
)
# Renders the Lantern Corps crown-swap animation (generated/lantern_corps_swap.mp4/.gif)
# and the hero still (generated/crowns/hero.png). Run crowns.py and export_parts.py
# (or render.ps1) first so animation/build/meshes holds the crown meshes.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$build = Join-Path $here "build"
$out = Join-Path (Split-Path $here) "generated"
$script = Join-Path $here "corps_swap.py"

Remove-Item (Join-Path $build "swap_frames") -Recurse -ErrorAction SilentlyContinue
$swapArgs = @("-b", "-P", $script, "--")
if ($Preview) { $swapArgs += "--preview" }
& $Blender @swapArgs
if ($LASTEXITCODE) { throw "Crown swap render failed" }
$heroArgs = @("-b", "-P", $script, "--", "--hero")
if ($Preview) { $heroArgs += "--preview" }
& $Blender @heroArgs
if ($LASTEXITCODE) { throw "Hero render failed" }

$frames = Join-Path $build "swap_frames\frame_%04d.png"
$mp4 = Join-Path $out "lantern_corps_swap.mp4"
$gif = Join-Path $out "lantern_corps_swap.gif"
ffmpeg -y -loglevel error -framerate 24 -i $frames -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart $mp4
if ($LASTEXITCODE) { throw "MP4 encode failed" }
ffmpeg -y -loglevel error -framerate 24 -i $frames -vf "fps=10,scale=400:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" $gif
if ($LASTEXITCODE) { throw "GIF encode failed" }
Write-Host "Wrote $mp4, $gif and $(Join-Path $out 'crowns\hero.png')"
