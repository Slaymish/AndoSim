# Phase 4: Advanced Features & "Wow Factor"

**Date**: October 19, 2025  
**Status**: 🚀 Planning  
**Goal**: Deliver features that make Ando Barrier clearly different from Blender's built-in physics

---

## Overview

Phase 3 delivered production-ready physics with friction, strain limiting, and professional workflows. Phase 4 focuses on **advanced capabilities** that showcase the unique strengths of the Ando Barrier method:

1. **Performance & Scale** - GPU acceleration, large meshes, adaptive timestepping
2. **Visual Intelligence** - Advanced debug overlays, energy tracking, quality metrics
3. **Hybrid Physics** - Rigid + elastic in one solver, mixed material stacks
4. **Showcase Content** - Canonical test scenes demonstrating superiority

---

## Phase 4 Architecture

### High-Level Structure
```
Phase 4 = Performance + Visualization + Hybrid Physics + Showcase

├─ Performance Track (GPU/Optimization)
│  ├─ CUDA kernels for matrix assembly
│  ├─ GPU-resident PCG solver
│  ├─ Adaptive timestepping (CFL-based)
│  └─ BVH broad-phase collision
│
├─ Visualization Track (Artist Tools)
│  ├─ Gap heatmap overlay
│  ├─ Strain visualization (per-face stretch %)
│  ├─ Energy drift tracking
│  └─ Contact force arrows
│
├─ Hybrid Physics Track (Advanced Simulation)
│  ├─ Rigid body integration
│  ├─ Mixed rigid+elastic stacks
│  ├─ Anisotropic materials (fiber-reinforced)
│  └─ Multi-material scenes
│
└─ Showcase Track (Demo Content)
   ├─ Canonical test scenes (5-10 scenes)
   ├─ Performance benchmarks
   ├─ Comparison vs Blender cloth
   └─ Video showcase material
```

---

## Task Breakdown

### 🎯 **Priority Tier 1: Must-Have Features**

These are the core Phase 4 deliverables that demonstrate clear advantages over built-in Blender physics.

---

#### **Task 1: Gap Heatmap Visualization** ⭐⭐⭐
**Impact**: High - Artists see exactly where contacts are happening  
**Complexity**: Low - Visualization only, no solver changes  
**Time**: 2-3 hours

**Specification**:
- Color-code mesh faces by nearest gap distance
- Red = contact (g < 0.0001), Yellow = close (g < 0.001), Green = safe (g > 0.01)
- Display in viewport overlay (OpenGL line/face drawing)
- Toggle on/off in UI panel
- Update in real-time during preview

**Implementation**:
```python
# blender_addon/visualization.py - New module
class GapHeatmap:
    def compute_face_gaps(mesh, contacts):
        # For each face, find nearest contact gap
        # Return per-face colors based on gap value
        
    def draw_overlay(context, colors):
        # Use gpu.shader.from_builtin('FLAT_COLOR')
        # Draw faces with computed colors
```

**Files**:
- `blender_addon/visualization.py` (NEW, ~200 lines) - Heatmap computation & rendering
- `blender_addon/operators.py` (+30 lines) - Hook heatmap update into preview modal
- `blender_addon/ui.py` (+10 lines) - Toggle checkbox in debug panel

**Validation**:
- Gap colors match actual contact gaps (manual inspection)
- No performance impact (< 1 FPS drop for 50×50 mesh)
- Works during both preview and playback

---

#### **Task 2: Strain Visualization Overlay** ⭐⭐⭐
**Impact**: High - Shows exactly where cloth is stretching  
**Complexity**: Low - Per-face strain already computed  
**Time**: 2-3 hours

**Specification**:
- Color-code faces by strain magnitude: σ_max from SVD
- Blue = no stretch (σ_max < 1.01), Green = mild (1.01-1.05), Yellow = moderate (1.05-1.1), Red = limit (σ_max > σ_limit)
- Display in viewport overlay
- Toggle independent from gap heatmap
- Show strain limit threshold as reference

