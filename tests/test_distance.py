"""Unit tests for the distance-matrix builders."""

import math

from vrp.distance import euclidean_matrix, haversine_matrix
from vrp.model import Location, Problem, Vehicle


def _problem(locs):
    return Problem(locations=locs, vehicle=Vehicle(count=1, capacity=100))


def test_euclidean_is_symmetric_with_zero_diagonal():
    p = _problem([
        Location("a", 0, 0),
        Location("b", 3, 4),
        Location("c", 6, 8),
    ])
    m = euclidean_matrix(p)
    for i in range(p.size):
        assert m[i][i] == 0
        for j in range(p.size):
            assert m[i][j] == m[j][i]


def test_euclidean_known_distance():
    # 3-4-5 triangle, scaled by the default factor of 1000.
    p = _problem([Location("a", 0, 0), Location("b", 3, 4)])
    m = euclidean_matrix(p)
    assert m[0][1] == 5000


def test_haversine_known_distance():
    # Istanbul -> Ankara is roughly 350 km in a straight line.
    p = _problem([
        Location("istanbul", 41.0082, 28.9784),
        Location("ankara", 39.9334, 32.8597),
    ])
    m = haversine_matrix(p)
    km = m[0][1] / 1000
    assert 330 < km < 365


def test_haversine_symmetric():
    p = _problem([
        Location("x", 10.0, 20.0),
        Location("y", -5.0, 40.0),
        Location("z", 0.0, 0.0),
    ])
    m = haversine_matrix(p)
    for i in range(p.size):
        for j in range(p.size):
            assert m[i][j] == m[j][i]
