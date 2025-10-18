# AndoSim Blender Add-on Milestones

This document outlines the key milestones for turning the AndoSim physics engine into a fully-featured Blender add-on that is compelling for artists, researchers, and technical users.

---

## Phase 1: Core Integration
**Goal:** Connect the existing AndoSim physics engine to Blender, creating a working, minimal add-on.

- [x] Create Python bindings for the AndoSim solver.  
  _Status:_ `ando_barrier_core` module builds and ships with the add-on.
- [x] Implement basic scene import/export:
  - [x] Convert Blender meshes to AndoSim colliders.
  - [x] Map Blender transforms to physics simulation state (object → state init).
- [~] Expose core physics parameters in Blender:
  - [x] Time stepping & solver controls (dt, β, Newton/PCG).
  - [x] Material properties (E, ν, density, thickness).
  - [ ] Damping & restitution presets (pending material system).
- [x] Enable single-frame simulation preview in the viewport (Step operator + realtime modal).
- [~] Ensure correct unit scaling and axis alignment with Blender.
  - Z-up alignment handled; scaling audit still queued for validation pass.

---

## Phase 2: Reliability and Visual Feedback
**Goal:** Make the simulation visually stable and understandable in the Blender viewport.

- [ ] Continuous collision validation (no intersections, even for fast-moving objects).  
  _Next:_ CCD hooks exist in core; expose toggles & add regression tests.
- [ ] Smooth elastic responses:
  - Visually accurate bounces.
  - Stable stacks and dense contacts.
- [~] Real-time parameter feedback:
  - [x] Sliders for stiffness, friction, solver tolerances.
  - [ ] Immediate viewport response for parameter edits mid-sim (requires re-init hooks).
- [x] Debug overlays:
  - [x] Contact points, normals (type-colored) and pins visualized in viewport.
  - [ ] Energy drift / constraint violation visualization.

---

## Phase 3: Usability and Workflow
**Goal:** Make AndoSim intuitive and easy to use within typical Blender workflows.

- [ ] Panel and UI design:
  - Group parameters logically.
  - Presets for common materials (metal, rubber, jelly, etc.).
- [ ] Keyframe integration:
  - Bake AndoSim simulations to Blender keyframes for animation.
- [ ] Scene save/load support:
  - Persist AndoSim-specific simulation states across Blender sessions.
- [ ] Compatibility with modifiers:
  - Ensure AndoSim plays nicely with subdivision, shape keys, and other modifiers.

---

### Current Focus
- Material preset system (rubber, metal, cloth, jelly) powering solver parameters.
- Collision validation pass to surface CCD/debug metrics in the UI.
- Documentation refresh once Phase 2 reliability work lands.

---

## Phase 4: Advanced Features / “Wow” Factor
**Goal:** Deliver features that make AndoSim clearly different from Blender’s built-in physics.

- [ ] Hybrid rigid + elastic simulation:
  - Simulate metal, soft bodies, and mixed stacks in the same solver.
- [ ] Optional GPU acceleration or batched simulation (if feasible).
- [ ] Canonical test scenes:
  - Prebuilt scenes to show continuous collision, high-density stacking, and soft bounces.
- [ ] Export metrics / validation panel (optional):
  - Display energy, momentum, and contact statistics.

---

## Phase 5: Documentation & Showcase
**Goal:** Make the add-on approachable and appealing to new users.

- [ ] Write a “Getting Started” guide:
  - Quick setup, parameter explanation, example scene.
- [ ] Include screenshots / GIFs demonstrating unique features.
- [ ] Provide canonical test scenes for users to try immediately.
- [ ] Encourage community contributions:
  - Include a “How to extend AndoSim” section for plugin development.

---

> Once Phase 1 is completed with the core physics engine, the AI agent can begin working on Phases 2–5 to create a polished, visually compelling Blender add-on.