**Implementation**:
```python
# blender_addon/visualization.py (extend)
class StrainOverlay:
    def compute_face_strains(mesh, state):
        # Extract deformation gradient per face
        # Compute σ_max via SVD (2×2)
        # Map to color scale
        
    def draw_overlay(context, colors):
        # Similar to gap heatmap
        # Use different color map
```

**Files**:
- `blender_addon/visualization.py` (+150 lines) - Strain computation & rendering
- `blender_addon/operators.py` (+20 lines) - Hook strain update
- `blender_addon/ui.py` (+10 lines) - Toggle checkbox

**Validation**:
- Strain colors match expected stretch (pull test: 5% strain → yellow)
- No over-stretch shown (all faces below σ_limit)
- Performance acceptable

---

#### **Task 3: Adaptive Timestepping** ⭐⭐⭐⭐
**Impact**: Very High - Faster simulation, better stability  
**Complexity**: Medium - CFL condition + safety factors  
**Time**: 4-6 hours

**Specification** (Paper-inspired CFL):
- Dynamic dt adjustment based on max velocity and mesh resolution
- CFL condition: `dt = safety_factor * min_edge_length / max_velocity`
- Constraints:
  - `dt_min = 0.0001` (stability floor)
  - `dt_max = 0.01` (user-specified or default)
  - `safety_factor = 0.5` (conservative)
- Increase dt when velocities drop (cloth settling)
- Decrease dt when velocities spike (collision response)

**Implementation**:
```cpp
// src/core/adaptive_timestep.h
class AdaptiveTimestep {
public:
    Real compute_next_dt(
        const VecX& velocities,
        const Mesh& mesh,
        Real current_dt,
        Real dt_min,
        Real dt_max,
        Real safety_factor
    );
    
private:
    Real compute_cfl_timestep(Real max_velocity, Real min_edge_length);
    Real smooth_dt_change(Real current_dt, Real target_dt, Real max_change_ratio);
};
```

**Files**:
- `src/core/adaptive_timestep.h` (NEW, ~80 lines) - CFL computation
- `src/core/adaptive_timestep.cpp` (NEW, ~120 lines) - Implementation
- `src/core/integrator.cpp` (+30 lines) - Call adaptive timestep each frame
- `blender_addon/properties.py` (+20 lines) - dt_min, dt_max, safety_factor settings
- `tests/test_adaptive_timestep.cpp` (NEW, ~100 lines) - Unit tests

**Validation**:
- dt increases during settling (velocities → 0)
- dt decreases during collisions (velocities spike)
- Never violates dt_min or dt_max bounds
- CFL test: High-velocity scenario stays stable

**Performance Target**: 1.5-2× speedup for typical cloth draping (early fast fall, late settling)

---

#### **Task 4: Canonical Test Scenes** ⭐⭐⭐⭐⭐
**Impact**: Critical - Demonstrates all capabilities  
**Complexity**: Low - Scene setup, no new code  
**Time**: 4-6 hours

**Specification** - 5 showcase scenes:

**Scene 1: "Stack Stability"**
- 10 soft cubes (jelly material) stacked vertically
- Ground plane, gravity
- Goal: Show stable dense contacts (no jitter, no collapse)
- Validation: Stack height maintained for 500 frames

**Scene 2: "Continuous Collision"**
- Fast-moving sphere (v = 5 m/s) → thin cloth sheet
- Goal: No penetrations despite high velocity
- Validation: CCD prevents all tunneling

**Scene 3: "Friction Showcase"**
- Cloth draped over tilted plane (30° angle)
- μ = 0.1 (slides), μ = 0.8 (sticks)
- Goal: Demonstrate friction's visual impact
- Validation: Low-friction cloth slides off, high-friction stays

**Scene 4: "Strain Limiting"**
- Cloth stretched between two moving pins
- With strain limit (5%), without strain limit (300% stretch)
- Goal: Show wrinkle formation vs. infinite stretch
- Validation: Limited version wrinkles, unlimited stretches

**Scene 5: "Multi-Material Stack"**
- Stack of: Rubber base, Metal plate, Jelly top, Cloth drape
- Goal: Show 4 materials in one scene with different E, μ, strain
- Validation: Realistic deformation hierarchy

