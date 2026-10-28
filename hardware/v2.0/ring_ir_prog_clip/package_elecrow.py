"""Validate and package three bare-PCB jobs for an Elecrow quotation."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

import check_reports

HERE = Path(__file__).resolve().parent
BOARDS = (
    ("probe", "ring_ir_prog_probe", 2),
    ("anvil", "ring_ir_prog_anvil", 1),
    ("fence", "ring_ir_prog_fence", 1),
)
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"
GERBER_SUFFIXES = (
    "-F_Cu.gtl", "-B_Cu.gbl", "-F_Mask.gts", "-B_Mask.gbs",
    "-F_Silkscreen.gto", "-B_Silkscreen.gbo", "-Edge_Cuts.gm1",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    result = subprocess.run(
        [str(arg) for arg in args], capture_output=True, text=True
    )
    if result.returncode:
        raise RuntimeError("Command failed: {}\n{}\n{}".format(
            result.args, result.stdout, result.stderr))
    return result.stdout.strip()


def board_dimensions(python, board):
    code = (
        "import json, pcbnew, sys\n"
        "b = pcbnew.LoadBoard(sys.argv[1])\n"
        "p = pcbnew.SHAPE_POLY_SET()\n"
        "assert b.GetBoardPolygonOutlines(p, False), 'Invalid board outline'\n"
        "r = p.BBox()\n"
        "print(json.dumps({'width_mm': pcbnew.ToMM(r.GetWidth()),"
        "'height_mm': pcbnew.ToMM(r.GetHeight()),"
        "'thickness_mm': pcbnew.ToMM(b.GetDesignSettings().GetBoardThickness()),"
        "'copper_layers': b.GetCopperLayerCount()}))\n"
    )
    return json.loads(run(python, "-c", code, board))


def write_zip(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, name in sorted(files, key=lambda pair: pair[1]):
            archive.write(source, name)
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError("Corrupt ZIP member: " + bad)


def prepare(cli, sets, color):
    validation = json.loads((HERE / "generated" / "validation.json").read_text())
    if validation["status"] != "pass":
        raise ValueError("Existing clip validation is not passing")
    for relative, expected in validation["sources_sha256"].items():
        if check_reports.sha256(HERE / relative) != expected:
            raise ValueError("Rebuild clip before packaging changed source: " + relative)
    geometry = json.loads((HERE / "generated" / "geometry.json").read_text())
    target = HERE / geometry["target_board"]
    if check_reports.sha256(target) != validation["target_sha256"]:
        raise ValueError("IR target has changed; rebuild and validate its adapter")

    output = HERE / "fab" / "elecrow"
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": run("git", "-C", HERE, "rev-parse", "HEAD"),
        "kicad_version": run(cli, "version"),
        "packager_sha256": check_reports.sha256(Path(__file__)),
        "scope": "Bare PCB quotation only; no assembly, parts, stencil or production authorization",
        "sets": sets,
        "settings": {
            "material": "FR-4", "layers": 2, "finished_thickness_mm": 1.6,
            "outer_copper_oz": 1, "solder_mask": color + ", both sides",
            "silkscreen": "white, as supplied", "finish": "ENIG (immersion gold)",
            "electrical_test": "100% for copper-bearing probe and anvil",
            "delivery": "Separate routed boards, not a customer-designed panel",
        },
        "target_sha256": validation["target_sha256"],
        "source_sha256": validation["sources_sha256"],
        "jobs": [],
        "reports": {},
    }
    with tempfile.TemporaryDirectory(prefix="lantern-ring-elecrow-") as temporary:
        staging = Path(temporary)
        reports = staging / "validation"
        reports.mkdir()
        for directory, name, copies in BOARDS:
            board = HERE / directory / (name + ".kicad_pcb")
            base = board.with_suffix("")
            editor = {
                path: path.read_bytes()
                for path in (base.with_suffix(".kicad_pro"), base.with_suffix(".kicad_prl"))
                if path.exists()
            }
            job_dir = staging / name
            job_dir.mkdir()
            try:
                drc = reports / (name + "_drc.json")
                args = ["pcb", "drc", "--severity-all", "--format", "json", "-o", drc]
                if directory != "fence":
                    args += ["--schematic-parity"]
                    run(cli, "sch", "erc", "--severity-all", "--format", "json",
                        "-o", reports / (name + "_erc.json"),
                        base.with_suffix(".kicad_sch"))
                run(cli, *args, board)
                for report in sorted(reports.glob(name + "_*.json")):
                    violations = check_reports.violations(json.loads(report.read_text()))
                    if violations:
                        raise ValueError("ERC/DRC violations: " + str(report) + "\n"
                                         + json.dumps(violations, indent=2))
                    manifest["reports"][report.name] = {
                        "violations": 0, "sha256": digest(report),
                    }
                dimensions = board_dimensions(cli.with_name("python.exe"), board)
                if dimensions["copper_layers"] != 2 or dimensions["thickness_mm"] != 1.6:
                    raise ValueError("Unexpected stackup: " + name)
                run(cli, "pcb", "export", "gerbers", "--no-x2", "--layers", LAYERS,
                    "--subtract-soldermask", "-o", str(job_dir) + "\\", board)
                run(cli, "pcb", "export", "drill", "--format", "excellon",
                    "--drill-origin", "absolute", "--excellon-units", "mm",
                    "--excellon-separate-th", "-o", str(job_dir) + "\\", board)
            finally:
                for path, data in editor.items():
                    path.write_bytes(data)
            files = [(job_dir / (name + suffix), name + suffix) for suffix in GERBER_SUFFIXES]
            for path, _ in files:
                if not path.is_file() or path.stat().st_size == 0:
                    raise ValueError("Missing or empty Gerber: " + str(path))
            for kind in ("PTH", "NPTH"):
                drill = job_dir / (name + "-" + kind + ".drl")
                if drill.exists() and any(
                    line.startswith("T") and "C" in line for line in drill.read_text().splitlines()
                ):
                    files.append((drill, name + "-" + kind + ".txt"))
            notes = job_dir / "FABRICATION-NOTES.txt"
            notes.write_text(
                "QUOTATION ONLY - BARE PCB, NO ASSEMBLY OR PARTS.\n"
                "Job: {name}; quantity: {quantity}; outline: {width_mm} x {height_mm} mm.\n"
                "FR-4, 2 layers, 1.6 mm finished thickness, 1 oz outer copper.\n"
                "{color} mask both sides, white silk as supplied, ENIG finish.\n"
                "Dimensions follow Edge_Cuts.gm1 centreline, not plot stroke width.\n"
                "PTH.txt = plated finished holes; NPTH.txt = unplated slots/holes.\n"
                "Missing drill files mean no holes of that type. Do not invent holes.\n"
                "Route internal cutouts and all slots as supplied; no V-scoring.\n"
                "Keep mask openings and flat ENIG contact P8 free of mask, ink and solder.\n"
                "Do not add order numbers/markings without agreeing a safe position.\n"
                "No paste files, stencil, BOM, placement data or components are required.\n"
                "Supply separated boards. Contact us for DFM changes; do not alter files.\n"
                .format(name=name, quantity=sets * copies, color=color.capitalize(), **dimensions),
                encoding="ascii",
            )
            files.append((notes, notes.name))
            upload = staging / (name + "_elecrow.zip")
            write_zip(upload, files)
            manifest["jobs"].append({
                "board": name, "quantity": sets * copies, **dimensions,
                "role": {"probe": "Upper probe and identical lower guide",
                         "anvil": "Front-side GND contact and component-clearance window",
                         "fence": "Mechanical locator; no functional copper"}[directory],
                "source_sha256": check_reports.sha256(board),
                "upload_zip": upload.name, "zip_sha256": digest(upload),
                "members_sha256": {name: digest(path) for path, name in files},
            })

        rows = "\n".join(
            "- {board}: {quantity} bare boards, {width_mm} x {height_mm} mm; {upload_zip}"
            .format(**job) for job in manifest["jobs"]
        )
        request = (
            "Hello Elecrow PCB team,\n\n"
            "Please provide a fabrication-only quotation for three separate PCB designs:\n"
            + rows + "\n\n"
            "This is a prototype batch for five clip sets (two identical probe/guide PCBs,\n"
            "one ground-contact anvil and one locator fence per set).\n\n"
            "All jobs: FR-4, 2 copper layers, 1.6 mm finished thickness, 1 oz outer copper,\n"
            "{color} solder mask both sides, white silkscreen as supplied, ENIG finish.\n"
            "PCB ONLY: no components, sourcing, soldering, assembly or stencil.\n"
            "Please quote three separate jobs and combine dispatch if possible. Supply\n"
            "separated routed boards; any supplier production panelization is your process.\n"
            "Perform electrical testing on the copper-bearing probe and anvil.\n\n"
            "The anvil's P8 pad is a flat electrical contact: retain its full exposed ENIG\n"
            "area. No HASL, solder coating, mask, ink or order marking on this pad.\n"
            "The probe's seven nominal 1.15 mm PTH holes guide pogo barrels; preserve\n"
            "their finished diameters and position. Its two 2.2 x 3.4 mm mounting slots\n"
            "are NPTH. Preserve all anvil/fence internal routing and corner radii.\n"
            "Please confirm finished thickness, hole/slot and routed-profile tolerances,\n"
            "particularly registration of pogo holes to the anvil/fence locator.\n"
            "Please review narrow rails, internal corners and clearances for DFM and\n"
            "report any issues before changing artwork. Do not add a maker/order code\n"
            "without agreeing a location away from contacts, holes and seating surfaces.\n\n"
            "Please quote fabrication price, any engineering/panel fees, ENIG option and\n"
            "lead time. Freight can be quoted separately after destination confirmation.\n"
            "These are prototype fixtures; mechanical fit/contact/programming have not\n"
            "been physically qualified. Quotation only: do not start production, charge\n"
            "an account or treat this request as a paid manufacturing authorization.\n"
        )
        request = request.replace("five clip sets", "{} clip sets".format(sets))
        request = request.replace("{color}", color)
        (staging / "RFQ.txt").write_text(request, encoding="ascii")
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="ascii"
        )
        shutil.copyfile(output / "README.md", staging / "README.md")
        handoff = staging / "lantern_ring_ir_clip_elecrow_quote.zip"
        write_zip(handoff, [
            (path, path.relative_to(staging).as_posix())
            for path in staging.rglob("*")
            if path.is_file() and path != handoff
            and path.parent in (staging, reports)
        ])
        for path in staging.iterdir():
            if path.is_file():
                shutil.copyfile(path, output / path.name)
        (output / "validation").mkdir(exist_ok=True)
        for path in reports.iterdir():
            shutil.copyfile(path, output / "validation" / path.name)
    print("Prepared quote package:", output)
    print("ERC/DRC: zero violations in all five fresh reports")
    print("Not submitted. No production or payment authorized.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-bin", type=Path,
                        default=Path(r"C:\Program Files\KiCad\10.0\bin"))
    parser.add_argument("--sets", type=int, default=5)
    parser.add_argument("--color", choices=("green", "purple"), default="purple")
    args = parser.parse_args()
    if args.sets < 1:
        parser.error("--sets must be positive")
    prepare(args.kicad_bin / "kicad-cli.exe", args.sets, args.color)


if __name__ == "__main__":
    main()
