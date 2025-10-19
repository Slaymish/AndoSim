# Phase 3: Usability and Workflow - Implementation Plan
**Start Date**: October 19, 2025

---

## Executive Summary

**Phase 3 Goal**: Transform the Ando Barrier Physics simulator from a working prototype into an intuitive, production-ready Blender add-on with seamless workflow integration.

**Focus Areas**:
1. **Keyframe baking** (already 90% complete)
2. **Friction implementation** (paper Section 3.7 - core physics feature)
3. **Strain limiting** (paper Section 3.2 - prevents excessive stretching)
4. **Enhanced material presets** (artist-friendly workflow)
5. **Advanced visualizations** (gap heatmaps, strain display)
6. **Scene persistence** (save/load simulation state)

**Status**: Phase 2 is 60% complete (3/5 tasks). Phase 3 can begin in parallel since core reliability features are production-ready.

---

## Task Prioritization

### Priority 1: Critical User Features (Must-Have)
These features directly impact user workflows and have been requested repeatedly:

1. **Keyframe Baking Enhancement** (90% complete)
   - Current state: Shape key baking works
   - Missing: Progress bar, cancellation, mesh deformation options
   - Impact: HIGH - Users can't export animations without this

2. **Friction Implementation** (Task 10 from roadmap)
   - Current state: Not implemented
   - Paper reference: Section 3.7 (quadratic friction potential)
   - Impact: HIGH - Critical for realistic contact behavior (sliding, stacking)

### Priority 2: Core Physics Features (Should-Have)
These complete the paper's methodology:

3. **Strain Limiting** (Task 5 from roadmap)
   - Current state: Not implemented
   - Paper reference: Section 3.2 (SVD-based strain barrier)
   - Impact: MEDIUM - Prevents cloth over-stretching, improves realism

4. **Dynamic Stiffness Optimization** (Task 4 completion)
   - Current state: Basic implementation done
   - Missing: mass/gap takeover near tiny gaps, H projection caching
   - Impact: MEDIUM - Performance improvement, numerical stability

### Priority 3: Workflow Enhancements (Nice-to-Have)
These improve artist experience:

5. **Material Preset Expansion**
   - Current state: 4 presets (Cloth, Rubber, Metal, Jelly)
   - Add: Leather, Silk, Canvas, Foam, Plastic (with descriptions)
   - Impact: LOW - Artists can manually adjust, but presets save time

6. **Advanced Debug Visualizations**
   - Current state: Contact points, normals, pins displayed
   - Add: Gap heatmap, strain visualization, energy density
   - Impact: LOW - Helpful for debugging, not essential for production

7. **Scene Persistence**
   - Current state: Parameters stored in .blend file
   - Missing: Simulation state save/load, constraint serialization
   - Impact: LOW - Users can re-bake simulations

---

## Task Breakdown

### Task 1: Keyframe Baking Enhancement ✅ (90% Complete)

**Current Implementation**:
- ✅ Shape key creation and animation
- ✅ Frame range selection (cache_start → cache_end)
- ✅ Substep calculation (steps_per_frame based on dt)
- ✅ Pin constraint extraction
- ✅ Ground plane support
- ✅ Progress reporting every 10 frames

**Remaining Work** (~1 hour):
- [ ] Add Blender progress bar (window_manager.progress_begin/update/end)
- [ ] Implement cancellation via escape key detection
- [ ] Add option to bake to mesh deformation instead of shape keys
- [ ] Validate mesh topology preservation

**Implementation Details**:
```python
# Add to ANDO_OT_bake_simulation.execute()
wm = context.window_manager
wm.progress_begin(start_frame, end_frame)

for frame in range(start_frame, end_frame + 1):
    # Check for user cancellation
    if context.window_manager.baking_cancelled:
        wm.progress_end()
        return {'CANCELLED'}
    
    # Update progress bar
    wm.progress_update(frame - start_frame)
    
    # ... simulation code ...

wm.progress_end()
```

**Testing**:
- Bake 20×20 cloth for 100 frames
- Test cancellation mid-bake
- Verify shape keys playback smoothly

---

### Task 2: Friction Implementation (Task 10) 🔥 HIGH PRIORITY

**Paper Reference**: Section 3.7 - Friction Model

