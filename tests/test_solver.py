"""Behavioural tests for the routing solver.

These exercise the full stack (model -> matrix -> OR-Tools) on tiny instances
whose answers we can reason about by hand.
"""

import pytest

from vrp.distance import euclidean_matrix
from vrp.io_utils import load_problem
from vrp.model import Location, Problem, Vehicle
from vrp.solver import solve


def _solve(problem, **kw):
    return solve(problem, euclidean_matrix(problem), time_limit_s=2, **kw)


def test_every_customer_visited_exactly_once():
    problem = Problem(
        locations=[
            Location("depot", 0, 0),
            Location("a", 1, 0, demand=1),
            Location("b", 2, 0, demand=1),
            Location("c", 0, 1, demand=1),
            Location("d", 0, 2, demand=1),
        ],
        vehicle=Vehicle(count=2, capacity=10),
    )
    sol = _solve(problem)
    assert sol.total_distance >= 0
    visited = []
    for route in sol.routes:
        # interior nodes only (strip leading/trailing depot)
        visited.extend(route.stops[1:-1])
    assert sorted(visited) == [1, 2, 3, 4]
    assert sol.dropped == []


def test_capacity_is_respected():
    # Four stops of demand 6 with capacity 10 force at least two vehicles,
    # because no two stops fit on one route.
    problem = Problem(
        locations=[
            Location("depot", 0, 0),
            Location("a", 1, 1, demand=6),
            Location("b", 2, 2, demand=6),
            Location("c", 3, 3, demand=6),
            Location("d", 4, 4, demand=6),
        ],
        vehicle=Vehicle(count=4, capacity=10),
    )
    sol = _solve(problem)
    assert sol.total_distance >= 0
    for route in sol.routes:
        assert route.load <= problem.vehicle.capacity


def test_infeasible_instance_without_dropping_returns_no_solution():
    # One vehicle, capacity 5, but total demand is 12 -> impossible.
    problem = Problem(
        locations=[
            Location("depot", 0, 0),
            Location("a", 1, 0, demand=4),
            Location("b", 2, 0, demand=4),
            Location("c", 3, 0, demand=4),
        ],
        vehicle=Vehicle(count=1, capacity=5),
    )
    sol = _solve(problem)
    assert sol.total_distance == -1


def test_dropping_recovers_a_partial_solution():
    problem = Problem(
        locations=[
            Location("depot", 0, 0),
            Location("a", 1, 0, demand=4),
            Location("b", 2, 0, demand=4),
            Location("c", 3, 0, demand=4),
        ],
        vehicle=Vehicle(count=1, capacity=5),
    )
    sol = _solve(problem, allow_dropping=True)
    assert sol.total_distance >= 0
    # Only one stop (demand 4) fits, so two must be dropped.
    assert len(sol.dropped) == 2


def test_bundled_small_instance_is_solvable():
    problem = load_problem("data/example_small.json")
    sol = _solve(problem)
    assert sol.total_distance > 0
    assert sol.dropped == []


def test_bundled_timewindow_instance_is_solvable():
    problem = load_problem("data/example_timewindows.json")
    assert problem.uses_time_windows
    sol = _solve(problem)
    assert sol.total_distance > 0


def test_demand_exceeding_capacity_is_rejected_early():
    with pytest.raises(ValueError):
        Problem(
            locations=[Location("depot", 0, 0), Location("big", 1, 1, demand=99)],
            vehicle=Vehicle(count=1, capacity=10),
        )
