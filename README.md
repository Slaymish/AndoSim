# BlenderSim: Ando Barrier Physics

Blender add-on implementing "A Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness" (Ando 2024) for cloth/shell physics simulation.

## Quick Start

**For Blender Users:**
- See [BLENDER_GUIDE.md](BLENDER_GUIDE.md) for installation, usage, and tutorials

**For Developers:**
- Build: `./build.sh` (requires CMake, Eigen3, pybind11)
- Test: `./build.sh -t` (runs C++ unit tests)
- Demos: `./build/demos/demo_cloth_drape` (standalone C++ demos)
- Visualize: `python3 demos/view_sequence.py output/cloth_drape`

**Project Status:**
- Core physics engine: ✓ Complete (Tasks 0-9)
- Standalone demos: ✓ Working (90-170 FPS for 200-400 vertex meshes)
- Blender integration: ✓ Mostly Complete (baking functional, overlays pending)
- See [PROJECT_STATUS.md](PROJECT_STATUS.md) and [ROADMAP.md](ROADMAP.md) for details

---

## Phase 1 AI Agent Specification

### Goal Phase 1 AI Agent Specification: Blender Add-on implementing “A Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness” (Ando 2024)

Goal
- Build a Blender add-on (prototype CPU implementation) that reproduces the paper’s core method for cloth/shells (and optionally rods) with:
  - Cubic barrier for inequality constraints (contacts, pins, strain limiting) with semi-implicit dynamic stiffness.
  - Elasticity-inclusive stiffness design k ≈ m/Δt² + n·(H n), with m/ĝ² dominance near tiny gaps.
  - Inexact Newton integrator with β accumulation, extended direction line search, and final error-reduction pass.
  - Explicit sparse matrix assembly with cached indices (CAMA-like), block-Jacobi PCG.
  - Constraint-only line search (CCD-backed feasibility).
  - Minimal working demos: cloth vs. wall/ground contact; pins; strain limiting; visualization of diagnostics.

Constraints and priorities
- Absolute top priority: method consistency with the paper in energies, stiffness definitions, integrator, line search behavior, matrix structure, and numerical safeguards.
- CPU-first (C++ with Eigen). Python only for Blender UI and orchestration via pybind11.
- Single precision allowed for most core operations; host-side scalars (e.g., PCG alphas/betas) can use double.
- Scope: shells/cloth; optional rods if time allows. No volumetric tets in Phase 1.
- Export helpers, visualization overlays, and validation checks.

Deliverables
- A Blender add-on (Python) that exposes settings and runs/bakes the sim.
- A compiled C++ core module (Eigen + pybind11) that performs the solver loop.
- At least two demo .blend scenes and prebaked caches:
  1) Sheet draping onto a sphere/ground with contact and pins (no strain limiting).
  2) Strain-limited sheet (5%) showing wrinkle formation and locking-free behavior.
- Documentation: README with build steps, parameter mapping, validation notes aligned with the paper.

Agent Operating Model
- The agent executes a sequenced task list. Each task includes:
  - Objective
  - Inputs and dependencies
  - Required outputs and acceptance tests
  - Technical notes and references to specific equations/sections of the paper
  - Consistency checks versus the paper

Task List

Task 0: Repository and Build Scaffolding
- Objective: Set up repo, build, and CI scaffolding for Blender add-on + C++ core integration via pybind11.
- Inputs: Blender 3.6+ (LTS or current), CMake, Eigen, pybind11, Python 3.10+, OS toolchain.
- Outputs:
  - cmake/ toolchain; src/core (C++), src/py (bindings), blender_addon/ (Python).
  - Build script to produce a Python extension (e.g., ando_barrier_core.*.so/pyd).
  - README with platform-specific build instructions.
- Acceptance tests:
  - Import test in Python console inside Blender: from ando_barrier_core import api; api.version() returns a string.
- Notes:
  - Use -O3, enable fast-math optionally guarded by a flag.
  - Prepare a toggle for float/double build; default float for core, double for selected host scalars.

