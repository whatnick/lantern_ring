"""Route the motion/RGB board's assigned nets on its two copper layers.

The router is deliberately conservative around pads, vias, the PCB edge, and
the rear battery contact. KiCad DRC remains the final authority.
"""

from collections import defaultdict
import heapq
import itertools
import math
from pathlib import Path
import sys

import pcbnew


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PCB_PATH = HERE / "ring_motion_rgb.kicad_pcb"
RING_3D = ROOT / "hardware" / "v2.0" / "ring_3d"
sys.path.insert(0, str(RING_3D))
from design import offset_polygon, pcb_interface, point_inside


GRID = 0.1
TRACK_WIDTH = 0.2
VIA_DIAMETER = 0.5
VIA_DRILL = 0.3
PAD_TRACK_CLEARANCE = 0.3
VIA_PAD_CLEARANCE = 0.55
OTHER_TRACK_CLEARANCE = 0.4
VIA_TRACK_CLEARANCE = 0.55
EDGE_TRACK_MARGIN = 0.21
VIA_COST = 10
POWER_NETS = {"/GND", "VCC"}
NET_ORDER = (
    "ACC_INT", "ACC_SCL", "ACC_SDA",
    "PB0", "PB1", "PB2", "PB5", "PB3", "PB4",
    "PWM_R", "PWM_G", "PWM_B",
    "LIMIT_R", "LIMIT_G", "LIMIT_B",
    "LED_R", "LED_G", "LED_B",
)
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
LAYER_NAMES = {pcbnew.F_Cu: "F.Cu", pcbnew.B_Cu: "B.Cu"}


class Grid:
    def __init__(self, outline, origin, positive, positive_radius):
        self.origin = origin
        self.x_min, self.x_max = -8.9, 8.9
        self.y_min, self.y_max = -9.5, 9.5
        self.nx = round((self.x_max - self.x_min) / GRID) + 1
        self.ny = round((self.y_max - self.y_min) / GRID) + 1
        self.inner_outline = offset_polygon(outline, -EDGE_TRACK_MARGIN)
        self.positive = positive
        self.positive_radius = positive_radius
        self.valid = set()
        for ix in range(self.nx):
            x = self.x_min + ix * GRID
            for iy in range(self.ny):
                y = self.y_min + iy * GRID
                if point_inside((x, y), self.inner_outline):
                    self.valid.add((ix, iy))
        if not self.valid:
            raise ValueError("The routed board outline contains no valid grid cells")

    def index(self, xy):
        return (
            round((xy[0] - self.x_min) / GRID),
            round((xy[1] - self.y_min) / GRID),
        )

    def xy(self, cell):
        return (
            self.x_min + cell[0] * GRID,
            self.y_min + cell[1] * GRID,
        )

    def rectangle(self, blocked, bounds, margin):
        xmin, xmax, ymin, ymax = bounds
        ix0 = max(0, math.floor((xmin - margin - self.x_min) / GRID))
        ix1 = min(self.nx - 1, math.ceil((xmax + margin - self.x_min) / GRID))
        iy0 = max(0, math.floor((ymin - margin - self.y_min) / GRID))
        iy1 = min(self.ny - 1, math.ceil((ymax + margin - self.y_min) / GRID))
        for ix in range(ix0, ix1 + 1):
            x = self.x_min + ix * GRID
            if x < xmin - margin or x > xmax + margin:
                continue
            for iy in range(iy0, iy1 + 1):
                y = self.y_min + iy * GRID
                if ymin - margin <= y <= ymax + margin:
                    blocked.add((ix, iy))

    def circle(self, blocked, center, radius):
        ix0, iy0 = self.index((center[0] - radius, center[1] - radius))
        ix1, iy1 = self.index((center[0] + radius, center[1] + radius))
        center_x, center_y = center
        for ix in range(max(0, ix0), min(self.nx - 1, ix1) + 1):
            for iy in range(max(0, iy0), min(self.ny - 1, iy1) + 1):
                x, y = self.xy((ix, iy))
                if math.hypot(x - center_x, y - center_y) <= radius:
                    blocked.add((ix, iy))

    def capsule(self, blocked, start, end, radius):
        xmin = min(start[0], end[0]) - radius
        xmax = max(start[0], end[0]) + radius
        ymin = min(start[1], end[1]) - radius
        ymax = max(start[1], end[1]) + radius
        ix0, iy0 = self.index((xmin, ymin))
        ix1, iy1 = self.index((xmax, ymax))
        dx, dy = end[0] - start[0], end[1] - start[1]
        length_squared = dx * dx + dy * dy
        for ix in range(max(0, ix0), min(self.nx - 1, ix1) + 1):
            for iy in range(max(0, iy0), min(self.ny - 1, iy1) + 1):
                x, y = self.xy((ix, iy))
                if length_squared:
                    t = max(0.0, min(
                        1.0,
                        ((x - start[0]) * dx + (y - start[1]) * dy)
                        / length_squared,
                    ))
                    closest = (start[0] + t * dx, start[1] + t * dy)
                else:
                    closest = start
                if math.dist((x, y), closest) <= radius:
                    blocked.add((ix, iy))


