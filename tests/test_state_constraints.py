"""Additional coverage for mesh, state, and constraint helpers.

These tests focus on the pure-Python fallback implementation that ships with
the kata.  They exercise the guard-rails around the light-weight simulation
objects so that future refactors cannot accidentally regress the semantics the
rest of the suite relies upon.
"""

from __future__ import annotations

import sys

import numpy as np
import pytest

sys.path.insert(0, "build")

import ando_barrier_core as abc  # type: ignore  # pylint: disable=import-error


def test_mesh_initialisation_and_counts() -> None:
    """Initialising a mesh normalises triangle data and exposes counts."""

    mesh = abc.Mesh()

    # Counts on an empty mesh default to zero so collection-time failures are
    # easier to debug.
    assert mesh.num_vertices() == 0
    assert mesh.num_triangles() == 0

    vertices = [
        [0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0],
        [0.0, 0.1, 0.0],
    ]

    # Provide triangles as a flat list – ``Mesh.initialize`` must reshape it
    # into the ``(n, 3)`` form expected by the rest of the API.
    triangles = [0, 1, 2]

    mesh.initialize(vertices, triangles, abc.Material())

    assert mesh.num_vertices() == 3
    assert mesh.num_triangles() == 1

    # ``Mesh.initialize`` should store triangles as a 2D array regardless of
    # the input container shape to keep downstream code simple.
    assert mesh.triangles is not None
    assert mesh.triangles.shape == (1, 3)


def test_state_requires_initialised_mesh() -> None:
    """Attempting to construct a state from an empty mesh should fail."""

    mesh = abc.Mesh()  # No vertices loaded.
    state = abc.State()

    with pytest.raises(ValueError):
        state.initialize(mesh)


def test_state_initialisation_copies_vertex_data() -> None:
    """Mutating the mesh after state creation must not affect state buffers."""

    material = abc.Material(density=2.0, thickness=0.5)
    vertices = np.array([[0.0, 0.0, 0.0], [0.2, 0.0, 0.0]], dtype=np.float32)
    triangles = [[0, 1, 1]]  # Degenerate but sufficient for the copy test.

    mesh = abc.Mesh()
    mesh.initialize(vertices, triangles, material)

    state = abc.State()
    state.initialize(mesh)

    # Masses derive from the material properties and should be uniform.
    masses = state.get_masses()
    assert np.allclose(masses, masses[0])

    # ``State.initialize`` copies vertex positions – mutating the mesh after
    # initialisation must not leak through to the state buffers.
    mesh.vertices[0, 0] = 42.0
    assert np.allclose(state.get_positions(), [[0.0, 0.0, 0.0], [0.2, 0.0, 0.0]])


def test_state_apply_gravity_updates_velocities() -> None:
    """Gravity integration updates both velocity and position arrays."""

    material = abc.Material()
    mesh = abc.Mesh()
    mesh.initialize([[0.0, 0.0, 0.0]], [0, 0, 0], material)

    state = abc.State()
    state.initialize(mesh)

    initial_positions = state.get_positions().copy()
    initial_velocities = state.get_velocities().copy()

    dt = 0.5
    gravity = (0.0, -9.81, 0.0)
    state.apply_gravity(gravity, dt)

    velocities = state.get_velocities()
    positions = state.get_positions()

    assert np.allclose(velocities, initial_velocities + np.array(gravity) * dt)
    assert np.allclose(positions, initial_positions + velocities * dt)


def test_state_apply_gravity_validation() -> None:
    """Gravity requires a three component vector and an initialised state."""

    state = abc.State()

    with pytest.raises(RuntimeError):
        state.apply_gravity((0.0, -9.81, 0.0), 0.1)

    material = abc.Material()
    mesh = abc.Mesh()
    mesh.initialize([[0.0, 0.0, 0.0]], [0, 0, 0], material)
    state.initialize(mesh)

    with pytest.raises(ValueError):
        state.apply_gravity((0.0, -9.81), 0.1)


