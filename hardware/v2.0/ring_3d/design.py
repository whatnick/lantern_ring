"""Tool-neutral PCB interface and mechanical stack for Lantern Ring v2."""

import json
import hashlib
import math
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
PCB_PATH = HERE.parent / "ring_mono" / "ring_mono.kicad_pcb"


def source_hash(path):
    # Git checkout line endings differ between Windows and Linux.
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def artifact_hash(path):
    path = Path(path)
    if path.suffix.lower() in (".step", ".svg"):
        return source_hash(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_sexpr(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack = []
    root = None
    for token in tokens:
        if token == "(":
            node = []
            if stack:
                stack[-1].append(node)
            elif root is not None:
                raise ValueError("Multiple S-expression roots")
            else:
                root = node
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("Unmatched closing parenthesis")
            stack.pop()
        else:
            if not stack:
                raise ValueError("Token outside S-expression")
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    if stack or root is None:
        raise ValueError("Incomplete S-expression")
    return root


def children(node, name):
    return [item for item in node if isinstance(item, list) and item[0] == name]


def child(node, name):
    matches = children(node, name)
    if len(matches) != 1:
        raise ValueError("Expected exactly one {!r}, got {}".format(name, len(matches)))
    return matches[0]


def xy(node):
    return tuple(float(v) for v in node[1:3])


def pcb_interface(path=PCB_PATH):
    board = parse_sexpr(Path(path).read_text(encoding="utf-8"))
    edges = []
    for item in children(board, "gr_line"):
        if child(item, "layer")[1] == "Edge.Cuts":
            edges.append((xy(child(item, "start")), xy(child(item, "end"))))
    if not edges:
        raise ValueError("PCB has no supported straight Edge.Cuts outline")
    unsupported = children(board, "gr_arc") + children(board, "gr_circle")
    if any(child(item, "layer")[1] == "Edge.Cuts" for item in unsupported):
        raise ValueError("Curved PCB outlines require an explicit interface update")
    first = edges.pop(0)
    vertices = [first[0], first[1]]
    while edges:
        endpoint = vertices[-1]
        for i, (a, b) in enumerate(edges):
            if a == endpoint or b == endpoint:
                vertices.append(b if a == endpoint else a)
                edges.pop(i)
                break
        else:
            raise ValueError("PCB outline is not a single connected polygon")
    if vertices[-1] != vertices[0]:
        raise ValueError("PCB outline is not closed")
    vertices.pop()
    xs, ys = zip(*vertices)
    origin = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)

    def local(point):
        return (point[0] - origin[0], origin[1] - point[1])

    ground = []
    components = []
    for fp in children(board, "footprint"):
        texts = children(fp, "fp_text")
        refs = [t[2] for t in texts if t[1] == "reference"]
        if len(refs) != 1:
            raise ValueError("Expected one footprint reference")
        ref = refs[0]
        at = xy(child(fp, "at"))
        if ref.startswith("TP"):
            pads = children(fp, "pad")
            if (child(fp, "layer")[1] == "F.Cu" and len(pads) == 1
                    and child(pads[0], "net")[2] == "/GND"):
                ground.append((ref, local(at)))
        elif ref.startswith("D"):
            angle = float(child(fp, "at")[3]) if len(child(fp, "at")) > 3 else 0.0
            components.append({"reference": ref, "xy": local(at), "angle": angle})
    if not ground:
        raise ValueError("No front-side /GND pad found")
    rear = [c for c in children(board, "gr_circle") if child(c, "layer")[1] == "B.Mask"]
    if len(rear) != 1:
        raise ValueError("Expected one rear VCC mask opening")
    positive = local(xy(child(rear[0], "center")))
    positive_radius = math.dist(xy(child(rear[0], "center")), xy(child(rear[0], "end")))
    rear_zones = [z for z in children(board, "zone")
                  if child(z, "layer")[1] == "B.Cu" and child(z, "net_name")[1] == "VCC"]
    if len(rear_zones) != 1:
        raise ValueError("Expected one rear VCC plane")
    positive_fill = [local(xy(v)) for v in child(child(rear_zones[0], "filled_polygon"), "pts")[1:]]
    if not point_inside(positive, positive_fill):
        raise ValueError("Rear contact is not inside the filled VCC plane")
    return {
        "source": str(Path(path).relative_to(HERE.parent.parent.parent)),
        "origin": origin,
        "outline": [local(v) for v in vertices],
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
        "thickness": float(child(child(board, "general"), "thickness")[1]),
        "positive": positive,
        "positive_radius": positive_radius,
        "ground_reference": max(ground, key=lambda g: g[1][1])[0],
        "ground": max(ground, key=lambda g: g[1][1])[1],
        "components": components,
    }


def point_inside(point, polygon):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            crossing = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < crossing:
                inside = not inside
    return inside


def offset_polygon(polygon, distance):
    area = sum(a[0] * b[1] - b[0] * a[1]
               for a, b in zip(polygon, polygon[1:] + polygon[:1]))
    sign = 1 if area > 0 else -1
    lines = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        nx, ny = sign * dy / length, -sign * dx / length
        lines.append(((a[0] + distance * nx, a[1] + distance * ny), (dx, dy)))
    result = []
    for (a, u), (b, v) in zip(lines[-1:] + lines[:-1], lines):
        determinant = u[0] * v[1] - u[1] * v[0]
        if abs(determinant) < 1e-10:
            raise ValueError("Polygon has collinear / degenerate edges")
        t = ((b[0] - a[0]) * v[1] - (b[1] - a[1]) * v[0]) / determinant
        result.append((a[0] + t * u[0], a[1] + t * u[1]))
    return result


def load_parameters(path=HERE / "parameters.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def stack(p, pcb):
    working = p["pin_initial_height"] - p["pin_compression"]
    battery_top = p["battery_bottom"] + p["battery_thickness"]
    pcb_top = p["pcb_bottom"] + pcb["thickness"]
    return {
        "working_pin_height": working,
        "battery_top": battery_top,
        "negative_flange": p["battery_bottom"] - working,
        "positive_flange": battery_top + working,
        "pcb_top": pcb_top,
        "assembly_top": pcb_top + p["bezel_height"],
        "highest_component": pcb_top + max(1.1, p["bezel_height"]),
        "profile_above_finger": pcb_top + max(1.1, p["bezel_height"]) - p["bore_top"],
    }


def flexible_fit(p):
    """Uniform-curvature strain screen, not a force, creep or fatigue model."""
    neutral_radius = (p["finger_diameter"] + p["band_wall"]) / 2
    expanded_radius = neutral_radius + p["fit_expansion"] / 2
    strain = p["band_wall"] / 2 * (1 / neutral_radius - 1 / expanded_radius)
    return {
        "nominal_bore": p["finger_diameter"],
        "screening_bore": p["finger_diameter"] + p["fit_expansion"],
        "uniform_curvature_strain": strain,
        "tip_gap": 2 * neutral_radius * math.sin(math.radians(p["band_gap_angle"] / 2)) - p["band_wall"],
        "status": "UNQUALIFIED: uniform-curvature screen only; root strain, force, creep and fatigue require tests",
    }


def validate_parameters(p, pcb):
    for name, value in p.items():
        if isinstance(value, (float, int)) and (not math.isfinite(value) or value <= 0):
            raise ValueError("{} must be finite and positive".format(name))
    s = stack(p, pcb)
    worst = p["printed_stack_tolerance"] + p["pin_height_tolerance"] + p["battery_height_tolerance"]
    if not (0 < p["pin_compression"] - worst
            < p["pin_compression"] + worst < p["pin_max_stroke"]):
        raise ValueError("Pogo tolerance stack loses preload or bottoms out")
    if p["battery_clearance"] < p["battery_radial_tolerance"]:
        raise ValueError("Battery pocket is smaller than the worst-case cell")
    if abs(p["pcb_bottom"] - s["positive_flange"] - 0.05) > 1e-6:
        raise ValueError("Positive SMT pin must meet the rear PCB pad through its 0.05 mm solder land")
    if s["negative_flange"] - p["wire_diameter"] <= p["carrier_bottom"]:
        raise ValueError("Negative solder land protrudes below the cassette")
    if not (p["deck_bottom"] < s["positive_flange"] - p["pin_flange_thickness"]
            < p["deck_floor_top"] < s["positive_flange"]):
        raise ValueError("Positive pin flange is not captured by the contact deck")
    if p["deck_floor_top"] >= p["pcb_bottom"] - 0.6:
        raise ValueError("PCB support lip has no underside wiring clearance")
    if p["body_radius"] - p["track_outer_radius"] < 0.79:
        raise ValueError("Bayonet track leaves less than 0.8 mm outer wall")
    if not (p["carrier_radius"] < p["socket_radius"] < p["lug_outer_radius"]
            < p["track_outer_radius"] < p["body_radius"]):
        raise ValueError("Invalid bayonet radial stack")
    if p["carrier_radius"] - p["battery_radius"] - p["battery_clearance"] < 0.49:
        raise ValueError("Battery well wall is less than 0.5 mm")
    if p["deck_radius"] >= p["deck_pocket_radius"]:
        raise ValueError("Contact deck does not fit the carrier")
    if p["lug_inner_radius"] >= p["carrier_radius"]:
        raise ValueError("Bayonet lugs are disconnected from the cassette")
    if len(p["lug_angles"]) != 3 or len(p["lug_widths"]) != 3:
        raise ValueError("Exactly three bayonet lugs are required")
    if p["lug_angles"] != [0.0, 120.0, 240.0]:
        raise ValueError("Only the three equally spaced bayonet positions are supported")
    if p["screw_angles"] != [0.0, 180.0]:
        raise ValueError("Compact screw towers must flank the two PCB side flats")
    if p["lug_widths"][0] <= max(p["lug_widths"][1:]) + 2 * p["angular_clearance"]:
        raise ValueError("Wide bayonet lug no longer rejects incorrect orientation")
    if p["lock_angle"] + max(p["lug_widths"]) + 2 * p["angular_clearance"] >= 120:
        raise ValueError("Bayonet tracks overlap")
    if (p["lug_bottom"] - p["track_clearance"] <= p["carrier_bottom"]
            or p["lug_bottom"] + p["lug_height"] + p["track_clearance"] >= p["socket_top"]):
        raise ValueError("Bayonet lacks an axial retaining shelf")
    if p["wire_channel_diameter"] <= p["wire_diameter"]:
        raise ValueError("Insulated wire does not fit the channel")
    if (p["wire_channel_y"] - p["wire_channel_diameter"] / 2
            <= p["battery_radius"] + p["battery_clearance"]):
        raise ValueError("Ground wire channel enters the battery pocket")
    if p["pin_bore_diameter"] <= p["pin_body_diameter"]:
        raise ValueError("Pogo barrel does not fit the bore")
    if p["pin_bore_diameter"] >= p["pin_flange_diameter"]:
        raise ValueError("Pogo flange falls through its shoulder")
    if p["pin_flange_bore_diameter"] <= p["pin_flange_diameter"]:
        raise ValueError("Pogo flange does not fit its counterbore")
    if math.hypot(*pcb["positive"]) + p["pin_tip_diameter"] / 2 >= p["battery_radius"]:
        raise ValueError("Positive tip is not on the top battery face")
    if p["pin_tip_diameter"] / 2 + p["battery_radial_tolerance"] >= p["minimum_negative_face_radius"]:
        raise ValueError("Negative tip could reach the positive battery rim")
    if max(math.hypot(*v) for v in pcb["outline"]) + p["pcb_clearance"] >= p["deck_radius"]:
        raise ValueError("PCB does not fit in the contact deck")
    if p["body_radius"] > 12.45 or s["assembly_top"] > 11.221:
        raise ValueError("Compact legacy-derived crown envelope exceeded")
    if p["band_width"] != 11.0:
        raise ValueError("Preserve the measured legacy 11 mm band width")
    if p["band_wall"] != 1.0:
        raise ValueError("Preserve the measured legacy 1 mm band wall")
    if not 45 <= p["band_gap_angle"] <= 80:
        raise ValueError("Split band needs a 45..80 degree bottom opening")
    if p["carrier_bottom"] - p["bore_top"] < 0.5 - 1e-6:
        raise ValueError("Nested finger bore leaves less than 0.5 mm insulating floor")
    if s["profile_above_finger"] > 11.421:
        raise ValueError("Lowered top exceeds the 11.42 mm above-finger budget")
    if p["bezel_height"] < 0.6:
        raise ValueError("Bezel clamp is thinner than 0.6 mm")
    if p["fit_expansion"] > 1.0 or flexible_fit(p)["uniform_curvature_strain"] > 0.005:
        raise ValueError("Elastic fit screen exceeds the unqualified 1 mm / 0.5 percent strain budget")
    return s
