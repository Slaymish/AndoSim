# Demo Status Report

**Last Updated:** October 17, 2025

## Current Status

### ✅ Working: All Core Demos
- **`demo_simple_fall`**: Basic gravity with forward Euler integration ✓
- **`demo_cloth_drape`**: Full Newton integrator with β accumulation ✓
- **`demo_cloth_wall`**: Wall constraints with barrier method ✓

All demos produce valid OBJ sequences and complete successfully.

## Recent Fixes (October 17, 2025)

### Issue: Integrator Constraint Extraction
**Status:** ✅ RESOLVED

The `Integrator::inner_newton_step()` function had incomplete constraint extraction that prevented proper operation. This has been completely fixed.

#### What Was Fixed:
1. **Pin Constraint Extraction** - Now properly extracts active pins from `constraints.pins`
2. **Wall Constraint Extraction** - Correctly extracts first active wall's normal/offset
3. **Stiffness Computation** - Uses real elastic Hessian blocks instead of fallback values
4. **Barrier Gradient/Hessian** - Added pin and wall contributions to gradient and system matrix
5. **API Improvements** - Made `Stiffness::extract_hessian_block()` public for better accuracy

#### Changes Made:
- `src/core/stiffness.h`: Made `extract_hessian_block()` public
- `src/core/integrator.cpp`: 
  - Added H_block extraction from elastic Hessian
  - Implemented pin/wall gradient contributions
  - Implemented pin/wall Hessian contributions
  - Fixed field name usage (`pin.target_position`)

#### Verification:
```bash
✓ Build: Success (Release mode)
✓ Unit tests: 2/2 passed (BasicTest, BarrierDerivativesTest)
✓ demo_cloth_drape: 200 frames @ 11.6 FPS, no line search failures
✓ Output validation: 201 valid OBJ files with physically plausible geometry
```

See `INTEGRATOR_FIX_SUMMARY.md` for detailed technical documentation.

## Demo Performance

### demo_simple_fall
- **Mesh:** 20×20 grid (400 vertices, 722 triangles)
- **Runtime:** ~2-3 seconds for 100 frames
- **Method:** Forward Euler with basic ground collision
- **Use case:** Quick smoke test, simple physics validation

### demo_cloth_drape
- **Mesh:** 20×20 grid (400 vertices, 722 triangles)  
- **Runtime:** ~17 seconds for 200 frames (11.6 FPS)
- **Method:** Full Newton integrator with β accumulation
- **Constraints:** 2 pinned corners + ground plane (wall constraint)
- **Output:** Cloth drapes from y=0.5 to y≈0.4 (rests on pins/ground)

### demo_cloth_wall
- **Mesh:** 20×20 grid (400 vertices, 722 triangles)
- **Method:** Full Newton integrator
- **Constraints:** Ground plane + vertical wall
- **Use case:** Multi-constraint validation

## Running the Demos

```bash
# Build everything
./build.sh -c -t

# Run individual demos
./build/demos/demo_simple_fall
./build/demos/demo_cloth_drape
./build/demos/demo_cloth_wall

# View results
python3 demos/view_sequence.py output/cloth_drape
# (Controls: space=play/pause, arrows=step, q=quit)
```

## Output Structure

Each demo creates a directory in `output/` with numbered OBJ files:
```
output/
├── simple_fall/
│   ├── frame_0000.obj
│   ├── frame_0001.obj
│   └── ...
├── cloth_drape/
│   ├── frame_0000.obj
│   └── ...
└── cloth_wall/
    ├── frame_0000.obj
    └── ...
```

## Technical Notes

### Constraint System
- **Pins:** Fixed vertices at target positions (barrier method)
- **Walls:** Plane constraints with barrier forces
- **Contacts:** Point-triangle and edge-edge collision detection
- **Line Search:** Extended direction (1.25×) with CCD feasibility checks

### Physics Parameters (defaults)
- `dt = 0.01s` (10ms time step)
- `beta_max = 0.25` (β accumulation limit)
- `contact_gap_max = 0.001m` (1mm barrier threshold)
- `wall_gap = 0.001m` (1mm wall barrier)
- `pcg_tol = 1e-3` (PCG relative tolerance)

### Known Limitations
1. **Single wall support:** Line search uses first active wall only (multi-wall planned)
2. **Wall gradient overhead:** Currently iterates all vertices (can be optimized with BVH)
3. **No friction yet:** Task 10 pending implementation
4. **No strain limiting:** Task 5 pending implementation

## Troubleshooting

### If demo fails to build:
```bash
./build.sh -c  # Clean rebuild
```

### If demo hangs or crashes:
- Check that Eigen is installed (CMake should auto-detect)
- Verify pybind11 is available (for Python bindings)
- Run with smaller mesh or fewer frames

### If output is empty:
- Check console for "Line search failed" messages (should not appear now)
- Verify output directory exists and is writable
- Run unit tests to validate core physics

## Next Development Steps

1. **Blender Integration** (Task 11)
   - Create baking operators
   - Add playback system
   - Integrate with Blender's animation timeline

2. **Friction** (Task 10)
   - Implement tangential forces
   - Add friction barrier energy
   - Test with sliding scenarios

3. **Strain Limiting** (Task 5)
   - SVD-based strain analysis
   - Adaptive strain barrier
   - Prevent excessive stretching

4. **Performance**
   - Cache elastic Hessian between gradient/matrix assembly
   - Optimize wall gradient loop (use BVH to find nearby vertices)
   - Parallel matrix assembly

See `PROJECT_STATUS.md` and `ROADMAP.md` for complete development plan.