Task 1: Data Marshaling and State Layout
- Objective: Define clean data structures for shell meshes and physics state compatible with the paper.
- Inputs: Active Blender mesh object(s) and scene settings.
- Outputs:
  - C++ structs:
    - Mesh: vertices (x: N×3), triangles (M×3), rest-state per-face gradients (Dm_inv), per-edge bending topology.
    - State: positions x, velocities v, masses m, material params (E, ν, density ρ), shell thickness h (if used in bending).
    - Constraints: pins (vertex indices + targets), walls (plane n, offset, wall gap g_wall).
  - Python marshaling functions to build these buffers from bpy.
- Acceptance tests:
  - Round-trip a simple plane mesh; counts match; rest data computed.
- Notes:
  - Lumped masses per vertex by distributing face mass (area × thickness × ρ) equally to incident vertices.
  - Support per-object overrides for materials.

Task 2: Elasticity Model (Shells)
- Objective: Implement shell elasticity (choose ARAP or Baraff–Witkin FE consistent with the paper’s options).
- Inputs: Mesh, rest-state per-face matrices, materials.
- Outputs:
  - Functions: compute_elastic_energy(x), gradient g_el, Hessian H_el (explicit assembled blocks), PSD enforced by symmetrization and eigenvalue clamping to small +ε.
- Acceptance tests:
  - Unit tests on small meshes: positive energy, gradient ~0 at rest; H_el SPD; simple pull test produces reasonable deformation.
- Notes:
  - Reference: Section 4 (used ARAP/Wikin-Baraff for shells).
  - Use explicit assembly (not matrix-free) to match caching strategy later.

Task 3: Cubic Barrier Energy (Weak) with Semi-Implicit k
- Objective: Implement the weak cubic barrier V_weak(g, ḡ, k̄) as defined in the paper and its first/second derivatives w.r.t x, treating k̄ as constant during differentiation.
- Inputs: Gap function g(x) and max gap ḡ per constraint; stiffness k̄ computed separately.
- Outputs:
  - Energy, force, and Hessian assembly routines for:
    - Contacts (point-triangle, edge-edge, cloth vs. wall plane)
    - Pin constraints (as in Eq. 6 variant)
  - Unit tests: smooth C2 behavior at g=ḡ; zero outside barrier.
- Acceptance tests:
  - Compare numeric and analytic gradients/Hessians on random configurations (finite differences).
- Notes:
  - Equation: V_weak(g, ḡ, k) = −(k/2)(g−ḡ)² ln(g/ḡ) for g ≤ ḡ, else 0.
  - Semi-implicit stiffness: no chain rule on k̄. This is a critical consistency requirement.

Task 4: Dynamic Elasticity-Inclusive Stiffness (k) per constraint
- Objective: Implement stiffness selection per the paper’s design rule: k = m/Δt² + n·(H n), with m/ĝ² takeover as gaps shrink.
- Inputs: Per-constraint mass m (vertex/avg mass), Δt, contact direction, global elasticity Hessian H (or relevant blocks).
- Outputs:
  - For contacts (Eq. 5): compute extended direction w = Wᵀ(p−q), normalize to get n, then n·(H n). Add m/ĝ² near tiny gaps to bound stiffness (follow Section 3.3/3.4).
  - For pins (Eq. 6): use w_i = x_i − P_fixed, H_i 3×3 block.
  - For walls (Eq. 7): k_wall = m_i/(g_wall)² + n_wall · (H_i n_wall).
- Acceptance tests:
  - Numerical sanity: k increases as gap shrinks; adding elasticity raises k consistent with stiffer materials.
- Notes:
  - Symmetrize H; ensure PSD locally.
  - Cache H_n projections to avoid recomputing heavy ops within a step.
  - Treat k̄ as frozen for derivative evals (semi-implicit).

Task 5: Strain Limiting (Face singular values)
- Objective: Implement per-face strain limiting using σ1, σ2 with cubic barrier and k_SL as defined in Eq. (8–9).
- Inputs: Per-face deformation gradient F(x), singular values, small τ and ε (use τ=ε default), face mass m_face.
- Outputs:
  - Energy: Ψ_SL(σ1,σ2) = Ψ_weak(1+τ+ε−σ, ε, k_SL) applied to each σ.
  - Stiffness: k_SL = m_face/(1+τ+ε−max(σ1,σ2))² + w_r · (H_r x_r w_r).
  - Derivatives: explicit eigensystem for SVD to avoid degeneracy at σ1=σ2 (as in paper supplementary).
