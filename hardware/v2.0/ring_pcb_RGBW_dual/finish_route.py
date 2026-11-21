"""Import the matching local SES, then require a clean, refilled KiCad board."""

import hashlib
import json
import subprocess

import pcbnew

from generate import CLI, GEN, HERE, NAME, digest


def main():
    design = json.loads((GEN / "design.json").read_text())
    for filename, key in (("parameters.json", "parameters_sha256"),
                          ("generate.py", "generator_sha256"),
                          (NAME + ".kicad_pcb", "placement_board_sha256")):
        if digest(HERE / filename) != design[key]:
            raise RuntimeError("Stale placement: " + filename)
    dsn = GEN / (NAME + ".dsn")
    result = json.loads((GEN / "router-result.json").read_text())
    if hashlib.sha256(dsn.read_bytes()).hexdigest() != result["fixture"]["sha256"]:
        raise RuntimeError("Router result belongs to a different DSN")
    if not result["output_written"] or result["final_state"] != "EXPORTED":
        raise RuntimeError("Router did not write its result")
    if hashlib.sha256((GEN / (NAME + ".ses")).read_bytes()).hexdigest() != result["ses_sha256"]:
        raise RuntimeError("SES does not match the local router export")
    board_path = HERE / (NAME + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    if not pcbnew.ImportSpecctraSES(board, str(GEN / (NAME + ".ses"))):
        raise RuntimeError("SES import failed")
    if not pcbnew.SaveBoard(str(board_path), board, True):
        raise RuntimeError("Routed board save failed")
    subprocess.run([str(CLI), "pcb", "drc", "--refill-zones", "--save-board",
                    "--severity-all", "--schematic-parity", "--exit-code-violations",
                    "--format", "json", "-o", str(GEN / "drc.json"),
                    str(board_path)], check=True)
    design["status"] = "routed"
    design["routing"] = {
        "dsn_sha256": digest(dsn), "ses_sha256": digest(GEN / (NAME + ".ses")),
        "router_result_sha256": digest(GEN / "router-result.json"),
        "board_sha256": digest(board_path),
        "finish_route_sha256": digest(HERE / "finish_route.py"),
    }
    (GEN / "design.json").write_text(json.dumps(design, indent=2) + "\n")


if __name__ == "__main__":
    main()
