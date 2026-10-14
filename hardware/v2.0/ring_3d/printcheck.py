"""Dependency-light STL manufacturability checks (a 3D-print "DRC").

Used by the FreeCAD build and by CI (needs only NumPy). Checks per part:

* binary/ASCII STL load, finite coordinates, non-degenerate triangles
* closed, two-manifold, consistently oriented mesh (every edge used twice, once
  in each direction) with positive volume
* minimum wall thickness: a ray is cast inward from every triangle centroid
  along its inward normal and the distance to the far surface is the local wall
  thickness (the same quantity a service bureau's wall-thickness map shows)
* bounding box against the printer build volume

Run ``python printcheck.py generated/*.stl`` for a report.
"""

import argparse
import json
from pathlib import Path
import struct
import sys

import numpy as np

MIN_WALL = 1.0
SEARCH = 4.0
CHUNK = 192
FACING = 0.5


def read_stl(path):
    data = Path(path).read_bytes()
    triangles = None
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if 84 + 50 * count == len(data):
            record = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
            triangles = np.frombuffer(data, record, count, 84)["v"].astype(np.float64)
    if triangles is None:
        values = [float(line.split()[i]) for line in data.decode("ascii").splitlines()
                  for i in (1, 2, 3) if line.strip().startswith("vertex")]
        triangles = np.array(values, dtype=np.float64).reshape(-1, 3, 3)
    return triangles