def test_constraints_track_pins_and_walls() -> None:
    """Pins and walls accumulate counts that downstream code relies upon."""

    constraints = abc.Constraints()

    assert constraints.num_active_pins() == 0
    assert constraints.num_active_contacts() == 0

    constraints.add_pin(0, (0.0, 0.0, 0.0))
    constraints.add_pin(1, (1.0, 0.0, 0.0))
    assert constraints.num_active_pins() == 2
    assert np.allclose(constraints._pins[0], (0.0, 0.0, 0.0))  # noqa: SLF001

    constraints.add_wall((0.0, 1.0, 0.0), offset=0.1, gap=0.01)
    constraints.add_wall((0.0, 0.0, 1.0), offset=-0.2, gap=0.05)
    assert constraints.num_active_contacts() == 2
    assert constraints._walls[0][1:] == (0.1, 0.01)  # noqa: SLF001


def test_adaptive_timestep_handles_degenerate_inputs() -> None:
    """Degenerate meshes and velocities fall back to safe defaults."""

    mesh = abc.Mesh()
    mesh.vertices = np.zeros((0, 3), dtype=np.float32)
    mesh.triangles = np.zeros((0, 3), dtype=np.int32)

    # No valid edges, so the minimum length should be reported as zero.
    assert abc.AdaptiveTimestep.compute_min_edge_length(mesh) == 0.0

    # ``compute_cfl_timestep`` returns zero if the mesh is invalid regardless
    # of the other parameters.
    assert (
        abc.AdaptiveTimestep.compute_cfl_timestep(max_velocity=1.0, min_edge_length=0.0, safety=0.5)
        == 0.0
    )

    # Empty velocity buffers are tolerated and treated as stationary cloth.
    assert abc.AdaptiveTimestep.compute_max_velocity([]) == 0.0


def test_compute_next_dt_respects_bounds_when_increasing() -> None:
    """When velocities drop the timestep expands gradually and stays bounded."""

    material = abc.Material()
    mesh = abc.Mesh()
    mesh.initialize(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        [0, 1, 2],
        material,
    )

    slow_velocities = np.full(9, 1e-4, dtype=np.float32)
    current_dt = 0.02
    dt_min = 0.001
    dt_max = 0.05
    safety = 0.5

    # First expansion step should be capped at 1.5x the current dt.
    next_dt = abc.AdaptiveTimestep.compute_next_dt(
        slow_velocities, mesh, current_dt, dt_min, dt_max, safety
    )
    assert next_dt == pytest.approx(min(dt_max, current_dt * 1.5))

    # Feeding the relaxed dt back in should continue to honour the explicit
    # ``dt_max`` guard.
    second_dt = abc.AdaptiveTimestep.compute_next_dt(
        slow_velocities, mesh, next_dt, dt_min, dt_max, safety
    )
    assert dt_min <= second_dt <= dt_max
    assert second_dt == pytest.approx(min(dt_max, next_dt * 1.5))


def test_compute_next_dt_clamps_to_dt_min() -> None:
    """Extremely high velocities collapse the timestep to the minimum bound."""

    material = abc.Material()
    mesh = abc.Mesh()
    mesh.initialize(
        [
            [0.0, 0.0, 0.0],
            [0.01, 0.0, 0.0],
            [0.0, 0.01, 0.0],
        ],
        [0, 1, 2],
        material,
    )

    fast_velocities = np.full(9, 1e6, dtype=np.float32)

    dt_min = 1e-5
    dt_max = 1.0

    dt = abc.AdaptiveTimestep.compute_next_dt(
        fast_velocities, mesh, current_dt=0.1, dt_min=dt_min, dt_max=dt_max, safety=0.5
    )

    assert dt_min <= dt <= dt_max
    # The returned dt should be extremely close to the lower bound because the
    # velocity is orders of magnitude larger than the mesh can accommodate.
    assert dt <= dt_min * 1.01