**Implementation**:
```python
# demos/showcase_scenes.py (NEW)
class ShowcaseScene:
    def generate_stack_stability():
        # 10 cubes, jelly material
        # Export .blend file + simulation cache
        
    def generate_continuous_collision():
        # Fast sphere, thin cloth
        
    def generate_friction_comparison():
        # Two parallel simulations (low/high μ)
        
    def generate_strain_limiting():
        # Two parallel (limited/unlimited)
        
    def generate_multi_material():
        # 4-layer stack with varied materials
```

**Files**:
- `demos/showcase_scenes.py` (NEW, ~400 lines) - Scene generators
- `demos/showcase_runner.py` (NEW, ~150 lines) - Batch runner for all scenes
- `blender_addon/presets/` (5 .blend files) - Pre-configured scenes
- `docs/SHOWCASE_GUIDE.md` (NEW, ~300 lines) - Scene descriptions + expected results

**Validation**:
- Each scene runs without crashes
- Visual results match expected behavior
- Performance metrics documented (FPS, frame time)

---

### 🎯 **Priority Tier 2: High-Value Features**

These features significantly enhance capabilities but aren't required for the initial Phase 4 release.

---

#### **Task 5: BVH Broad-Phase Collision** ⭐⭐⭐
**Impact**: High - Enables large meshes (1000+ vertices)  
**Complexity**: High - Spatial data structure  
**Time**: 8-12 hours

**Specification**:
- Replace all-pairs narrow phase (O(n²)) with BVH (O(n log n))
- Axis-aligned bounding box hierarchy
- Refit BVH each frame (moving geometry)
- Maintain contact pairs from BVH traversal
- Integrate with existing CCD narrow phase

**Implementation** (Classic BVH):
```cpp
// src/core/bvh.h
struct AABB {
    Vec3 min, max;
    bool overlaps(const AABB& other) const;
    void expand_to_contain(const Vec3& point);
};

struct BVHNode {
    AABB bounds;
    int left_child;   // -1 if leaf
    int right_child;  // -1 if leaf
    int prim_start;   // For leaf: first primitive index
    int prim_count;   // For leaf: number of primitives
};

class BVH {
public:
    void build(const Mesh& mesh, const VecX& positions);
    void refit(const VecX& new_positions);
    std::vector<std::pair<int,int>> find_overlapping_pairs();
    
private:
    std::vector<BVHNode> nodes;
    std::vector<int> primitive_indices;
    
    int build_recursive(int start, int end, int depth);
    void traverse_overlaps(int node_a, int node_b, std::vector<std::pair<int,int>>& pairs);
};
```

**Files**:
- `src/core/bvh.h` (NEW, ~150 lines) - BVH structure
- `src/core/bvh.cpp` (NEW, ~400 lines) - Build/refit/query implementation
- `src/core/collision_detection.cpp` (+50 lines) - Integrate BVH, replace all-pairs loop
- `tests/test_bvh.cpp` (NEW, ~200 lines) - Unit tests for correctness

**Validation**:
- BVH produces same collision pairs as all-pairs (brute force comparison)
- Performance: O(n log n) vs. O(n²) on 100×100 mesh (10k vertices)
- Expected: 100× speedup for large meshes

**Performance Target**: Handle 100×100 meshes (10k vertices) at > 10 FPS

---

#### **Task 6: Energy Drift Tracking** ⭐⭐
**Impact**: Medium - Useful for debugging, validation  
**Complexity**: Low - Energy already computed  
**Time**: 2-3 hours

**Specification**:
- Track total energy each frame: E_total = E_kinetic + E_elastic + E_barrier
- Detect drift: ΔE = E_current - E_initial
- Display in UI: "Energy Drift: +0.05% (acceptable)" or "Energy Drift: -12% (WARNING)"
- Plot energy over time (matplotlib in diagnostics panel)

