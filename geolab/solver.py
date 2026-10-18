"""Adaptive conservative cell cover; no answer-key access and no dependencies."""

import math
import time

PAD_DEG = 1e-8  # Empirical roundoff cushion, NOT directed interval arithmetic.
MAX_RESOLUTION = 256


def circular_distance(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def prepare(scene, observation_ids=None):
    """Validate bounded numerical inputs and resolve explicit correspondences."""
    if observation_ids is None:
        observation_ids = scene.get("default_observations")
    bounds = scene.get("bounds", [])
    if len(bounds) != 4 or not all(_number(v) and abs(v) <= 1e6 for v in bounds):
        raise ValueError("bounds must be four finite coordinates within +/-1e6 metres")
    xmin, ymin, xmax, ymax = bounds
    if not (1e-3 <= xmax - xmin <= 1e6 and 1e-3 <= ymax - ymin <= 1e6):
        raise ValueError("domain dimensions must be between 0.001 and 1e6 metres")
    landmarks = {}
    for lm in scene.get("landmarks", []):
        name = lm.get("id")
        if not isinstance(name, str) or name in landmarks:
            raise ValueError("landmark IDs must be unique strings")
        if not all(_number(lm.get(k)) and abs(lm[k]) <= 1e6 for k in ("x", "y")):
            raise ValueError("landmarks need finite x and y within +/-1e6 metres")
        landmarks[name] = (lm["x"], lm["y"])
    observations = []
    seen = set()
    for obs in scene.get("observations", []):
        name, kind = obs.get("id"), obs.get("kind")
        if not isinstance(name, str) or name in seen:
            raise ValueError("observation IDs must be unique strings")
        seen.add(name)
        ids = obs.get("landmarks", [])
        if kind not in ("bearing", "angle") or len(ids) != (1 if kind == "bearing" else 2):
            raise ValueError("observations need a bearing landmark or two angle landmarks")
        if len(set(ids)) != len(ids) or any(i not in landmarks for i in ids):
            raise ValueError("unknown or repeated landmark correspondence")
        value, tolerance = obs.get("value_deg"), obs.get("tolerance_deg")
        if not _number(value) or not _number(tolerance) or not 0 <= tolerance <= 180:
            raise ValueError("angles must be finite and tolerances between 0 and 180 degrees")
        if kind == "angle" and not 0 <= value <= 180:
            raise ValueError("unsigned angle must be between 0 and 180 degrees")
        if kind == "bearing" and abs(value) > 360000:
            raise ValueError("bearing magnitude exceeds supported range")
        observations.append({**obs, "value_deg": value % 360 if kind == "bearing" else value})
    if observation_ids is not None:
        if not isinstance(observation_ids, (list, tuple)) or len(set(observation_ids)) != len(observation_ids):
            raise ValueError("observation selection must be a list of unique IDs")
        if any(i not in seen for i in observation_ids):
            raise ValueError("unknown observation selection")
        observations = [o for o in observations if o["id"] in observation_ids]
    used = {key for obs in observations for key in obs["landmarks"]}
    return bounds, {k: landmarks[k] for k in used}, observations


def _point_values(point, landmarks):
    values = {}
    for name, (x, y) in landmarks.items():
        dx, dy = x - point[0], y - point[1]
        if dx == 0 and dy == 0:
            return None
        values[name] = math.degrees(math.atan2(dy, dx))
    return values


def _accept(values, observations):
    if values is None:
        return False
    for obs in observations:
        names = obs["landmarks"]
        if obs["kind"] == "bearing":
            residual = circular_distance(values[names[0]], obs["value_deg"])
        else:
            value = circular_distance(values[names[0]], values[names[1]])
            residual = abs(value - obs["value_deg"])
        if residual > obs["tolerance_deg"] + PAD_DEG:
            return False
    return True


def point_feasible(scene, point, observation_ids=None):
    bounds, landmarks, observations = prepare(scene, observation_ids)
    if len(point) != 2 or not all(_number(v) for v in point):
        return False
    if not (bounds[0] <= point[0] <= bounds[2] and bounds[1] <= point[1] <= bounds[3]):
        return False
    return _accept(_point_values(point, landmarks), observations)


def _classify(cx, cy, radius, landmarks, observations):
    values, spreads = {}, {}
    nonsingular = True
    for name, (x, y) in landmarks.items():
        dx, dy = x - cx, y - cy
        distance = math.hypot(dx, dy)
        values[name] = math.degrees(math.atan2(dy, dx))
        if distance <= radius:
            spreads[name] = 180.0
            nonsingular = False
        else:
            spreads[name] = math.degrees(math.asin(min(1, radius / distance))) + PAD_DEG
    inner = nonsingular
    for obs in observations:
        names = obs["landmarks"]
        if obs["kind"] == "bearing":
            residual = circular_distance(values[names[0]], obs["value_deg"])
            spread = spreads[names[0]]
            lo, hi = max(0, residual - spread), min(180, residual + spread)
        else:
            angle = circular_distance(values[names[0]], values[names[1]])
            spread = min(180, spreads[names[0]] + spreads[names[1]])
            low_angle, high_angle = max(0, angle - spread), min(180, angle + spread)
            lo = max(0, low_angle - obs["value_deg"], obs["value_deg"] - high_angle)
            hi = max(abs(low_angle - obs["value_deg"]), abs(high_angle - obs["value_deg"]))
        if lo > obs["tolerance_deg"] + PAD_DEG:
            return -1
        if hi > obs["tolerance_deg"] - PAD_DEG:
            inner = False
    return int(inner)


def _direct_conflict(observations):
    # Same measurement has a single value at any nonsingular camera position.
    for i, a in enumerate(observations):
        for b in observations[i + 1:]:
            if a["kind"] != b["kind"] or sorted(a["landmarks"]) != sorted(b["landmarks"]):
                continue
            delta = (circular_distance(a["value_deg"], b["value_deg"])
                     if a["kind"] == "bearing" else abs(a["value_deg"] - b["value_deg"]))
            if delta > a["tolerance_deg"] + b["tolerance_deg"] + 4 * PAD_DEG:
                return [a["id"], b["id"]]
    return []


def solve(scene, resolution=128, observation_ids=None):
    """Enumerate coarse cells, then prune/refine to a fixed final lattice.

    All outputs are numerical. Real-arithmetic enclosure is explained in docs;
    PAD_DEG is not a machine-checked floating-point error certificate.
    """
    start = time.perf_counter()
    if type(resolution) is not int or resolution < 8 or resolution > MAX_RESOLUTION or resolution & (resolution - 1):
        raise ValueError("resolution must be a power of two from 8 through 256")
    bounds, landmarks, observations = prepare(scene, observation_ids)
    xmin, ymin, xmax, ymax = bounds
    dx, dy = (xmax - xmin) / resolution, (ymax - ymin) / resolution
    cell_area = dx * dy
    conflict = _direct_conflict(observations)
    # Start with an 8x8 enumeration, then refine only retained cells.
    stride = resolution // 8
    stack = [] if conflict else [(i * stride, j * stride, stride) for j in range(8) for i in range(8)]
    leaves, tested = {}, 0
    while stack:
        ix, iy, step = stack.pop()
        cx, cy = xmin + (ix + step / 2) * dx, ymin + (iy + step / 2) * dy
        radius = math.hypot(dx * step, dy * step) / 2
        kind = _classify(cx, cy, radius, landmarks, observations)
        tested += 1
        if kind < 0:
            continue
        if step == 1:
            leaves[(ix, iy)] = kind
        else:
            half = step // 2
            stack.extend((ix + ox, iy + oy, half) for oy in (0, half) for ox in (0, half))
    unseen = set(leaves)
    labels, components = {}, []
    while unseen:
        first = min(unseen)
        unseen.remove(first)
        frontier, group = [first], []
        while frontier:
            p = frontier.pop()
            group.append(p)
            for ox, oy in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)):
                q = (p[0] + ox, p[1] + oy)
                if q in unseen:
                    unseen.remove(q)
                    frontier.append(q)
        cid = len(components)
        inner_count, witnesses, witness = 0, 0, None
        for ix, iy in group:
            labels[(ix, iy)] = cid
            inner_count += leaves[(ix, iy)]
            point = [xmin + (ix + .5) * dx, ymin + (iy + .5) * dy]
            if _accept(_point_values(point, landmarks), observations):
                witnesses += 1
                if witness is None:
                    witness = point
        components.append({"id": cid, "cell_count": len(group), "area_lower": inner_count * cell_area,
                           "area_upper": len(group) * cell_area, "witness_count": witnesses, "witness": witness})
    count = sum(c["witness_count"] for c in components)
    lower, upper = sum(leaves.values()) * cell_area, len(leaves) * cell_area
    return {"scene_id": scene.get("id"), "status": "incompatible" if not leaves else "feasible" if count else "unresolved",
            "grid": {"n": resolution, "bounds": bounds, "dx": dx, "dy": dy},
            "cells": [[ix, iy, leaves[(ix, iy)], labels[(ix, iy)]] for ix, iy in sorted(leaves)],
            "components": components, "area_lower": lower, "area_upper": upper,
            "area_uncertain": upper - lower, "cell_diagonal": math.hypot(dx, dy),
            "center_witness_count": count, "tested_cells": tested,
            "conflict_observations": conflict, "observation_ids": [o["id"] for o in observations],
            "runtime_ms": (time.perf_counter() - start) * 1000,
            "numerical_pad_deg": PAD_DEG, "method": "adaptive conservative cell cover; 8-neighbor cover components",
            "guarantee": "real-arithmetic enclosure argument; floating-point implementation empirically checked, not formally certified"}


def contains(result, point):
    """Membership in the closed outer cell cover, including domain/grid edges."""
    xmin, ymin, xmax, ymax = result["grid"]["bounds"]
    x, y = point
    if not (xmin <= x <= xmax and ymin <= y <= ymax):
        return False
    dx, dy = result["grid"]["dx"], result["grid"]["dy"]
    # At a shared edge either adjacent retained cell covers the point.
    fx, fy = (x - xmin) / dx, (y - ymin) / dy
    ix, iy = math.floor(fx), math.floor(fy)
    candidates_x = {ix, ix - 1} if abs(fx - ix) <= 1e-10 else {ix}
    candidates_y = {iy, iy - 1} if abs(fy - iy) <= 1e-10 else {iy}
    return any(c[0] in candidates_x and c[1] in candidates_y for c in result["cells"])
