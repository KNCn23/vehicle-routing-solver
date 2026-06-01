"""Data model for the vehicle routing problem.

A :class:`Problem` is a self-contained description of a routing instance:
where the stops are, how much each one demands, how many vehicles are
available and how much they can carry. Keeping the data separate from the
solver makes the instances easy to serialise to JSON and to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Location:
    """A single point that has to be visited (or the depot).

    Coordinates are generic numbers. They can be planar ``(x, y)`` values or
    ``(latitude, longitude)`` pairs - the distance builder you pick decides how
    they are interpreted.

    Attributes:
        name: Human readable label, shown in the printed solution.
        x: First coordinate (x or latitude).
        y: Second coordinate (y or longitude).
        demand: Units of goods this stop needs. The depot has demand 0.
        ready_time: Earliest time the stop may be served (time-window mode).
        due_time: Latest time the stop may be served (time-window mode).
        service_time: How long the vehicle stays at the stop.
    """

    name: str
    x: float
    y: float
    demand: int = 0
    ready_time: int = 0
    due_time: int = 0
    service_time: int = 0


@dataclass
class Vehicle:
    """A homogeneous fleet description.

    Attributes:
        count: How many identical vehicles are available.
        capacity: Maximum total demand a single vehicle can carry.
    """

    count: int
    capacity: int


@dataclass
class Problem:
    """A complete routing instance.

    Attributes:
        locations: All points. ``locations[depot]`` is the start/end point.
        vehicle: Fleet description.
        depot: Index into ``locations`` of the depot.
        name: Optional instance name.
    """

    locations: list[Location]
    vehicle: Vehicle
    depot: int = 0
    name: str = "unnamed"

    def __post_init__(self) -> None:
        if not self.locations:
            raise ValueError("a problem needs at least one location (the depot)")
        if not 0 <= self.depot < len(self.locations):
            raise ValueError(f"depot index {self.depot} is out of range")
        if self.vehicle.count < 1:
            raise ValueError("the fleet needs at least one vehicle")
        if self.vehicle.capacity < 1:
            raise ValueError("vehicle capacity must be positive")
        biggest = max(loc.demand for loc in self.locations)
        if biggest > self.vehicle.capacity:
            raise ValueError(
                f"stop demand {biggest} exceeds vehicle capacity "
                f"{self.vehicle.capacity}; the instance is infeasible"
            )

    @property
    def size(self) -> int:
        """Number of locations including the depot."""
        return len(self.locations)

    @property
    def total_demand(self) -> int:
        """Sum of demand across every customer stop."""
        return sum(loc.demand for loc in self.locations)

    @property
    def uses_time_windows(self) -> bool:
        """True when at least one stop defines a non-trivial time window."""
        return any(loc.due_time > 0 for loc in self.locations)