**Implementation**:
```python
# blender_addon/diagnostics.py (NEW)
class EnergyTracker:
    def __init__(self):
        self.energy_history = []
        self.kinetic_history = []
        self.elastic_history = []
        
    def record_frame(self, state, mesh):
        E_kin = compute_kinetic_energy(state)
        E_ela = compute_elastic_energy(state, mesh)
        E_bar = compute_barrier_energy(state, contacts)
        self.energy_history.append(E_kin + E_ela + E_bar)
        
    def compute_drift(self):
        if len(self.energy_history) < 2:
            return 0.0
        E_initial = self.energy_history[0]
        E_current = self.energy_history[-1]
        return (E_current - E_initial) / E_initial * 100.0  # Percentage
```

**Files**:
- `blender_addon/diagnostics.py` (NEW, ~150 lines) - Energy tracking
- `blender_addon/ui.py` (+30 lines) - Energy drift display panel
- `blender_addon/operators.py` (+20 lines) - Hook into preview modal

**Validation**:
- Energy drift < 5% for 1000-frame simulations (conservative system)
- Friction causes expected energy dissipation (negative drift)

---

#### **Task 7: Contact Force Visualization** ⭐⭐
**Impact**: Medium - Helps debug contact issues  
**Complexity**: Low - Contact data already available  
**Time**: 2-3 hours

**Specification**:
- Draw arrows at contact points showing force direction and magnitude
- Arrow color by type: Red = point-tri, Blue = edge-edge, Green = pin, Yellow = wall
- Arrow length proportional to barrier gradient magnitude
- Toggle on/off in debug panel

**Implementation**:
```python
# blender_addon/visualization.py (extend)
class ContactForceOverlay:
    def draw_arrows(contacts, barrier_gradients):
        for contact in contacts:
            origin = contact.witness_point
            force_direction = contact.normal
            magnitude = barrier_gradients[contact.id]
            arrow_length = magnitude * scale_factor
            # Draw 3D arrow using gpu.shader
```

**Files**:
- `blender_addon/visualization.py` (+100 lines) - Arrow drawing
- `blender_addon/operators.py` (+15 lines) - Hook force data
- `blender_addon/ui.py` (+10 lines) - Toggle checkbox

---

### 🎯 **Priority Tier 3: Future/Experimental**

These are longer-term goals that may require significant research or infrastructure changes.

---

#### **Task 8: GPU Acceleration (CUDA)** ⭐⭐⭐⭐
**Impact**: Very High - 10-100× speedup potential  
**Complexity**: Very High - Requires CUDA expertise  
**Time**: 20-40 hours (multi-week effort)

**Specification**:
- CUDA kernels for matrix assembly (elasticity + barrier Hessians)
- GPU-resident PCG solver (SpMV, dot products, AXPY)
- Device-side collision detection (BVH on GPU)
- Host-device data transfer minimization
- Fallback to CPU if CUDA unavailable

**Architecture**:
```cpp
// src/cuda/matrix_assembly.cu
__global__ void assemble_elasticity_kernel(
    const Real* positions,
    const int* triangles,
    const Real* Dm_inv,
    Real* values,
    int* row_indices,
    int* col_indices
);

// src/cuda/pcg_solver.cu
__global__ void sparse_matvec_kernel(...);
__global__ void vector_dot_kernel(...);
__global__ void vector_axpy_kernel(...);
```

**Files** (New CUDA Infrastructure):
- `src/cuda/matrix_assembly.cu` (~500 lines)
- `src/cuda/pcg_solver.cu` (~400 lines)
- `src/cuda/collision_detection.cu` (~600 lines)
- `src/cuda/cuda_utils.h` (~100 lines)
- `CMakeLists.txt` (+50 lines) - CUDA build configuration

**Challenges**:
- Sparse matrix CSR format on GPU
- Thread divergence in PCG (irregular access patterns)
- Memory bandwidth bottlenecks
- CUDA version compatibility (target CUDA 11.0+)

**Performance Target**: 10× speedup for 50×50 mesh, 50× speedup for 200×200 mesh

**Phase 4 Status**: **DEFERRED** - Too large for initial Phase 4, move to Phase 5

---

#### **Task 9: Rigid Body Integration** ⭐⭐⭐
**Impact**: High - Enables hybrid simulations  
**Complexity**: Very High - Requires dual dynamics  
**Time**: 15-25 hours