**Theory**:
```
V_friction(x, x_prev) = (k_f / 2) * ||Δx_tangent||²
where:
- Δx_tangent = relative tangential motion
- k_f = friction stiffness (computed from contact forces)
- Hessian contribution: ∇²V_friction added to system matrix
```

**Implementation Plan** (~4-6 hours):

#### Step 1: C++ FrictionModel Class (`src/core/friction.h/cpp`)
```cpp
class FrictionModel {
public:
    // Compute friction energy for a single contact
    static Real compute_energy(
        const Vec3& x_current,
        const Vec3& x_previous,
        const Vec3& contact_normal,
        Real friction_mu,
        Real normal_force
    );
    
    // Gradient w.r.t current positions
    static Vec3 compute_gradient(...);
    
    // Hessian contribution (3×3 block per vertex)
    static Mat3 compute_hessian(...);
    
    // Compute friction stiffness from contact force
    static Real compute_friction_stiffness(
        Real normal_force,
        Real friction_mu,
        Real dt
    );
};
```

#### Step 2: Integration into Integrator
- Store previous positions (`x_prev`) in `State`
- Compute friction energy after collision detection
- Add friction gradient to RHS of Newton system
- Add friction Hessian blocks to system matrix
- Update `x_prev` after each successful step

#### Step 3: Python Bindings
```python
# Expose friction parameters (already in SimParams)
params.enable_friction  # bool
params.friction_mu      # float (0.0-1.0)
params.friction_epsilon # float (small value for numerical stability)
```

#### Step 4: Testing
- C++ unit test: Sliding box on inclined plane
- Expected: Box slides when angle > arctan(μ), sticks otherwise
- Numerical validation: Energy dissipation matches analytical model

**Acceptance Criteria**:
- Cloth slides realistically on surfaces
- Stacking cloth pieces remain stable (no sliding)
- Energy dissipation observable in energy panel
- No numerical instabilities (SPD enforcement)

---

### Task 3: Strain Limiting (Task 5) 🔥 HIGH PRIORITY

**Paper Reference**: Section 3.2 - Strain Limiting with Cubic Barrier

**Theory**:
```
Per-face strain barrier:
V_strain(F) = V_weak(σ_max - σ_limit, τ, k_SL)
where:
- F = deformation gradient per triangle
- σ_max = largest singular value of F (max stretch)
- σ_limit = user-specified limit (e.g., 1.05 = 5% stretch)
- τ = barrier range (default: 0.01)
- k_SL = strain stiffness (computed from elasticity)
```

**Implementation Plan** (~5-7 hours):

#### Step 1: SVD Computation (`src/core/svd_utils.h/cpp`)
```cpp
// Eigen has built-in SVD, but add wrapper for degeneracy handling
struct SVDResult {
    Vec3 singular_values;
    Mat3 U;
    Mat3 V;
};

SVDResult compute_svd_safe(const Mat3& F, Real epsilon = 1e-8);
```

#### Step 2: StrainLimiting Class (`src/core/strain_limiting.h/cpp`)
```cpp
class StrainLimiting {
public:
    // Compute strain barrier energy for all faces
    static Real compute_energy(
        const Mesh& mesh,
        const State& state,
        Real strain_limit,
        Real strain_tau
    );
    
    // Gradient w.r.t. vertex positions (9D per triangle)
    static void compute_gradient(...);
    
    // Hessian blocks (9×9 per triangle, distributed to vertices)
    static void compute_hessian(...);
    
    // Compute k_SL from elasticity Hessian
    static Real compute_strain_stiffness(
        const Mat3& H_elasticity,
        const Vec3& singular_values
    );
};
```

#### Step 3: Integration into Integrator
- Compute per-face deformation gradients: `F = Ds * Dm_inv`
- SVD decomposition: `F = U Σ Vᵀ`
- Check if `σ_max > σ_limit - τ` (inside barrier domain)
- Add strain energy/gradient/Hessian to Newton system

#### Step 4: UI Integration
```python
# Already in properties.py:
props.enable_strain_limiting  # bool
props.strain_limit            # float (1.0-2.0, default 1.05)
props.strain_tau              # float (barrier range, default 0.01)
```

#### Step 5: Testing
- C++ unit test: Stretch single triangle beyond limit
- Expected: Energy/gradient prevent over-stretching
- Visual test: Cloth with 5% strain limit shows wrinkles instead of stretching

