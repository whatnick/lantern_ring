"""Fail unless every generated ERC/DRC report is clean; record validation.json."""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "generated")
REPORTS = [
    "ring_ir_prog_probe_erc.json", "ring_ir_prog_probe_drc.json",
    "ring_ir_prog_anvil_erc.json", "ring_ir_prog_anvil_drc.json",
    "ring_ir_prog_fence_drc.json",
]
SOURCES = [
    "parameters.json", "generate.py",
    "probe/ring_ir_prog_probe.kicad_pcb", "probe/ring_ir_prog_probe.kicad_sch",
    "anvil/ring_ir_prog_anvil.kicad_pcb", "anvil/ring_ir_prog_anvil.kicad_sch",
    "fence/ring_ir_prog_fence.kicad_pcb",
    "ring_ir_prog_clip.pretty/Pogo_P75_THT.kicad_mod",
    "ring_ir_prog_clip.pretty/GND_Anvil_Pad.kicad_mod",
]


def violations(report):
    items = list(report.get("violations", []))
    for sheet in report.get("sheets", []):
        items += sheet.get("violations", [])
    items += report.get("unconnected_items", []) + report.get("schematic_parity", [])
    return items


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read().replace(b"\r\n", b"\n")).hexdigest()


def main():
    summary, failed = {}, False
    for name in REPORTS:
        path = os.path.join(GEN, name)
        if not os.path.exists(path):
            print("missing", name)
            failed = True
            continue
        with open(path, encoding="utf-8") as handle:
            items = violations(json.load(handle))
        summary[name] = len(items)
        for item in items:
            failed = True
            print(name, item["severity"], item["type"], item["description"],
                  [i["description"] for i in item.get("items", [])])
    with open(os.path.join(GEN, "geometry.json"), encoding="utf-8") as handle:
        geometry = json.load(handle)
    result = {
        "status": "fail" if failed else "pass",
        "violations": summary,
        "unmeasured": geometry["unmeasured"],
        "target_sha256": geometry["target_sha256"],
        "sources_sha256": {name: sha256(os.path.join(HERE, name)) for name in SOURCES},
        "scope": "KiCad ERC/DRC and generated geometry only; no physical fit, contact or programming test",
    }
    with open(os.path.join(GEN, "validation.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "violations", "unmeasured")}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