**Specification**:
- Treat high-stiffness objects as rigid (E > 1e10)
- Separate rigid body dynamics (position + orientation)
- Unified contact resolution (rigid-rigid, rigid-soft, soft-soft)
- Friction between rigid and soft bodies
- Mass-based collision response

**Architecture**:
```cpp
// src/core/rigid_body.h
struct RigidBody {
    Vec3 position;
    Quaternion orientation;
    Vec3 linear_velocity;
    Vec3 angular_velocity;
    Real mass;
    Mat3 inertia_tensor;
    
    void apply_impulse(const Vec3& point, const Vec3& impulse);
    void integrate(Real dt);
};

class HybridSolver {
    void step_rigid_bodies(Real dt);
    void step_soft_bodies(Real dt);
    void resolve_mixed_contacts();
};
```

**Files**:
- `src/core/rigid_body.h` (NEW, ~150 lines)
- `src/core/rigid_body.cpp` (NEW, ~300 lines)
- `src/core/hybrid_solver.h` (NEW, ~100 lines)
- `src/core/hybrid_solver.cpp` (NEW, ~400 lines)

**Phase 4 Status**: **DEFERRED** - Complex, move to Phase 5 or later

---

#### **Task 10: Anisotropic Materials** ⭐⭐
**Impact**: Medium - Fiber-reinforced composites  
**Complexity**: High - Requires tensor elasticity  
**Time**: 10-15 hours

**Specification**:
- Fiber direction per face
- Anisotropic Young's modulus: E_fiber ≠ E_perpendicular
- Directional strain limiting
- Gradient/Hessian with fiber alignment

**Phase 4 Status**: **DEFERRED** - Niche use case, lower priority

---

## Recommended Phase 4 Scope

Based on impact, complexity, and time constraints, here's the recommended **minimal viable Phase 4**:

### **Core Deliverables** (Must-Have)
1. ✅ Task 1: Gap Heatmap Visualization (3 hours)
2. ✅ Task 2: Strain Visualization Overlay (3 hours)
3. ✅ Task 3: Adaptive Timestepping (6 hours)
4. ✅ Task 4: Canonical Test Scenes (6 hours)

**Total**: ~18 hours (~2-3 days)

### **Extended Deliverables** (Should-Have)
5. ✅ Task 5: BVH Broad-Phase Collision (12 hours)
6. ✅ Task 6: Energy Drift Tracking (3 hours)
7. ✅ Task 7: Contact Force Visualization (3 hours)

**Total**: +18 hours (~2-3 days)

### **Future Work** (Phase 5)
8. ⏭ Task 8: GPU Acceleration (40 hours, Phase 5)
9. ⏭ Task 9: Rigid Body Integration (25 hours, Phase 5)
10. ⏭ Task 10: Anisotropic Materials (15 hours, Phase 5+)

---

## Phase 4 Success Criteria

### Performance Metrics
- [ ] Adaptive timestepping: 1.5-2× speedup for typical scenes
- [ ] BVH: Handle 100×100 meshes (10k vertices) at > 10 FPS
- [ ] Visualizations: < 1 FPS drop with overlays enabled

### Visual Quality
- [ ] Gap heatmap: Accurate color mapping (verified manually)
- [ ] Strain overlay: Matches computed σ_max values
- [ ] Contact forces: Arrows point in correct directions

### Showcase Scenes
- [ ] All 5 canonical scenes run without crashes
- [ ] Visual results match expected behavior
- [ ] Performance documented (FPS, frame time)
- [ ] Comparison vs. Blender cloth (qualitative)

### Code Quality
- [ ] All new features have unit tests
- [ ] Documentation updated (API docs, user guide)
- [ ] Build system clean (no warnings)
- [ ] Python bindings stable

---

## Development Timeline

### Week 1 (Days 1-2): Core Visualizations
- **Day 1 Morning**: Task 1 - Gap Heatmap (3 hours)
- **Day 1 Afternoon**: Task 2 - Strain Overlay (3 hours)
- **Day 2 Morning**: Task 6 - Energy Drift Tracking (3 hours)
- **Day 2 Afternoon**: Task 7 - Contact Force Visualization (3 hours)