**Acceptance Criteria**:
- Cloth stops stretching at specified limit
- Wrinkles form naturally (no "locked" appearance)
- No numerical instabilities (SVD handles degeneracies)
- Performance overhead < 10% (SVD is O(n) per face)

---

### Task 4: Material Preset Expansion

**Current Presets** (4 total):
1. Cloth: E=10^6, ν=0.3, ρ=1000, h=0.001
2. Rubber: E=10^5, ν=0.48, ρ=1100, h=0.002
3. Metal: E=2×10^8, ν=0.3, ρ=7800, h=0.0005
4. Jelly: E=10^4, ν=0.49, ρ=1050, h=0.003

**New Presets to Add** (5 more):

| Material | Young's Modulus (Pa) | Poisson's Ratio | Density (kg/m³) | Thickness (m) | Use Case |
|----------|---------------------|-----------------|-----------------|---------------|----------|
| Leather  | 5×10^6              | 0.4             | 950             | 0.002         | Jackets, furniture |
| Silk     | 5×10^5              | 0.35            | 1300            | 0.0003        | Dresses, scarves |
| Canvas   | 2×10^6              | 0.3             | 1400            | 0.0015        | Tents, sails |
| Foam     | 5×10^4              | 0.45            | 200             | 0.01          | Cushions, padding |
| Plastic  | 1×10^9              | 0.35            | 1200            | 0.001         | Tarps, bags |

**Implementation** (~1 hour):
1. Add presets to `properties.py` in `MATERIAL_PRESETS` dict
2. Add descriptions for UI tooltips
3. Update `ui.py` to show preset descriptions
4. Test each preset with validation scene

---

### Task 5: Advanced Debug Visualizations

**Goal**: Surface internal physics state for debugging and validation

**Implementation Plan** (~3-4 hours):

#### Visualization 1: Gap Heatmap
- Display color-coded contact gaps on mesh surface
- Color scale: Green (large gap) → Yellow → Red (tiny gap)
- Uses Blender vertex colors or GPU shader

```python
# In visualization.py
def update_gap_heatmap(mesh, contacts, gap_max):
    # Map contacts to nearest vertices
    # Compute color: red = gap/gap_max, green = 1 - gap/gap_max
    # Update vertex colors or shader uniforms
```

#### Visualization 2: Strain Overlay
- Display per-face strain percentage
- Color scale: Green (< 1%) → Yellow (1-5%) → Red (> 5%)
- Only visible when strain limiting is enabled

```python
def update_strain_visualization(mesh, state, strain_limit):
    # Compute per-face deformation gradients
    # Extract max singular values
    # Color faces by (σ_max - 1.0) / (strain_limit - 1.0)
```

#### Visualization 3: Energy Density
- Display elastic energy per triangle
- Useful for finding stress concentrations
- Color scale: Blue (low energy) → Green → Red (high energy)

```python
def update_energy_density(mesh, state):
    # Compute per-face elastic energy
    # Normalize by face area
    # Color faces by energy density
```

**UI Integration**:
```python
# Add to ui.py Debug Visualization panel
row = layout.row()
row.prop(props, "show_gap_heatmap", text="Gap Heatmap")
row.prop(props, "show_strain_overlay", text="Strain")
row.prop(props, "show_energy_density", text="Energy")
```

---

### Task 6: Scene Persistence & Save/Load

**Goal**: Save/load simulation state across Blender sessions

**Implementation** (~2-3 hours):

#### Data to Persist:
1. Constraint setup (pins, walls)
2. Material properties
3. Solver parameters
4. Simulation cache (optional)

#### Approach 1: Blender Custom Properties
```python
# Store in object custom properties
obj["ando_pins"] = [list of vertex indices]
obj["ando_walls"] = [list of wall dicts]
obj["ando_material"] = {E, ν, ρ, h}
obj["ando_params"] = {dt, beta_max, ...}
```

#### Approach 2: External JSON File
```python
# Save to .blend directory
scene_data = {
    "pins": [...],
    "walls": [...],
    "material": {...},
    "params": {...},
}
json.dump(scene_data, open("scene_state.json", "w"))
```

**Operators**:
```python
class ANDO_OT_save_scene_state(Operator):
    """Save simulation state to file"""
    
class ANDO_OT_load_scene_state(Operator):
    """Load simulation state from file"""
```

---