def local_xy(position, origin):
    return (
        pcbnew.ToMM(position.x) - origin[0],
        origin[1] - pcbnew.ToMM(position.y),
    )


def pad_bounds(pad, origin):
    bounds = pad.GetBoundingBox()
    x0 = pcbnew.ToMM(bounds.GetLeft()) - origin[0]
    x1 = pcbnew.ToMM(bounds.GetRight()) - origin[0]
    y0 = origin[1] - pcbnew.ToMM(bounds.GetBottom())
    y1 = origin[1] - pcbnew.ToMM(bounds.GetTop())
    return min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)


def net_pads(board):
    result = defaultdict(list)
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetCode():
                layer = (
                    pcbnew.F_Cu if pad.GetLayerSet().Contains(pcbnew.F_Cu)
                    else pcbnew.B_Cu
                )
                result[pad.GetNetname()].append(
                    (footprint.GetReference(), pad, layer)
                )
    return result


def raster_route_obstacles(grid, pads_by_net, net, routes, vias):
    blocked = {pcbnew.F_Cu: set(), pcbnew.B_Cu: set()}
    via_blocked = set()
    for other_net, pads in pads_by_net.items():
        for _, pad, layer in pads:
            bounds = pad_bounds(pad, grid.origin)
            grid.rectangle(
                via_blocked, bounds, VIA_PAD_CLEARANCE
            )
            if other_net != net:
                grid.rectangle(
                    blocked[layer], bounds, PAD_TRACK_CLEARANCE
                )
    for route_net, layer, start, end in routes:
        if route_net != net:
            grid.capsule(blocked[layer], start, end, OTHER_TRACK_CLEARANCE)
    for via_net, center in vias:
        grid.circle(via_blocked, center, VIA_TRACK_CLEARANCE)
        if via_net != net:
            for layer in LAYERS:
                grid.circle(blocked[layer], center, VIA_TRACK_CLEARANCE)
    # Keep all non-VCC copper away from the exposed rear battery contact.
    grid.circle(
        blocked[pcbnew.B_Cu],
        grid.positive,
        grid.positive_radius + TRACK_WIDTH / 2 + 0.2,
    )
    grid.circle(
        via_blocked,
        grid.positive,
        grid.positive_radius + VIA_DIAMETER / 2 + 0.2,
    )
    return blocked, via_blocked


def octile(cell, goal):
    dx, dy = abs(cell[0] - goal[0]), abs(cell[1] - goal[1])
    return 14 * min(dx, dy) + 10 * abs(dx - dy)


def find_path(grid, blocked, via_blocked, start, goal):
    start_xy, start_layer = start
    goal_xy, goal_layer = goal
    start_cell = grid.index(start_xy)
    goal_cell = grid.index(goal_xy)
    start_state = (start_cell[0], start_cell[1], start_layer)
    goal_state = (goal_cell[0], goal_cell[1], goal_layer)
    counter = itertools.count()
    queue = [(octile(start_cell, goal_cell), next(counter), start_state)]
    costs = {start_state: 0}
    parent = {}
    moves = (
        (-1, 0, 10), (1, 0, 10), (0, -1, 10), (0, 1, 10),
        (-1, -1, 14), (-1, 1, 14), (1, -1, 14), (1, 1, 14),
    )

    while queue:
        _, _, current = heapq.heappop(queue)
        if current == goal_state:
            path = [current]
            while current in parent:
                current = parent[current]
                path.append(current)
            path.reverse()
            return path
        x, y, layer_index = current
        current_cost = costs[current]
        layer = LAYERS[layer_index]
        for dx, dy, step_cost in moves:
            nx, ny = x + dx, y + dy
            cell = (nx, ny)
            if cell not in grid.valid:
                continue
            if cell in blocked[layer] and cell != goal_cell:
                continue
            if dx and dy:
                if (
                    (x + dx, y) not in grid.valid
                    or (x, y + dy) not in grid.valid
                    or (x + dx, y) in blocked[layer]
                    or (x, y + dy) in blocked[layer]
                ):
                    continue
            neighbor = (nx, ny, layer_index)
            new_cost = current_cost + step_cost
            if new_cost >= costs.get(neighbor, math.inf):
                continue
            costs[neighbor] = new_cost
            parent[neighbor] = current
            estimate = octile(cell, goal_cell)
            if layer_index != goal_state[2]:
                estimate += VIA_COST
            heapq.heappush(
                queue, (new_cost + estimate, next(counter), neighbor)
            )
        other_layer_index = 1 - layer_index
        if (x, y) not in via_blocked:
            neighbor = (x, y, other_layer_index)
            new_cost = current_cost + VIA_COST
            if new_cost < costs.get(neighbor, math.inf):
                costs[neighbor] = new_cost
                parent[neighbor] = current
                estimate = octile((x, y), goal_cell)
                if other_layer_index != goal_state[2]:
                    estimate += VIA_COST
                heapq.heappush(
                    queue, (new_cost + estimate, next(counter), neighbor)
                )
    return None


