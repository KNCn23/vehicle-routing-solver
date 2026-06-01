"""Distance-matrix builders.

OR-Tools works with integer arc costs, so every builder returns a square
matrix of **integers**. We therefore scale the raw floating point distance by
a fixed factor before rounding, which keeps sub-unit precision (e.g. metres
when the haversine result is in kilometres).
"""

from __future__ import annotations

import math

from .model import Problem

# Multiplying by this factor before rounding keeps three decimal digits of the
# original distance once we cast to int.
SCALE = 1000


def euclidean_matrix(problem: Problem, scale: int = SCALE) -> list[list[int]]:
    """Straight-line distance on a flat plane.

    Use this when coordinates are arbitrary ``(x, y)`` points such as warehouse
    grid positions or a synthetic benchmark.
    """
    locs = problem.locations
    n = len(locs)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            dx = locs[i].x - locs[j].x
            dy = locs[i].y - locs[j].y
            matrix[i][j] = round(math.hypot(dx, dy) * scale)
    return matrix


def haversine_matrix(problem: Problem, scale: int = SCALE) -> list[list[int]]:
    """Great-circle distance in metres for ``(latitude, longitude)`` points.

    Use this for real-world maps. ``x`` is treated as latitude and ``y`` as
    longitude, both in decimal degrees.
    """
    earth_radius_m = 6_371_000.0
    locs = problem.locations
    n = len(locs)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        lat1 = math.radians(locs[i].x)
        lon1 = math.radians(locs[i].y)
        for j in range(n):
            if i == j:
                continue
            lat2 = math.radians(locs[j].x)
            lon2 = math.radians(locs[j].y)
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
            )
            c = 2 * math.asin(min(1.0, math.sqrt(a)))
            metres = earth_radius_m * c
            # scale is interpreted relative to metres here; default keeps
            # millimetre resolution which is plenty for routing.
            matrix[i][j] = round(metres * scale / SCALE)
    return matrix