## Timeline Estimate

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| 1. Keyframe Baking Polish | HIGH | 1 hour | None |
| 2. Friction Implementation | HIGH | 6 hours | None |
| 3. Strain Limiting | HIGH | 7 hours | None |
| 4. Material Presets | MEDIUM | 1 hour | None |
| 5. Debug Visualizations | LOW | 4 hours | Task 3 (strain) |
| 6. Scene Persistence | LOW | 3 hours | None |

**Total Estimated Effort**: 22 hours (~3 days of focused development)

**Recommended Order**:
1. Start with **Friction** (biggest physics gap, enables realistic contact)
2. Then **Strain Limiting** (completes paper methodology)
3. Polish **Keyframe Baking** (quick win for users)
4. Add **Material Presets** (easy, high user value)
5. Implement **Debug Visualizations** (helpful but not critical)
6. Add **Scene Persistence** (nice-to-have for power users)

---

## Success Metrics

### Phase 3 Completion Criteria:
- [x] Baking produces smooth keyframe animations
- [ ] Friction enables realistic sliding and stacking
- [ ] Strain limiting prevents cloth over-stretching
- [ ] 9+ material presets cover common use cases
- [ ] Debug visualizations aid in parameter tuning
- [ ] Scene state persists across Blender sessions

### User Experience Goals:
- **Artists**: "I can bake a cloth animation in 3 clicks"
- **Technical Users**: "Friction and strain limiting work as expected from the paper"
- **Developers**: "Debug overlays help me validate physics correctness"

### Performance Targets:
- Friction overhead: < 15% (acceptable for contact-heavy scenes)
- Strain limiting overhead: < 10% (SVD is O(n) per face)
- Baking speed: Real-time preview should match baked output
- Total Phase 3 overhead: < 25% compared to Phase 2 baseline

---

## Risk Assessment

### HIGH RISK
- ⚠️ **Friction Stability**: Quadratic potential may introduce stiffness
  - Mitigation: Eigenvalue capping, conservative stiffness formula
  - Fallback: Implement velocity-based Coulomb friction instead

- ⚠️ **SVD Performance**: Per-face SVD may be slow for large meshes
  - Mitigation: Use Eigen's optimized 3×3 SVD, cache results
  - Fallback: Implement strain limiting as post-process constraint

### MEDIUM RISK
- ⚠️ **Baking Performance**: Large meshes (10K+ vertices) may slow down
  - Mitigation: Multi-threading (Python GIL limits this)
  - Fallback: Add "Low Quality" mode with fewer substeps

- ⚠️ **Visualization Performance**: GPU overlays may drop FPS
  - Mitigation: Only update every N frames, use efficient shaders
  - Fallback: Disable by default, enable on-demand

### LOW RISK
- ✅ Material presets are trivial (just parameter sets)
- ✅ Scene persistence uses standard Blender APIs
- ✅ Keyframe baking is already 90% working

---

## Documentation Needed

### User-Facing:
- [ ] "Quick Start Guide" (5-minute tutorial with screenshots)
- [ ] "Material Presets Reference" (table of all presets + use cases)
- [ ] "Friction & Strain Limiting Explained" (what do these parameters do?)
- [ ] "Troubleshooting Guide" (common issues + solutions)

### Developer-Facing:
- [ ] "Friction Implementation Notes" (equations, code mapping)
- [ ] "Strain Limiting Derivation" (SVD → barrier energy → derivatives)
- [ ] "Phase 3 API Reference" (Python bindings for new features)
- [ ] "Performance Profiling Results" (before/after comparisons)

---

## Next Steps

**Immediate Action** (after user approval):
1. Mark Task 1 (Keyframe Baking) as "in-progress"
2. Implement progress bar + cancellation (~30 minutes)
3. Test baking on 20×20 mesh, validate output
4. Mark Task 1 as complete, move to Task 2 (Friction)

**User Decision Required**:
- Should we prioritize **Friction** (realistic physics) or **Material Presets** (quick artist value)?
- Do you want **all 6 tasks** completed, or focus on top 3-4?
- Any specific features from Phase 4 (GPU acceleration, rigid bodies) to pull forward?

---

**Document Status**: Draft, awaiting user feedback  
**Created**: October 19, 2025  
**Author**: Copilot (assisted)  
**Estimated Completion**: Phase 3 @ 100% by October 22, 2025 (3 days)
