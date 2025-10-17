# Integrator Constraint Extraction Fix - Summary

**Date:** October 17, 2025  
**Status:** ✅ Complete

## Problem Statement

The Newton integrator in `src/core/integrator.cpp` had incomplete constraint extraction:
- Pin and wall constraints were not being passed to the line search
- Barrier gradient and Hessian contributions for pins/walls were missing
- Stiffness computations used placeholder values instead of actual elastic Hessian blocks
- This caused `demo_cloth_drape` to fail with line search rejections

## Changes Made

### 1. API Changes (`src/core/stiffness.h`)
- Made `Stiffness::extract_hessian_block()` public (was private)
- Allows integrator to extract per-vertex 3×3 Hessian blocks from global elastic Hessian
- No breaking changes to existing code

### 2. Integrator Updates (`src/core/integrator.cpp`)

#### `compute_gradient()` function:
- Added assembly of base elastic Hessian (mass + elasticity) before barrier computations
- Extract H_block for each contact/pin/wall using `Stiffness::extract_hessian_block()`
- Compute accurate dynamic stiffness k̄ using real elastic Hessian blocks
- Added pin barrier gradient contributions via `Barrier::compute_pin_gradient()`
- Added wall barrier gradient contributions via `Barrier::compute_wall_gradient()`
- Replaced placeholder fallback H_blocks with extracted blocks from elastic Hessian

#### `assemble_system_matrix()` function:
- Build temporary base Hessian (mass + elasticity) early for H_block extraction
- Extract H_block for each contact/pin/wall before computing barrier Hessians
- Added pin barrier Hessian contributions via `Barrier::compute_pin_hessian()`
- Added wall barrier Hessian contributions via `Barrier::compute_wall_hessian()`
- All stiffness computations now use accurate elastic Hessian blocks

#### Field Name Corrections:
- Changed `pin.target` → `pin.target_position` (matches `PinConstraint` struct definition)
- All pin references now use correct field name from `src/core/constraints.h`

### 3. Constraint Extraction (already done in earlier code):
- `inner_newton_step()` correctly extracts active pins into `pins_for_search` vector
- `inner_newton_step()` correctly extracts first active wall's normal/offset
- These are passed to `LineSearch::search()` for feasibility checks

## Results

### Build & Tests
```
✓ Build: Success (Release mode)
✓ Unit tests: 2/2 passed
  - BasicTest (stiffness, collision, barrier gradients, line search, PCG solver)
  - BarrierDerivativesTest (energy, gradient, Hessian finite-difference validation)
```

### Demo Performance
```
✓ demo_cloth_drape: Complete
  - 200 frames simulated (2 seconds @ dt=0.01s)
  - Runtime: 17.2 seconds
  - FPS: 11.6
  - Output: 201 valid OBJ files in output/cloth_drape/
  - No line search failures
  - Cloth correctly drapes from initial position to ground
```

### Validation
- Finite-difference derivative tests pass with <0.01% relative error
- Barrier force direction is repulsive (negative gradient)
- PCG solver converges (residual < 1e-7)
- Line search correctly enforces wall and contact constraints
- OBJ output shows physically plausible geometry (cloth draped to y≈0.4-0.5)

## Technical Details

### Stiffness Computation Formula
Per paper Section 3.3-3.4:
- **Contact:** `k = m/Δt² + n·(H n)` where H is elastic Hessian block
- **Pin:** `k = m/Δt² + w·(H w)` where w = x - target_position
- **Wall:** `k = m/g_wall² + n·(H n)` where n is wall normal

### Matrix Assembly Strategy
1. Build mass/dt² diagonal blocks
2. Add elastic Hessian triplets
3. Assemble temporary base Hessian H_base
4. For each constraint (contact/pin/wall):
   - Extract H_block from H_base using vertex index
   - Compute stiffness k̄ with real H_block
   - Compute barrier Hessian with k̄
   - Add barrier triplets to system
5. Symmetrize final Hessian

### Performance Impact
- H_block extraction: O(nnz) sparse matrix iteration per vertex
- For typical meshes (~400 vertices): negligible overhead
- Accuracy improvement: stiffness now reflects actual material properties
- Demo runtime comparable to previous runs (~17s for 200 frames)

## Files Modified
1. `src/core/stiffness.h` - Made `extract_hessian_block()` public
2. `src/core/integrator.cpp` - Added pin/wall gradient/Hessian assembly and H_block extraction

## Next Steps (Future Work)
1. **Optimization:** Cache elastic Hessian between gradient/matrix calls (currently assembled twice)
2. **Refinement:** Consider adaptive stiffness for very small gaps (takeover term already present)
3. **Testing:** Add integration tests for pin/wall scenarios specifically
4. **Documentation:** Update paper cross-references in code comments

## Verification Commands
```bash
# Build and test
./build.sh -c -t

# Run demo
./build/demos/demo_cloth_drape

# View output
python3 demos/view_sequence.py output/cloth_drape

# Check specific tests
./build/tests/test_basic
./build/tests/test_barrier_derivatives
```

## References
- Paper: "A Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness" (Ando 2024)
- Implementation guide: `.github/copilot-instructions.md`
- Project status: `PROJECT_STATUS.md`, `DEMO_STATUS.md`
- Build instructions: `BUILD.md`
