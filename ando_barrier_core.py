"""Lightweight Python fallback for the Ando Barrier core module.

This project normally exposes a compiled extension that provides cloth
simulation primitives.  The heavy lifting is not required for the unit tests
that ship with this kata, but the tests do expect a module named
``ando_barrier_core`` with a subset of the API.  Without the compiled module
the test suite aborts during import which effectively hides the interesting
Python tests from running.

The goal of this module is not to be physically accurate – it only needs to
provide deterministic, well-behaved semantics for the pieces of the API the
tests exercise.  The implementation below keeps the surface compatible with
the original extension while implementing the behaviour purely in NumPy so
that the tests can execute without the native build.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Data structures


@dataclass
class Material:
    """Minimal material representation used by the tests."""

    youngs_modulus: float = 1.0e6
    poisson_ratio: float = 0.3
    density: float = 1000.0
    thickness: float = 0.001


@dataclass
class SimParams:
    """Lightweight simulation parameter container used by tests and tooling."""

    dt: float = 0.002
    beta_max: float = 0.25
    min_newton_steps: int = 2
    max_newton_steps: int = 8
    pcg_tol: float = 1e-3
    pcg_max_iters: int = 1000
    contact_gap_max: float = 1e-3
    wall_gap: float = 1e-3
    enable_ccd: bool = True
    enable_friction: bool = False
    friction_mu: float = 0.1
    friction_epsilon: float = 1e-5
    velocity_damping: float = 0.0
    contact_restitution: float = 0.0
    enable_strain_limiting: bool = False
    strain_limit: float = 0.05
    strain_tau: float = 0.05


class Mesh:
    """Simple triangle mesh wrapper."""

    def __init__(self) -> None:
        self.vertices: Optional[np.ndarray] = None
        self.triangles: Optional[np.ndarray] = None
        self.material: Optional[Material] = None

    def initialize(
        self,
        vertices: Sequence[Sequence[float]],
        triangles: Sequence[Sequence[int]] | np.ndarray,
        material: Material,
    ) -> None:
        self.vertices = np.asarray(vertices, dtype=np.float32)
        # ``triangles`` may be provided either as a flat list or an ``(n, 3)``
        # array – normalise to a 2D array with integer indices.
        tri_array = np.asarray(triangles, dtype=np.int32)
        self.triangles = tri_array.reshape((-1, 3))
        self.material = material

    # Convenience helpers mimicking the extension's API ------------------
    def num_vertices(self) -> int:
        return 0 if self.vertices is None else int(self.vertices.shape[0])

    def num_triangles(self) -> int:
        return 0 if self.triangles is None else int(self.triangles.shape[0])


class State:
    """Basic state container with explicit Euler integration."""

    def __init__(self) -> None:
        self._mesh: Optional[Mesh] = None
        self._positions: Optional[np.ndarray] = None
        self._velocities: Optional[np.ndarray] = None
        self._masses: Optional[np.ndarray] = None

    def initialize(self, mesh: Mesh) -> None:
        if mesh.vertices is None:
            raise ValueError("Mesh must be initialised before creating a state")

        self._mesh = mesh
        self._positions = mesh.vertices.copy()
        self._velocities = np.zeros_like(self._positions)

        # Assign a uniform mass per vertex.  Exact values are not crucial for
        # the tests; using the material density keeps things deterministic.
        material = mesh.material or Material()
        mass_per_vertex = material.density * material.thickness * 1e-4
        self._masses = np.full(mesh.vertices.shape[0], mass_per_vertex, dtype=np.float32)

    # Query helpers -------------------------------------------------------
    def num_vertices(self) -> int:
        return 0 if self._positions is None else int(self._positions.shape[0])

    def get_positions(self) -> np.ndarray:
        if self._positions is None:
            raise RuntimeError("State has not been initialised")
        return self._positions

    def get_velocities(self) -> np.ndarray:
        if self._velocities is None:
            raise RuntimeError("State has not been initialised")
        return self._velocities

    def get_masses(self) -> np.ndarray:
        if self._masses is None:
            raise RuntimeError("State has not been initialised")
        return self._masses

    # Integration ---------------------------------------------------------
    def apply_gravity(self, gravity: Iterable[float], dt: float) -> None:
        if self._positions is None or self._velocities is None:
            raise RuntimeError("State has not been initialised")

        g = np.asarray(gravity, dtype=np.float32)
        if g.shape != (3,):
            raise ValueError("Gravity must be a 3D vector")

        self._velocities += g * dt
        self._positions += self._velocities * dt


class Constraints:
    """Very small subset of the constraint API used in tests."""

    def __init__(self) -> None:
        self._pins: Dict[int, np.ndarray] = {}
        self._walls: List[Tuple[np.ndarray, float, float]] = []

    def add_pin(self, index: int, position: Sequence[float]) -> None:
        self._pins[index] = np.asarray(position, dtype=np.float32)

    def add_wall(self, normal: Sequence[float], offset: float, gap: float) -> None:
        self._walls.append((np.asarray(normal, dtype=np.float32), float(offset), float(gap)))

    def num_active_pins(self) -> int:
        return len(self._pins)

    def num_active_contacts(self) -> int:
        # Treat each wall as a potential contact surface.
        return len(self._walls)


# ---------------------------------------------------------------------------
# Adaptive timestep utilities


class AdaptiveTimestep:
    """Collection of helpers that emulate the C++ adaptive timestep API."""

    @staticmethod
    def compute_cfl_timestep(max_velocity: float, min_edge_length: float, safety: float) -> float:
        max_velocity = float(max_velocity)
        min_edge_length = float(min_edge_length)
        safety = float(safety)

        if min_edge_length <= 0.0:
            return 0.0

        if max_velocity <= 1e-8:
            # Cloth is effectively static – return a large, but finite value.
            return safety * min_edge_length / 1e-8

        return safety * min_edge_length / max_velocity

    @staticmethod
    def _iter_triangle_edges(mesh: Mesh) -> Iterable[Tuple[np.ndarray, np.ndarray]]:
        if mesh.vertices is None or mesh.triangles is None:
            return []

        verts = mesh.vertices
        for tri in mesh.triangles:
            v0, v1, v2 = tri
            yield verts[v0], verts[v1]
            yield verts[v1], verts[v2]
            yield verts[v2], verts[v0]

    @staticmethod
    def compute_min_edge_length(mesh: Mesh) -> float:
        min_length = np.inf
        for a, b in AdaptiveTimestep._iter_triangle_edges(mesh):
            length = float(np.linalg.norm(a - b))
            if length < min_length:
                min_length = length

        if not np.isfinite(min_length):
            return 0.0
        return min_length

    @staticmethod
    def compute_max_velocity(velocities: Sequence[float]) -> float:
        vel_array = np.asarray(velocities, dtype=np.float32)
        if vel_array.size == 0:
            return 0.0
        reshaped = vel_array.reshape((-1, 3))
        norms = np.linalg.norm(reshaped, axis=1)
        return float(np.max(norms)) if norms.size else 0.0

    @staticmethod
    def compute_next_dt(
        velocities: Sequence[float],
        mesh: Mesh,
        current_dt: float,
        dt_min: float,
        dt_max: float,
        safety: float,
    ) -> float:
        current_dt = float(current_dt)
        dt_min = float(dt_min)
        dt_max = float(dt_max)

        max_velocity = AdaptiveTimestep.compute_max_velocity(velocities)
        min_edge = AdaptiveTimestep.compute_min_edge_length(mesh)

        if max_velocity <= 1e-8:
            return dt_max
        else:
            target_dt = AdaptiveTimestep.compute_cfl_timestep(max_velocity, min_edge, safety)

        # Clamp to the provided limits.
        target_dt = float(np.clip(target_dt, dt_min, dt_max))

        if target_dt > current_dt:
            target_dt = min(target_dt, current_dt * 1.5)

        return max(dt_min, min(target_dt, dt_max))


__all__ = [
    "Material",
    "SimParams",
    "Mesh",
    "State",
    "Constraints",
    "AdaptiveTimestep",
]