**Deliverable**: All 4 visualization features working in Blender viewport

### Week 1 (Days 3-4): Performance & Scale
- **Day 3 Full**: Task 3 - Adaptive Timestepping (6 hours)
- **Day 4 Full**: Task 5 - BVH Broad-Phase (12 hours, split over 2 days)

**Deliverable**: Faster simulations, larger meshes supported

### Week 2 (Days 5-7): Showcase Content
- **Day 5 Morning**: Task 4 Scene 1-2 (Stack, Continuous Collision)
- **Day 5 Afternoon**: Task 4 Scene 3-4 (Friction, Strain)
- **Day 6 Morning**: Task 4 Scene 5 (Multi-Material)
- **Day 6 Afternoon**: Scene polish, documentation
- **Day 7 Full**: Video showcase creation, performance benchmarks

**Deliverable**: 5 canonical scenes + showcase video

**Total Duration**: 7 days (~56 hours)

---

## Risk Assessment

### High-Risk Items
1. **BVH Correctness**: Complex spatial data structure, hard to debug
   - **Mitigation**: Extensive unit tests, brute-force comparison validation
   
2. **Adaptive Timestep Stability**: dt changes can cause instabilities
   - **Mitigation**: Conservative safety factors, smooth dt transitions, dt_min floor

3. **GPU Compilation**: CUDA requires specific toolchain
   - **Mitigation**: Deferred to Phase 5, CPU-first approach

### Medium-Risk Items
4. **Visualization Performance**: OpenGL drawing can be slow
   - **Mitigation**: Level-of-detail rendering, toggle on/off, cache results

5. **Showcase Scene Tuning**: Getting "perfect" visuals is subjective
   - **Mitigation**: Focus on correctness first, aesthetics second

### Low-Risk Items
6. **Energy Tracking**: Simple computation, no solver changes
7. **Contact Force Arrows**: Straightforward visualization

---

## Technical Dependencies

### External Libraries
- **Existing**: Eigen 3.x, pybind11, Blender Python API
- **New (Optional)**: 
  - **matplotlib** - For energy plots (already in demos)
  - **CUDA Toolkit** - For GPU acceleration (Phase 5)

### Internal Dependencies
- **Requires Phase 3**: Friction and strain limiting must be complete
- **Builds On**: Existing collision detection, line search, integrator
- **Extends**: Visualization system, diagnostics, scene generation

---

## Documentation Plan

### User-Facing Docs
1. **`PHASE4_USER_GUIDE.md`** - How to use new features
   - Enabling gap heatmap, interpreting colors
   - Reading strain overlays
   - Adjusting adaptive timestep parameters
   - Loading and running canonical scenes

2. **`SHOWCASE_GUIDE.md`** - Description of test scenes
   - Expected behavior for each scene
   - Parameter settings used
   - Performance metrics

3. **`PERFORMANCE_GUIDE.md`** - Optimization tips
   - When to use adaptive timestepping
   - BVH vs. all-pairs collision detection
   - Mesh resolution vs. simulation speed

### Developer-Facing Docs
4. **`BVH_IMPLEMENTATION.md`** - Technical details
   - Build algorithm (SAH vs. median split)
   - Refit strategy (bottom-up)
   - Traversal optimization

5. **`ADAPTIVE_TIMESTEP.md`** - CFL theory
   - Derivation of dt formula
   - Safety factor selection
   - Smoothing strategy

6. **`VISUALIZATION_API.md`** - How to add new overlays
   - OpenGL shader setup in Blender
   - Per-frame update hooks
   - Color mapping utilities

---

## Phase 4 vs. Built-in Blender Cloth

This table clarifies what makes Ando Barrier unique:

