#!/usr/bin/env python3
"""Command-line entry point for the vehicle routing solver.

Examples
--------
Solve the bundled capacitated instance::

    python cli.py data/example_small.json

Solve a time-window instance and save a plot::

    python cli.py data/example_timewindows.json --plot routes.png

Use a geographic distance metric and let the solver drop infeasible stops::

    python cli.py my_cities.json --metric haversine --allow-dropping
"""

from __future__ import annotations

import argparse
import sys

from vrp.distance import euclidean_matrix, haversine_matrix
from vrp.io_utils import format_solution, load_problem
from vrp.solver import solve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("instance", help="path to a JSON problem file")
    parser.add_argument("--metric", choices=["euclidean", "haversine"],
                        default="euclidean",
                        help="how to interpret coordinates (default: euclidean)")
    parser.add_argument("--time-limit", type=int, default=10,
                        help="solver time budget in seconds (default: 10)")
    parser.add_argument("--allow-dropping", action="store_true",
                        help="permit skipping stops the fleet cannot serve")
    parser.add_argument("--plot", metavar="PNG",
                        help="render the routes to this image file")
    args = parser.parse_args(argv)

    problem = load_problem(args.instance)
    builder = haversine_matrix if args.metric == "haversine" else euclidean_matrix
    matrix = builder(problem)

    solution = solve(
        problem,
        matrix,
        time_limit_s=args.time_limit,
        allow_dropping=args.allow_dropping,
    )

    print(format_solution(problem, solution))

    if args.plot and solution.total_distance >= 0:
        from vrp.plot import plot_solution
        out = plot_solution(problem, solution, args.plot)
        print(f"\nPlot written to {out}")

    return 0 if solution.total_distance >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
