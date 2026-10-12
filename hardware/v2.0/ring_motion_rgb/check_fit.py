"""Check the motion/RGB PCB STEP against the v2 cassette and crown STEP files.

Run with FreeCAD's bundled Python after exporting ring_motion_rgb.kicad_pcb
to STEP with KiCad CLI. A conservative U1 body proxy is used if its STEP model
is absent from the export.
"""

import argparse
import json
from pathlib import Path
import sys

import FreeCAD as App
import Part


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RING_3D = ROOT / "hardware" / "v2.0" / "ring_3d"
ASSEMBLY = RING_3D / "generated" / "Lantern_Ring_v2.FCStd"
CROWNS = RING_3D / "generated" / "crowns"
PRINT_PARTS = ("RingBase", "Carrier", "ContactDeck", "Bezel")
U1_BODY_XY = 4.0
U1_BODY_HEIGHT = 1.0
VOLUME_TOLERANCE = 1e-5

sys.path.insert(0, str(RING_3D))
from design import child, children, load_parameters, parse_sexpr, pcb_interface, stack


def qfn_location(pcb_path, origin):
    board = parse_sexpr(Path(pcb_path).read_text(encoding="utf-8"))
    for footprint in children(board, "footprint"):
        references = {
            item[2] for item in children(footprint, "property")
            if item[1] == "Reference"
        }
        references.update(
            item[2] for item in children(footprint, "fp_text")
            if item[1] == "reference"
        )
        if "U1" in references:
            position = child(footprint, "at")
            angle = float(position[3]) if len(position) > 3 else 0.0
            if angle != 0:
                raise ValueError("U1 fit proxy currently requires zero rotation")
            return (
                float(position[1]) - origin[0],
                origin[1] - float(position[2]),
            )
    raise ValueError("Could not find U1 footprint in the PCB")


def has_qfn_model(solids, global_xy):
    x, y = global_xy
    for solid in solids:
        bounds = solid.BoundBox
        if (
            abs((bounds.XMin + bounds.XMax) / 2 - x) < 0.05
            and abs((bounds.YMin + bounds.YMax) / 2 + y) < 0.05
            and bounds.XLength >= 3.8
            and bounds.YLength >= 3.8
            and bounds.ZLength <= 1.2
        ):
            return True
    return False


def inspect_fit(step_path):
    pcb_path = HERE / "ring_motion_rgb.kicad_pcb"
    pcb = pcb_interface(pcb_path)
    parameters = load_parameters()
    levels = stack(parameters, pcb)
    pcb_bottom = parameters["pcb_bottom"]
    pcb_top = levels["pcb_top"]

    board = Part.read(str(step_path))
    if board.isNull() or not board.Solids:
        raise ValueError("PCB STEP export contains no solid geometry")

    origin_x, origin_y = pcb["origin"]
    # KiCad STEP retains global X and negates global Y; the ring design uses
    # board-center-relative coordinates with positive Y toward the PCB top.
    board.translate(App.Vector(-origin_x, origin_y, pcb_bottom))

    assembly = App.openDocument(str(ASSEMBLY))
    parts = {}
    try:
        for name in PRINT_PARTS:
            part = assembly.getObject(name)
            if part is None or part.Shape.isNull():
                raise ValueError("Missing printable assembly part: " + name)
            parts[name] = part.Shape

        ring_interferences = []
        for name, shape in parts.items():
            volume = board.common(shape).Volume
            if volume > VOLUME_TOLERANCE:
                ring_interferences.append({
                    "part": name,
                    "intersection_volume_mm3": round(volume, 6),
                })

        qfn_xy = qfn_location(pcb_path, pcb["origin"])
        qfn_global_xy = (origin_x + qfn_xy[0], -(origin_y - qfn_xy[1]))
        qfn_proxy_used = not has_qfn_model(board.Solids, qfn_global_xy)
        component_solids = [
            solid for solid in board.Solids
            if solid.BoundBox.ZMin >= pcb_bottom + 1.55
        ]
        if qfn_proxy_used:
            qfn_proxy = Part.makeBox(
                U1_BODY_XY,
                U1_BODY_XY,
                U1_BODY_HEIGHT,
                App.Vector(
                    qfn_xy[0] - U1_BODY_XY / 2,
                    qfn_xy[1] - U1_BODY_XY / 2,
                    pcb_top,
                ),
            )
            component_solids.append(qfn_proxy)

        crown_files = sorted(CROWNS.glob("Crown_*.step"))
        if not crown_files:
            raise ValueError("No crown STEP files found")

        crown_interferences = []
        minimum_crown_clearance = None
        for crown_path in crown_files:
            crown = Part.read(str(crown_path))
            if crown.isNull() or not crown.Solids:
                raise ValueError("Invalid crown STEP: " + crown_path.name)
            for index, component in enumerate(component_solids):
                volume = component.common(crown).Volume
                if volume > VOLUME_TOLERANCE:
                    crown_interferences.append({
                        "crown": crown_path.stem,
                        "component_solid": index,
                        "intersection_volume_mm3": round(volume, 6),
                    })
                distance = component.distToShape(crown)[0]
                if minimum_crown_clearance is None or distance < minimum_crown_clearance:
                    minimum_crown_clearance = distance

        top_components = [
            solid for solid in component_solids
            if solid.BoundBox.ZMax > pcb_top
        ]
        return {
            "status": (
                "PASS" if not ring_interferences and not crown_interferences
                else "INTERFERENCE"
            ),
            "pcb_step": step_path.name,
            "printed_parts_checked": list(parts),
            "crown_variants_checked": len(crown_files),
            "component_solids_checked": len(component_solids),
            "qfn_body_proxy_used": qfn_proxy_used,
            "qfn_proxy_mm": (
                [U1_BODY_XY, U1_BODY_XY, U1_BODY_HEIGHT]
                if qfn_proxy_used else None
            ),
            "maximum_component_top_z_mm": round(
                max(solid.BoundBox.ZMax for solid in top_components), 4
            ),
            "minimum_component_to_crown_clearance_mm": round(
                minimum_crown_clearance, 4
            ),
            "ring_interferences": ring_interferences,
            "crown_interferences": crown_interferences,
        }
    finally:
        App.closeDocument(assembly.Name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pcb_step", type=Path, help="KiCad-exported PCB STEP file")
    parser.add_argument(
        "--json", type=Path, help="Optional path for a machine-readable fit report"
    )
    args = parser.parse_args()
    report = inspect_fit(args.pcb_step.resolve())
    output = json.dumps(report, indent=2)
    if args.json:
        args.json.write_text(output + "\n", encoding="utf-8")
    print(output)
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
