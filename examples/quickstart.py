#!/usr/bin/env python3
"""A 30-line tour of the library API.

Run it from the project root with::

    python examples/quickstart.py
"""

import sys
from pathlib import Path

# Make the project root importable no matter where this script is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vrp import Location, Problem, Vehicle, euclidean_matrix, solve
from vrp.io_utils import format_solution

# 1. Describe the problem in code (you can also load it from JSON).
problem = Problem(
    name="quickstart",
    locations=[
        Location("depot", 0, 0),
        Location("bakery", 2, 4, demand=3),
        Location("cafe", 5, 1, demand=5),
        Location("hotel", -3, 2, demand=4),
        Location("school", 1, -4, demand=6),
        Location("hospital", 4, 4, demand=2),
    ],
    vehicle=Vehicle(count=2, capacity=12),
)

# 2. Build a distance matrix (Euclidean here, haversine for lat/lon data).
matrix = euclidean_matrix(problem)

# 3. Solve and print.
solution = solve(problem, matrix, time_limit_s=3)
print(format_solution(problem, solution))