- Acceptance tests:
  - Stretch test: cap elongation near specified %; smooth forces; no jitter at g=ḡ.
- Notes:
  - Normalize/scaling: follow paper’s choice with w_r scaling so units align; DO NOT deviate.
  - Implement later if time is tight; ensure hooks in solver to toggle it.

Task 6: Collision Detection and Gaps
- Objective: Implement broad/narrow-phase for cloth collisions and compute gap g, witness points, and fixed contact normals.
- Inputs: Mesh(es), BVH for triangles and edges; previous-step caches for pairs.
- Outputs:
  - Broad-phase pair candidates; reuse last-step pairs for cache warm start.
  - Narrow-phase: point-triangle and edge-edge distances, witness points p, q, normals (fixed during evaluation).
  - Wall plane collisions.
- Acceptance tests:
  - Known test cases: plane sheet dropping onto plane/sphere; stable, no pass-through with line search active.
- Notes:
  - Use fixed contact normals (as per paper) to keep Hessians simpler; feasibility guaranteed via line search/CCD.
  - Implement discrete intersection check at end-of-step for validation (edge-triangle test).

Task 7: Constraint-only Line Search with Extended Direction
- Objective: Implement line search toward x + 1.25 d (extended) and return feasible α ∈ [0,1] considering only constraints.
- Inputs: Current x, search direction d, constraints (contacts, pins, strain limiting).
- Outputs:
  - Max α ensuring g ≥ 0 (or within barrier domain constraints); CCD or conservative stepping to avoid pass-through.
- Acceptance tests:
  - For a simple penetration scenario, α reduces to avoid constraint violation; no oscillatory instability.
- Notes:
  - This matches Algorithm 1, Line 13. Use constraints-only feasibility checks (performance and stability per paper).

Task 8: Inexact Newton Integrator with β Accumulation and Error Reduction
- Objective: Implement Algorithm 1 faithfully.
- Inputs: Δt, β_max (default 0.25), min/max Newton steps, stopping criteria.
- Outputs:
  - Loop: while β < β_max: inner_step(Δt, x) → (x, α); β ← β + (1−β) α
  - Error reduction: one additional inner_step(βΔt, x)
  - Velocities: update from Δx / (βΔt)
- Acceptance tests:
  - Reproduce “dragging artifacts” difference when β=1 vs using β accumulation (qualitative check).
- Notes:
  - PCG: 3×3 block Jacobi preconditioner; relative residual L∞ ≤ 1e−3 by default.
  - Enforce SPD for H; if needed, add small diagonal regularization εI.

Task 9: Matrix Assembly with Caching (CAMA-like)
- Objective: Implement explicit assembly with cached indices to reduce fill-in overhead for contact matrices.
- Inputs: Mesh connectivity, previous frame contact pairs and index mappings.
- Outputs:
  - Three-tier matrix cache: 3×3 block diagonal; fixed connectivity (topology-based blocks); dynamic contact blocks.
  - Atomic merges into cached entries during assembly.
- Acceptance tests:
  - Measure assembly time with/without cache on synthetic high-contact scenes; expect >3× improvement even on CPU.
- Notes:
  - Even though GPU cache benefits are larger, CPU version should still benefit and aligns with paper’s design.

Task 10: Friction (Prototype, optional for Phase 1)
- Objective: Implement the quadratic potential-based friction as per Eqs. (10–11) with μ f_contact and ε.
- Inputs: Contact set, previous positions x_prev, μ, ε=1e−5 m default.
- Outputs:
  - Additional energy/force/Hessian contributions; update k_friction after contact forces; optional Hessian cap to max eigenvalue of barrier.
- Acceptance tests:
  - Simple block-on-incline test at 30°: slides if μ<0.5, stays if μ>0.5 with sufficient Newton steps.
- Notes:
  - For Phase 1, keep friction off by default or require higher Newton iterations; otherwise, treat μ as heuristic.

Task 11: Blender Add-on UI and Orchestration
- Objective: Provide UI panels and operators to run/bake the solver and visualize diagnostics.
- Inputs: bpy API, compiled core module.
- Outputs:
  - Scene panel “Ando Barrier Physics”:
    - Δt (ms), β_max, min/max Newton steps, PCG tol/iters, precision toggles.
    - Contact: ḡ (default small mm), offset thickness, enable CCD for line search, friction μ, ε.
    - Strain limiting enable + limit %, τ=ε value.
    - Materials per object: E, ν, ρ; shell thickness; bending stiffness.
    - Pins/walls configuration.
    - Caching toggles and diagnostics.
  - Operators:
    - Bake simulation to frame range (writes per-frame mesh cache).
    - Visualize overlays: per-vertex min gap, per-face σ_max, contact counts; print α, β per step in console/log.
