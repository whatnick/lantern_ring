"""Read actual IR PCB layers and pad centres with KiCad's bundled Python."""
import json
from pathlib import Path

import pcbnew

import assembly_interface as interface

HERE = Path(__file__).resolve().parent


def contour(line):
    return [[round(pcbnew.ToMM(line.CPoint(i).x), 6),
             round(pcbnew.ToMM(line.CPoint(i).y), 6)] for i in range(line.PointCount())]


def board_layers(board):
    layers = {}
    for name, layer in (("front_copper", pcbnew.F_Cu), ("rear_copper", pcbnew.B_Cu),
                        ("front_openings", pcbnew.F_Mask), ("rear_openings", pcbnew.B_Mask),
                        ("front_silk", pcbnew.F_SilkS), ("rear_silk", pcbnew.B_SilkS)):
        polygons = pcbnew.SHAPE_POLY_SET()
        board.ConvertBrdLayerToPolygonalContours(layer, polygons)
        polygons.Simplify()
        layers[name] = [
            {"outer": contour(polygons.Outline(i)),
             "holes": [contour(polygons.Hole(i, j)) for j in range(polygons.HoleCount(i))]}
            for i in range(polygons.OutlineCount())]
    return layers


def main():
    board_path = HERE / ".." / "ring_pcb_IR" / "ring_pcb_IR.kicad_pcb"
    board = pcbnew.LoadBoard(str(board_path))
    pads = {}
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("TP"):
            pad = list(fp.Pads())[0]
            pos = pad.GetPosition()
            pads[fp.GetReference()] = {
                "xy_mm": [pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)],
                "size_mm": [pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)],
                "net": pad.GetNetname(),
            }
    layers = board_layers(board)
    x = sorted({round(pads[r]["xy_mm"][0], 6) for r in ("TP1", "TP2", "TP3", "TP4", "TP5", "TP6")})
    y = sorted({round(pads[r]["xy_mm"][1], 6) for r in ("TP1", "TP2", "TP3", "TP4", "TP5", "TP6")})
    pitch = {"x_mm": [round(b - a, 6) for a, b in zip(x, x[1:])],
             "y_mm": [round(b - a, 6) for a, b in zip(y, y[1:])],
             "pad_width_mm": 1.0,
             "edge_gap_mm": round(x[1] - x[0] - 1.0, 6)}
    result = {"board_sha256": interface.sha256(board_path),
              "exporter_sha256": interface.sha256(__file__),
              "thickness_mm": pcbnew.ToMM(board.GetDesignSettings().GetBoardThickness()),
              "origin_xy_mm": pads["TP3"]["xy_mm"], "pads": pads,
              "measured_from_file": pitch, "layers": layers,
              "note": "Layer polygons read directly with pcbnew, not inferred pad locations. "
                      "No component-model fabrication: component envelopes remain separate."}
    out = HERE / "generated" / "assembly" / "ir_board_layers.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pad_centres": pads, "pitch": pitch}, indent=2))
    clip = {}
    for name in ("probe", "anvil", "fence"):
        path = HERE / name / ("ring_ir_prog_" + name + ".kicad_pcb")
        pcb = pcbnew.LoadBoard(str(path))
        clip[name] = {
            "board_sha256": interface.sha256(path), "origin_xy_mm": [150.0, 100.0],
            "layers": board_layers(pcb),
            "pads": [{"ref": fp.GetReference(), "number": p.GetNumber(), "net": p.GetNetname(),
                      "xy_mm": [pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)]}
                     for fp in pcb.GetFootprints() for p in fp.Pads()],
        }
    (out.parent / "clip_board_layers.json").write_text(json.dumps({
        "exporter_sha256": interface.sha256(__file__), "boards": clip,
        "note": "Actual adapter PCB layers. Guide is an unpopulated second probe PCB."
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
