"""Python fallback implementation for the :mod:`ando_barrier_core` module.

This file contains the complete pure-Python implementation that mirrors the
public API of the native extension.  It is shared by the unit tests that live
in this repository and by the Blender add-on when the compiled module is not
available (e.g. due to a Python version mismatch).

The implementation used to live in the repository root as
``ando_barrier_core.py``.  That made it accessible to the tests, but Blender
users who copied only the ``blender_addon`` directory would miss the fallback
and see "Core module not loaded" errors.  Keeping the source here allows the
add-on to bundle the fallback directly while the tests import it dynamically.
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

    def resolve(self, state: State, compliance: float) -> None:
        del compliance  # Not used in fallback; keeps signature compatible.
        if state._positions is None:  # pylint: disable=protected-access
            raise RuntimeError("State must be initialised before resolving constraints")

        # Pin constraints simply overwrite positions.
        for index, target in self._pins.items():
            state._positions[index] = target  # pylint: disable=protected-access

        # Wall constraints perform a naive projection along the normal if the
        # vertex penetrates the wall plane.  This is not a physically accurate
        # model but suffices for deterministic unit tests.
        positions = state._positions  # pylint: disable=protected-access
        for normal, offset, gap in self._walls:
            distances = positions @ normal - offset
            mask = distances < -gap
            positions[mask] -= np.outer(distances[mask] + gap, normal)


# Public API helpers ---------------------------------------------------------


def version() -> str:
    return "ando_barrier_core (python fallback)"


def create_material(**kwargs) -> Material:
    material = Material()
    for key, value in kwargs.items():
        if not hasattr(material, key):
            raise AttributeError(f"Unknown material property: {key}")
        setattr(material, key, value)
    return material


def create_mesh() -> Mesh:
    return Mesh()


def create_state() -> State:
    return State()


def create_constraints() -> Constraints:
    return Constraints()


def apply_gravity(state: State, gravity: Iterable[float], dt: float) -> None:
    state.apply_gravity(gravity, dt)


def resolve_constraints(state: State, constraints: Constraints, compliance: float) -> None:
    constraints.resolve(state, compliance)


__all__ = [
    "Material",
    "SimParams",
    "Mesh",
    "State",
    "Constraints",
    "version",
    "create_material",
    "create_mesh",
    "create_state",
    "create_constraints",
    "apply_gravity",
    "resolve_constraints",
]

