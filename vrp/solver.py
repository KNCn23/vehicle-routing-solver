"""The OR-Tools routing layer.

This module turns a :class:`~vrp.model.Problem` plus a distance matrix into an
optimised set of vehicle routes. It supports two classic variants:

* **CVRP** - capacitated VRP: every stop has a demand and vehicles have a
  fixed capacity.
* **VRPTW** - CVRP with time windows: every stop additionally has an interval
  ``[ready_time, due_time]`` during which service must start.

The heavy lifting is done by OR-Tools' constraint-programming routing solver;
our job is to register the cost/dimension callbacks and translate the result
back into plain Python objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .distance import SCALE
from .model import Problem


@dataclass
class Route:
    """One vehicle's tour.

    Attributes:
        vehicle: Index of the vehicle (0-based).
        stops: Ordered list of location indices, starting and ending at depot.
        load: Total demand carried on this route.
        distance: Travelled distance in the matrix' own (scaled) units.
    """

    vehicle: int
    stops: list[int]
    load: int
    distance: int

    @property
    def is_used(self) -> bool:
        """A route is "used" when it visits at least one customer."""
        return len(self.stops) > 2


@dataclass
class Solution:
    """The full result returned by :func:`solve`.

    Attributes:
        routes: One :class:`Route` per vehicle (unused ones are kept too).
        total_distance: Sum of every route distance, scaled units.
        dropped: Stops that could not be served (only possible when
            ``allow_dropping`` is enabled).
    """

    routes: list[Route]
    total_distance: int
    dropped: list[int]

    @property
    def used_vehicles(self) -> int:
        return sum(1 for r in self.routes if r.is_used)


def solve(
    problem: Problem,
    matrix: list[list[int]],
    *,
    time_limit_s: int = 10,
    allow_dropping: bool = False,
    drop_penalty: int = 1_000_000,
    first_solution: str = "PATH_CHEAPEST_ARC",
    metaheuristic: str = "GUIDED_LOCAL_SEARCH",
) -> Solution:
    """Solve a routing instance.

    Args:
        problem: The instance to solve.
        matrix: Square integer distance matrix (see :mod:`vrp.distance`).
        time_limit_s: Wall-clock budget for the local-search phase.
        allow_dropping: If True, the solver may skip stops it cannot fit,
            paying ``drop_penalty`` each. Guarantees a solution even when the
            fleet is too small; if False an over-subscribed instance returns no
            solution instead.
        drop_penalty: Cost charged for each dropped stop.
        first_solution: Name of an OR-Tools first-solution strategy.
        metaheuristic: Name of an OR-Tools local-search metaheuristic.

    Returns:
        A :class:`Solution`. ``total_distance`` is -1 when the solver proved no
        feasible routing exists.
    """
    n = problem.size
    manager = pywrapcp.RoutingIndexManager(n, problem.vehicle.count, problem.depot)
    routing = pywrapcp.RoutingModel(manager)

    # --- arc cost: distance between two nodes -----------------------------
    def distance_cb(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return matrix[i][j]

    transit_idx = routing.RegisterTransitCallback(distance_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    # --- capacity dimension ----------------------------------------------
    def demand_cb(from_index: int) -> int:
        node = manager.IndexToNode(from_index)
        return problem.locations[node].demand

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx,
        0,  # no slack
        [problem.vehicle.capacity] * problem.vehicle.count,
        True,  # start cumul at zero
        "Capacity",
    )

    # --- optional time-window dimension ----------------------------------
    if problem.uses_time_windows:
        _add_time_windows(problem, matrix, manager, routing)

    # --- optionally let the solver drop unservable stops -----------------
    if allow_dropping:
        for node in range(n):
            if node == problem.depot:
                continue
            routing.AddDisjunction([manager.NodeToIndex(node)], drop_penalty)

    # --- search parameters ------------------------------------------------
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = getattr(
        routing_enums_pb2.FirstSolutionStrategy, first_solution
    )
    params.local_search_metaheuristic = getattr(
        routing_enums_pb2.LocalSearchMetaheuristic, metaheuristic
    )
    params.time_limit.FromSeconds(time_limit_s)

    assignment = routing.SolveWithParameters(params)
    if assignment is None:
        return Solution(routes=[], total_distance=-1, dropped=[])

    return _extract(problem, manager, routing, assignment)


def _add_time_windows(problem, matrix, manager, routing) -> None:
    """Register the "Time" dimension and constrain each node's window."""
    horizon = max(loc.due_time for loc in problem.locations) or 1_000_000

    def time_cb(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        # The distance matrix is scaled (see vrp.distance.SCALE) for arc-cost
        # precision. Time windows, however, are plain integers in the same
        # unit as travel time, so we un-scale here. This solver assumes one
        # distance unit equals one time unit (i.e. unit speed); adjust the
        # divisor if your fleet travels faster or slower.
        travel = round(matrix[i][j] / SCALE)
        return travel + problem.locations[i].service_time

    time_idx = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(
        time_idx,
        horizon,  # allow waiting (slack) up to the horizon
        horizon,
        False,  # do not force start cumul to zero (vehicles may start late)
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    for node, loc in enumerate(problem.locations):
        if node == problem.depot:
            continue
        index = manager.NodeToIndex(node)
        time_dim.CumulVar(index).SetRange(loc.ready_time, loc.due_time)

    # Each vehicle may leave the depot any time within the global horizon.
    for v in range(problem.vehicle.count):
        start = routing.Start(v)
        time_dim.CumulVar(start).SetRange(0, horizon)
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(start))
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.End(v)))


def _extract(problem, manager, routing, assignment) -> Solution:
    """Walk the assignment and build plain Python result objects."""
    routes: list[Route] = []
    total = 0
    for v in range(problem.vehicle.count):
        index = routing.Start(v)
        stops = [manager.IndexToNode(index)]
        load = 0
        dist = 0
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            load += problem.locations[node].demand
            nxt = assignment.Value(routing.NextVar(index))
            dist += routing.GetArcCostForVehicle(index, nxt, v)
            index = nxt
            stops.append(manager.IndexToNode(index))
        routes.append(Route(vehicle=v, stops=stops, load=load, distance=dist))
        total += dist

    dropped: list[int] = []
    for node in range(problem.size):
        idx = manager.NodeToIndex(node)
        if routing.IsStart(idx) or routing.IsEnd(idx):
            continue
        if assignment.Value(routing.NextVar(idx)) == idx:
            dropped.append(node)

    return Solution(routes=routes, total_distance=total, dropped=dropped)
