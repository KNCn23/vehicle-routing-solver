"""Load problems from JSON and pretty-print solutions.

The JSON schema is intentionally small. A minimal instance looks like::

    {
      "name": "demo",
      "depot": 0,
      "vehicle": {"count": 3, "capacity": 15},
      "locations": [
        {"name": "depot", "x": 0, "y": 0},
        {"name": "A", "x": 2, "y": 5, "demand": 4}
      ]
    }

Time-window instances add ``ready_time``, ``due_time`` and ``service_time`` to
the relevant stops.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import Location, Problem, Vehicle
from .solver import Solution


def load_problem(path: str | Path) -> Problem:
    """Read a problem instance from a JSON file."""
    raw = json.loads(Path(path).read_text())
    locations = [
        Location(
            name=str(item.get("name", f"stop{i}")),
            x=float(item["x"]),
            y=float(item["y"]),
            demand=int(item.get("demand", 0)),
            ready_time=int(item.get("ready_time", 0)),
            due_time=int(item.get("due_time", 0)),
            service_time=int(item.get("service_time", 0)),
        )
        for i, item in enumerate(raw["locations"])
    ]
    vehicle = Vehicle(
        count=int(raw["vehicle"]["count"]),
        capacity=int(raw["vehicle"]["capacity"]),
    )
    return Problem(
        locations=locations,
        vehicle=vehicle,
        depot=int(raw.get("depot", 0)),
        name=str(raw.get("name", Path(path).stem)),
    )


def format_solution(problem: Problem, solution: Solution, scale: int = 1000) -> str:
    """Render a solution as a human-readable, multi-line string."""
    if solution.total_distance < 0:
        return (
            "No feasible solution found.\n"
            "Try adding vehicles, raising capacity, or pass --allow-dropping."
        )

    lines: list[str] = []
    lines.append(f"Instance : {problem.name}")
    lines.append(f"Stops    : {problem.size - 1} customers + 1 depot")
    lines.append(f"Fleet    : {problem.vehicle.count} x cap {problem.vehicle.capacity}")
    lines.append("-" * 56)

    for route in solution.routes:
        if not route.is_used:
            continue
        path = " -> ".join(problem.locations[s].name for s in route.stops)
        km = route.distance / scale
        lines.append(
            f"Vehicle {route.vehicle}: load {route.load}/{problem.vehicle.capacity}"
            f"  dist {km:.2f}"
        )
        lines.append(f"    {path}")

    lines.append("-" * 56)
    lines.append(f"Vehicles used : {solution.used_vehicles}/{problem.vehicle.count}")
    lines.append(f"Total distance: {solution.total_distance / scale:.2f}")
    if solution.dropped:
        names = ", ".join(problem.locations[d].name for d in solution.dropped)
        lines.append(f"Dropped stops : {names}")
    return "\n".join(lines)
