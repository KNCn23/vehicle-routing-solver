"""Optional matplotlib visualisation of a solution.

Kept separate from the solver so the core has no hard dependency on
matplotlib - importing this module is only needed when you actually want a
picture.
"""

from __future__ import annotations

from pathlib import Path

from .model import Problem
from .solver import Solution


def plot_solution(
    problem: Problem,
    solution: Solution,
    out_path: str | Path = "routes.png",
    show: bool = False,
) -> Path:
    """Draw every used route and save it to ``out_path``.

    Each vehicle gets its own colour. The depot is drawn as a black square,
    customers as circles.
    """
    import matplotlib

    if not show:
        matplotlib.use("Agg")  # headless backend, no display needed
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 8))
    cmap = plt.get_cmap("tab10")

    # customers
    for i, loc in enumerate(problem.locations):
        if i == problem.depot:
            continue
        ax.scatter(loc.x, loc.y, c="#444", s=40, zorder=3)
        ax.annotate(loc.name, (loc.x, loc.y), textcoords="offset points",
                    xytext=(5, 5), fontsize=8)

    # depot
    depot = problem.locations[problem.depot]
    ax.scatter(depot.x, depot.y, c="black", marker="s", s=120, zorder=4,
               label="depot")

    # routes
    for route in solution.routes:
        if not route.is_used:
            continue
        xs = [problem.locations[s].x for s in route.stops]
        ys = [problem.locations[s].y for s in route.stops]
        ax.plot(xs, ys, "-o", color=cmap(route.vehicle % 10), linewidth=1.8,
                markersize=4, zorder=2, label=f"vehicle {route.vehicle}")

    ax.set_title(f"{problem.name} - {solution.used_vehicles} routes, "
                 f"dist {solution.total_distance / 1000:.2f}")
    ax.legend(loc="best", fontsize=8)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, linestyle=":", alpha=0.4)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return out
