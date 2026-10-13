"""Pre-route GND: drop every SMD GND pad to the In2.Cu plane, then export a DSN.

Run with KiCad's bundled Python:
    python route_ground_first.py ring_motion_rgb.kicad_pcb out.kicad_pcb out.dsn

The GND vias and stubs become fixed wiring in the DSN, so FreeRouting routes
all other nets around them.
"""

import math
import sys

import pcbnew

MM = pcbnew.FromMM
VIA_D, VIA_DRILL, TRACK, CLEAR = 0.5, 0.25, 0.15, 0.15
CENTER = (136.906, 83.185 - (-0.381) * 0)  # board datum (global mm)
BATTERY = (136.906, 83.185 - 0.381)
KEEP_R = 3.1 + VIA_D / 2 + 0.1


def other_net_clear(board, pos, net, ignore):
    r = (VIA_D / 2 + CLEAR) * 1e6
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == net or pad is ignore:
                continue
            box = pad.GetBoundingBox()
            box.Inflate(int(r))
            if box.Contains(pos):
                return False
    for tr in board.GetTracks():
        is_via = tr.Type() == pcbnew.PCB_VIA_T
        if tr.GetNetCode() == net and not is_via:
            continue
        if math.hypot(tr.GetStart().x - pos.x, tr.GetStart().y - pos.y) < MM(VIA_D + CLEAR + 0.1):
            return False
    return True


def inside_board(board, pos, margin_mm=0.35):
    box = board.GetBoardEdgesBoundingBox()
    m = MM(margin_mm)
    x, y = pos.x, pos.y
    cx, cy = box.GetCenter().x, box.GetCenter().y
    hw, hh = box.GetWidth() / 2 - m, box.GetHeight() / 2 - m
    # Octagonal outline: cut corners.
    cut = MM(4.2)
    dx, dy = abs(x - cx), abs(y - cy)
    return dx <= hw and dy <= hh and (hw - dx) + (hh - dy) >= cut


def main(src, dst, dsn):
    board = pcbnew.LoadBoard(src)
    settings = board.GetDesignSettings()
    settings.m_TrackMinWidth = MM(TRACK)
    settings.m_MinThroughDrill = MM(VIA_DRILL)
    settings.m_ViasMinSize = MM(VIA_D)
    placed = 0
    for net_name in ("/GND", "VCC"):
        placed += drop_net(board, board.FindNet(net_name))
    print("plane vias placed:", placed)
    pcbnew.SaveBoard(dst, board)
    pcbnew.ExportSpecctraDSN(board, dsn)


def drop_net(board, ground):
    gnet = ground.GetNetCode()
    placed = 0
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("TP"):
            continue
        for pad in fp.Pads():
            if pad.GetNetCode() != gnet or pad.HasHole():
                continue
            if pad.GetLayer() != pcbnew.F_Cu or pad.IsOnLayer(pcbnew.B_Cu):
                continue
            center = pad.GetPosition()
            size = pad.GetSize()
            target = None
            # Large pads (QFN exposed pad) take the via directly in the pad.
            if min(size.x, size.y) > MM(1.2):
                target = center
                stub = False
            else:
                stub = True
                for dist in (0.55, 0.7, 0.85, 1.0, 1.2):
                    for k in range(16):
                        a = 2 * math.pi * k / 16
                        p = pcbnew.VECTOR2I(
                            center.x + int(MM(dist) * math.cos(a)),
                            center.y + int(MM(dist) * math.sin(a)),
                        )
                        if math.hypot(
                            p.x - MM(BATTERY[0]), p.y - MM(BATTERY[1])
                        ) < MM(KEEP_R):
                            continue
                        if inside_board(board, p) and other_net_clear(
                            board, p, gnet, pad
                        ):
                            target = p
                            break
                    if target:
                        break
            if target is None:
                print("no GND via spot for", fp.GetReference(), pad.GetNumber())
                continue
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(target)
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetWidth(pcbnew.F_Cu, MM(VIA_D))
            via.SetDrill(MM(VIA_DRILL))
            via.SetNet(ground)
            board.Add(via)
            if stub:
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(center)
                tr.SetEnd(target)
                tr.SetWidth(MM(TRACK))
                tr.SetLayer(pcbnew.F_Cu)
                tr.SetNet(ground)
                board.Add(tr)
            placed += 1
    return placed


if __name__ == "__main__":
    main(*sys.argv[1:4])