def compress_path(path):
    if len(path) < 3:
        return path
    result = [path[0]]
    previous_direction = None
    for index in range(1, len(path)):
        previous = path[index - 1]
        current = path[index]
        if previous[2] != current[2]:
            result.append(previous)
            result.append(current)
            previous_direction = None
            continue
        direction = (
            current[0] - previous[0],
            current[1] - previous[1],
        )
        if previous_direction is not None and direction != previous_direction:
            result.append(previous)
        previous_direction = direction
    result.append(path[-1])
    deduplicated = []
    for item in result:
        if not deduplicated or item != deduplicated[-1]:
            deduplicated.append(item)
    return deduplicated


def board_position(local, origin):
    return origin[0] + local[0], origin[1] - local[1]


def add_track(board, net_code, layer, start, end, routes, origin):
    if math.dist(start, end) < 1e-4:
        return
    start_global = board_position(start, origin)
    end_global = board_position(end, origin)
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pcbnew.VECTOR2I(
        pcbnew.FromMM(start_global[0]), pcbnew.FromMM(start_global[1])
    ))
    track.SetEnd(pcbnew.VECTOR2I(
        pcbnew.FromMM(end_global[0]), pcbnew.FromMM(end_global[1])
    ))
    track.SetWidth(pcbnew.FromMM(TRACK_WIDTH))
    track.SetLayer(layer)
    track.SetNetCode(net_code)
    board.Add(track)
    routes.append((track.GetNetname(), layer, start, end))


def add_via(board, net_code, xy, net_name, vias, origin):
    via_global = board_position(xy, origin)
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(
        pcbnew.VECTOR2I(
            pcbnew.FromMM(via_global[0]), pcbnew.FromMM(via_global[1])
        )
    )
    via.SetWidth(pcbnew.FromMM(VIA_DIAMETER))
    via.SetDrill(pcbnew.FromMM(VIA_DRILL))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNetCode(net_code)
    board.Add(via)
    vias.append((net_name, xy))


def route_pair(board, grid, net_name, source, target, routes, vias):
    blocked, via_blocked = raster_route_obstacles(
        grid, net_pads(board), net_name, routes, vias
    )
    start_xy = local_xy(source[1].GetPosition(), grid.origin)
    goal_xy = local_xy(target[1].GetPosition(), grid.origin)
    start_layer = 0 if source[2] == pcbnew.F_Cu else 1
    goal_layer = 0 if target[2] == pcbnew.F_Cu else 1
    path = find_path(
        grid, blocked, via_blocked,
        (start_xy, start_layer), (goal_xy, goal_layer),
    )
    if path is None:
        raise RuntimeError(
            "No route found for {} {}.{} to {}.{}".format(
                net_name, source[0], source[1].GetNumber(),
                target[0], target[1].GetNumber(),
            )
        )
    path = compress_path(path)
    points = [
        (grid.xy((ix, iy)), LAYERS[layer])
        for ix, iy, layer in path
    ]
    if math.dist(start_xy, points[0][0]) > 1e-4:
        points.insert(0, (start_xy, points[0][1]))
    if math.dist(goal_xy, points[-1][0]) > 1e-4:
        points.append((goal_xy, points[-1][1]))

    net_code = source[1].GetNetCode()
    for index in range(1, len(points)):
        previous_xy, previous_layer = points[index - 1]
        current_xy, current_layer = points[index]
        if previous_layer != current_layer:
            if previous_xy != current_xy:
                raise ValueError("Layer transition is not at a via coordinate")
            add_via(
                board, net_code, previous_xy, net_name, vias, grid.origin
            )
            continue
        add_track(
            board, net_code, current_layer, previous_xy, current_xy, routes,
            grid.origin,
        )
    return len(path), sum(1 for a, b in zip(points, points[1:]) if a[1] != b[1])


def route_all():
    board = pcbnew.LoadBoard(str(PCB_PATH))
    for track in list(board.GetTracks()):
        board.Remove(track)
    interface = pcb_interface(PCB_PATH)
    grid = Grid(
        interface["outline"],
        interface["origin"],
        interface["positive"],
        interface["positive_radius"],
    )
    grouped = net_pads(board)
    routes = []
    vias = []
    reports = []
    ordered_nets = [
        name for name in NET_ORDER
        if name in grouped and len(grouped[name]) > 1
    ]
    ordered_nets.extend(sorted(
        name for name in grouped
        if name not in NET_ORDER and name not in POWER_NETS and len(grouped[name]) > 1
    ))
    for name in ordered_nets:
        pads = sorted(
            grouped[name],
            key=lambda entry: (entry[0], entry[1].GetNumber()),
        )
        root = pads[0]
        for target in pads[1:]:
            length, via_count = route_pair(
                board, grid, name, root, target, routes, vias
            )
            reports.append({
                "net": name,
                "from": root[0] + "." + root[1].GetNumber(),
                "to": target[0] + "." + target[1].GetNumber(),
                "grid_steps": length,
                "vias": via_count,
            })
    pcbnew.SaveBoard(str(PCB_PATH), board)
    print("Routed {} connections with {} track segments and {} vias".format(
        len(reports), len(routes), len(vias)
    ))
    for report in reports:
        print(report)


if __name__ == "__main__":
    route_all()
