"""Fail on stale/rule-violating RGBW results; bind deliverables to source."""

import json
from pathlib import Path

from test_rgbw import GEN, HERE, IR, PCB, digest


def main():
    design = json.loads((GEN / "design.json").read_text())
    if design["status"] != "routed":
        raise RuntimeError("The saved board is not successfully routed")
    expected = [(HERE / "generate.py", design["generator_sha256"]),
                (HERE / "parameters.json", design["parameters_sha256"]),
                (IR, design["source_board_sha256"]),
                (PCB, design["routing"]["board_sha256"]),
                (HERE / "finish_route.py", design["routing"]["finish_route_sha256"])]
    for path, sha in expected:
        if digest(path) != sha:
            raise RuntimeError("Stale routed design: " + str(path))
    for name in ("erc.json", "drc.json"):
        report = json.loads((GEN / name).read_text())
        if name == "drc.json":
            findings = sum((report[k] for k in ("violations", "unconnected_items", "schematic_parity")), [])
        else:
            findings = report.get("violations", []) + sum((s["violations"] for s in report["sheets"]), [])
        if findings:
            raise RuntimeError("Nonzero findings in " + name)
    required = ("schematic.pdf", "top_routing.svg", "bottom_routing.svg",
                "ground_plane.svg", "supply_plane.svg",
                "top.png", "bottom.png", "isometric.png", "populated.step",
                "cad-validation.json", "RGBW_checked.FCStd")
    for name in required:
        if not (GEN / name).is_file() or (GEN / name).stat().st_size == 0:
            raise FileNotFoundError("Required deliverable: " + name)
    cad = json.loads((GEN / "cad-validation.json").read_text())
    if not cad["valid_solids"] or not cad["component_window_screen_passed"]:
        raise RuntimeError("CAD validation did not pass")
    if cad["step_sha256"] != digest(GEN / "populated.step"):
        raise RuntimeError("STEP changed after CAD validation")
    for path, sha in cad["inputs_sha256"].items():
        if digest(HERE / Path(*path.split("/"))) != sha:
            raise RuntimeError("Stale CAD/render input; rerun -Render: " + path)
    if cad["clip_geometry_sha256"] != digest(
            HERE.parent / "ring_ir_prog_clip" / "generated" / "geometry.json"):
        raise RuntimeError("Clip geometry changed; repeat the CAD window screen")
    files = [HERE / name for name in ("generate.py", "parameters.json", "finish_route.py",
             "build.ps1", "check_reports.py", "test_rgbw.py", "sym-lib-table", "fp-lib-table",
             "create_led_model.py", "check_cad.py", "route_local.py", "ring_pcb_RGBW.kicad_sch",
             "ring_pcb_RGBW.kicad_pcb", "ring_pcb_RGBW.kicad_pro", "ring_rgbw.kicad_sym")]
    files += list((HERE / "ring_rgbw.pretty").glob("*.kicad_mod"))
    files += [p for p in (HERE / "models").rglob("*") if p.is_file() and p.suffix in (".step", ".json", ".FCStd")]
    files += [GEN / name for name in required + (
        "erc.json", "drc.json", "netlist.xml", "bom.csv", "design.json",
        "ring_pcb_RGBW.dsn", "ring_pcb_RGBW.ses", "router-result.json", "router.log")]
    report = {"status": "passed", "erc_violations": 0, "drc_violations": 0,
              "unconnected_items": 0, "schematic_parity_issues": 0,
              "source_IR_sha256": digest(IR),
              "scope": "Virtual electrical/interface/CAD checks only; physical and firmware qualification outstanding",
              "files_sha256": {p.relative_to(HERE).as_posix(): digest(p) for p in sorted(files)}}
    (GEN / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("ERC, DRC, connectivity and parity: zero findings; deliverables hash-bound.")


if __name__ == "__main__":
    main()