- Acceptance tests:
  - Run a bake on a plane falling onto a plane; observe stable contacts and timings; export animated cache.

Task 12: Demo Scenes and Validation
- Objective: Create minimal scenes to validate core behavior and consistency with the paper.
- Inputs: Blender assets (plane, sphere, pins, ground plane).
- Outputs:
  - Scene A: Sheet drape onto sphere/ground; 1–2 ms Δt, contacts on, no strain limiting; pins at top edge; β_max=0.25; 2–8 Newton steps.
  - Scene B: Strain limited sheet (5%); drop and settle; show locking-free wrinkles vs disabled SL reference.
  - Diagnostic plots/printouts: contact counts per frame, average time per step, α/β logs.
- Acceptance tests:
  - No penetrations (validated post-step by discrete intersection tests).
  - Smooth behavior near g≈ḡ due to C2 cubic barrier (no jitter).
  - Strain bounded near specified % with reasonable wrinkles.

Task 13: Documentation and Paper Consistency Checklist
- Objective: Provide explicit mapping of implementation to paper sections/equations and list of design decisions to ensure fidelity.
- Inputs: Paper PDF.
- Outputs:
  - README sections:
    - Energies implemented: V_weak eq, domains, smoothness.
    - Stiffness rules: contact (Eq. 5), pins (Eq. 6), walls (Eq. 7), strain limiting (Eq. 8–9).
    - Integrator: Algorithm 1 with β accumulation, extended direction LS, error reduction pass.
    - Assembly: explicit + caches.
    - Numerical choices: SPD enforcement, single/double precision split, PCG settings.
    - Limitations vs paper: GPU acceleration not in Phase 1; friction accuracy limited unless many Newton steps.
  - Paper consistency checklist items auto-verified or manually reviewed.

Strict Consistency Rules the Agent Must Enforce
- Do not introduce tuning constants not present in the paper (no magic 1e-9, 1e-11, 100 bounds, etc.). Use the stiffness design principle instead.
- Semi-implicit treatment of k̄: when differentiating energy, treat k̄ as constant, i.e., no chain rule through k̄.
- Use fixed contact normals in gap differential evaluation (as per paper); rely on line search/CCD for feasibility.
- Implement extended direction (1.25 d) and constraint-only line search.
- Implement β accumulation and a final error-reduction pass with βΔt.
- Enforce SPD on elasticity Hessians (symmetrize, clamp negatives).
- Default Δt in the 1–10 ms range; β_max=0.25; PCG tol L∞≈1e−3; block-Jacobi preconditioner.

Validation and KPIs
- Penetration-free results in demo scenes (discrete edge-triangle check per frame).
- Gap histogram shows most contacts with g/ḡ > 1/2 in non-SL scenes, consistent with paper observations.
- Visual absence of jitter at barrier boundary (C2).
- Time per frame and PCG iterations logged; assembly time reduced by caching on repeat frames.
- Strain limiting caps elongation to target within tolerance; wrinkles look natural vs high-Young’s-modulus-only.

Out-of-Scope for Phase 1
- GPU (CUDA) implementation, device-side PCG.
- Full friction validation scenes (domino/cards/belts) with 32 Newton steps; may be included later.
- Volumetric tetrahedra soft bodies.
- MAS or advanced preconditioners for extreme stiffness/mass ratios.

Appendix: Parameter Defaults (Phase 1)
- Δt: 2 ms (UI range: 1–10 ms)
- β_max: 0.25
- Newton steps: min 2, max 8
- PCG: rel L∞ tol 1e−3, max 1000 iters, 3×3 block-Jacobi
- Contact ḡ: 0.5–1.0 mm (scene scale dependent; expose in UI)
- Friction: disabled by default; ε = 0.01 mm if enabled; μ=0.1–0.5 for tests
- Strain limiting: disabled by default; if enabled, limit=5%, τ=ε such that τ+ε = limit