def mesh_topology(triangles, tolerance=1e-4):
    """Return (watertight, problems, signed volume) for the triangle soup."""
    problems = []
    if not np.isfinite(triangles).all():
        return False, ["non-finite coordinates"], 0.0
    flat = np.round(triangles.reshape(-1, 3) / tolerance).astype(np.int64)
    _, inverse = np.unique(flat, axis=0, return_inverse=True)
    index = inverse.reshape(-1, 3)
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    area = np.linalg.norm(cross, axis=1) / 2
    degenerate = int((area < 1e-9).sum())
    if degenerate:
        problems.append("{} degenerate triangles".format(degenerate))
    keep = area >= 1e-9
    edges = np.concatenate([index[keep][:, [0, 1]], index[keep][:, [1, 2]],
                            index[keep][:, [2, 0]]])
    forward = edges[:, 0] * (index.max() + 1) + edges[:, 1]
    backward = edges[:, 1] * (index.max() + 1) + edges[:, 0]
    f_vals, f_counts = np.unique(forward, return_counts=True)
    b_vals, b_counts = np.unique(backward, return_counts=True)
    if (f_counts > 1).any():
        problems.append("{} edges used more than once in the same direction "
                        "(non-manifold or flipped faces)".format(int((f_counts > 1).sum())))
    if not (len(f_vals) == len(b_vals) and (f_vals == b_vals).all()):
        problems.append("open mesh: {} unmatched edges".format(
            len(np.setxor1d(f_vals, b_vals))))
    volume = float(np.einsum("ij,ij->i", triangles[:, 0],
                             np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6)
    if volume <= 0:
        problems.append("non-positive volume {:.3f} mm^3 (inverted normals?)".format(volume))
    return not problems, problems, volume


def wall_thickness(triangles, search=SEARCH):
    """Local wall thickness at each triangle centroid (np.inf if > ``search``)."""
    v0, v1, v2 = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    _, inverse = np.unique(np.round(triangles.reshape(-1, 3) / 1e-4).astype(np.int64),
                           axis=0, return_inverse=True)
    vid = inverse.reshape(-1, 3)
    e1, e2 = v1 - v0, v2 - v0
    cross = np.cross(e1, e2)
    length = np.linalg.norm(cross, axis=1)
    live = length > 1e-12
    normal = np.zeros_like(cross)
    normal[live] = cross[live] / length[live, None]
    centroid = (v0 + v1 + v2) / 3
    direction = -normal
    origin = centroid + direction * 1e-3
    lo = np.minimum(np.minimum(v0, v1), v2)
    hi = np.maximum(np.maximum(v0, v1), v2)
    cell = np.floor(centroid / 2.0).astype(np.int64)
    order = np.lexsort((cell[:, 2], cell[:, 1], cell[:, 0]))
    result = np.full(len(triangles), np.inf)
    for start in range(0, len(order), CHUNK):
        ids = order[start:start + CHUNK]
        ids = ids[live[ids]]
        if len(ids) == 0:
            continue
        box_lo = origin[ids].min(axis=0) - search
        box_hi = origin[ids].max(axis=0) + search
        near = np.nonzero(((hi >= box_lo) & (lo <= box_hi)).all(axis=1) & live)[0]
        d = direction[ids][:, None, :]
        p = np.cross(d, e2[near][None, :, :])
        det = np.einsum("tj,stj->st", e1[near], p)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        s = origin[ids][:, None, :] - v0[near][None, :, :]
        u = np.einsum("stj,stj->st", s, p) * inv
        q = np.cross(s, e1[near][None, :, :])
        w = np.einsum("sj,stj->st", direction[ids], q) * inv
        t = np.einsum("tj,stj->st", e2[near], q) * inv
        hit = ok & (u >= -1e-9) & (w >= -1e-9) & (u + w <= 1 + 1e-9) & (t > 1e-6) & (t < search)
        # neighbours sharing a vertex are the same surface, not the opposite wall
        shared = (vid[ids][:, None, :, None] == vid[near][None, :, None, :]).any(axis=(2, 3))
        hit &= ~shared
        # only an exit surface facing back along the ray is an opposing wall
        hit &= np.einsum("sj,tj->st", direction[ids], normal[near]) > FACING
        t = np.where(hit, t, np.inf)
        result[ids] = t.min(axis=1) + 1e-3
    return centroid, result


def check_stl(path, min_wall=MIN_WALL, build_volume=(180, 180, 180), emboss=None):
    """`emboss=(height, min_width)` relaxes the limit for raised detail on the z=0 face."""
    triangles = read_stl(path)
    watertight, problems, volume = mesh_topology(triangles)
    centroid, thickness = wall_thickness(triangles)
    finite = np.isfinite(thickness)
    worst = int(np.argmin(thickness))
    limit = np.full(len(thickness), float(min_wall))
    if emboss:
        limit[centroid[:, 2] <= triangles.reshape(-1, 3).min(axis=0)[2] + emboss[0] + 1e-3] = emboss[1]
    bad = thickness < limit
    worst = int(np.argmin(thickness - limit))
    size = (triangles.reshape(-1, 3).max(axis=0) - triangles.reshape(-1, 3).min(axis=0))
    if (size > np.array(build_volume)).any():
        problems.append("exceeds build volume {}".format(build_volume))
    thin = []
    if bad.any():
        points = centroid[bad]
        values = thickness[bad]
        for index in np.argsort(values)[:5]:
            thin.append({"thickness": round(float(values[index]), 3),
                         "at": [round(float(c), 2) for c in points[index]]})
    return {
        "file": Path(path).name,
        "triangles": int(len(triangles)),
        "watertight": watertight,
        "volume_mm3": round(volume, 3),
        "size_mm": [round(float(c), 3) for c in size],
        "min_thickness_mm": round(float(thickness[worst]), 3),
        "min_thickness_at": [round(float(c), 2) for c in centroid[worst]],
        "thin_triangles": int(bad.sum()),
        "thin_examples": thin,
        "problems": problems,
        "passes": watertight and not problems and not bad.any(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stl", nargs="+", type=Path)
    parser.add_argument("--min-wall", type=float, default=MIN_WALL)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    reports = [check_stl(path, args.min_wall) for path in args.stl]
    for report in reports:
        print("{:28s} min wall {:6.3f} mm at {}  thin tris {:5d}  {}".format(
            report["file"], report["min_thickness_mm"], report["min_thickness_at"],
            report["thin_triangles"], "PASS" if report["passes"] else "FAIL"))
        for problem in report["problems"]:
            print("    " + problem)
        for example in report["thin_examples"]:
            print("    thin {thickness} mm at {at}".format(**example))
    if args.json:
        args.json.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    return 0 if all(r["passes"] for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