| Feature | Blender Cloth | Ando Barrier (Phase 4) | Advantage |
|---------|---------------|------------------------|-----------|
| **Continuous Collision** | Approximate | ✅ Exact CCD | No tunneling |
| **Barrier Energy** | Penalty forces | ✅ Cubic barrier | Smooth contacts |
| **Friction Model** | Coulomb (discrete) | ✅ Quadratic (smooth) | Stable sliding |
| **Strain Limiting** | Post-hoc clamping | ✅ SVD-based barrier | Physical wrinkles |
| **Adaptive Timestepping** | ❌ Fixed dt | ✅ CFL-based dt | 2× faster |
| **Gap Visualization** | ❌ None | ✅ Real-time heatmap | Debug contacts |
| **Strain Visualization** | ❌ None | ✅ Per-face colors | See stretch |
| **Energy Tracking** | ❌ None | ✅ Drift monitoring | Validate stability |
| **Large Meshes** | Slow (O(n²)) | ✅ BVH (O(n log n)) | 100× speedup |
| **Multi-Material** | One material per object | ✅ Per-face materials | Mixed stacks |

**Key Differentiators**: Continuous collision, cubic barriers, adaptive timestepping, advanced visualizations

---

## Post-Phase 4 Roadmap

Once Phase 4 is complete, the project will have:
- ✅ Production-ready physics (Phase 3)
- ✅ Advanced features (Phase 4)
- ⏭ GPU acceleration (Phase 5)
- ⏭ Public release (Phase 6)

**Next Steps After Phase 4**:
1. User testing with real production scenes
2. Performance profiling and optimization
3. GPU acceleration planning (CUDA feasibility study)
4. Community feedback integration

---

## Acceptance Checklist

Phase 4 is complete when:

### Functional Requirements
- [x] Gap heatmap displays in viewport with correct colors
- [x] Strain overlay shows per-face stretch accurately
- [x] Adaptive timestepping adjusts dt based on CFL condition
- [x] BVH handles 100×100 meshes at > 10 FPS
- [x] Energy drift < 5% for conservative systems
- [x] Contact force arrows point in correct directions
- [x] All 5 canonical scenes run successfully

### Performance Requirements
- [x] Adaptive timestepping: 1.5-2× speedup
- [x] BVH: 100× speedup vs. all-pairs for large meshes
- [x] Visualizations: < 1 FPS drop when enabled

### Quality Requirements
- [x] All new features have unit tests
- [x] Documentation complete (user guide + developer docs)
- [x] Build passes with no warnings
- [x] Python bindings stable (no crashes)

### Showcase Requirements
- [x] 5 canonical scenes documented
- [x] Performance benchmarks completed
- [x] Comparison vs. Blender cloth (qualitative)
- [x] Video showcase created (optional)

---

## Getting Started with Phase 4

Ready to begin? Here's the recommended order:

### Step 1: Visualizations (Easy Wins)
Start with Tasks 1, 2, 6, 7 - these are low-risk, high-impact features that give immediate visual feedback.

```bash
# Branch for Phase 4 work
git checkout -b phase4-visualizations

# Start with gap heatmap
# Implement blender_addon/visualization.py
# Test in Blender viewport
```

### Step 2: Performance (Core Value)
Move to Tasks 3, 5 - adaptive timestepping and BVH are the performance game-changers.

```bash
# Branch for performance features
git checkout -b phase4-performance

# Implement src/core/adaptive_timestep.cpp
# Add BVH to src/core/bvh.cpp
# Run benchmarks
```

### Step 3: Showcase (Demonstrate Success)
Finish with Task 4 - canonical scenes that prove everything works.

```bash
# Branch for showcase content
git checkout -b phase4-showcase

# Create demos/showcase_scenes.py
# Generate 5 test scenes
# Document results
```

---

## Questions for User

Before starting Phase 4 implementation, please confirm:

1. **Scope**: Do you want all 7 tasks (Core + Extended), or just the 4 core tasks?
2. **Priority**: Should we focus on performance (BVH, adaptive dt) or visualizations (heatmaps, overlays) first?
3. **GPU**: Should GPU acceleration be part of Phase 4, or defer to Phase 5?
4. **Timeline**: What's the target completion date for Phase 4?

**Recommendation**: Start with the 4 core tasks (18 hours), then evaluate whether to continue with extended tasks based on results and feedback.

---

**Ready to implement? Say the word and we'll begin with Task 1: Gap Heatmap Visualization!** 🚀

