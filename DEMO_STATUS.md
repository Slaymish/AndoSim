# Demo Status Report

## Current Status

### ✅ Working: Simple Physics
- Basic gravity simulation works correctly
- `demo_simple_fall` shows cloth falling from y=1.0 to y=0.0
- Mesh generation fixed: cloth now horizontal in XZ plane (Y is up)
- OBJ export working correctly

### ❌ Not Working: Full Integrator
- `demo_cloth_drape` produces no movement - cloth stays frozen
- Line search consistently fails (returns α=0)
- Issue: Integrator → LineSearch interface is incomplete

## Root Cause

The `Integrator::inner_newton_step()` function has TODO placeholders that prevent proper operation:

```cpp
// Line search for feasible α
Real alpha = LineSearch::search(
    mesh, state, direction, contacts,
    std::vector<Pin>(),  // TODO: extract from constraints
    Vec3(0, 0, 1), 0.0,  // TODO: extract wall from constraints
    1.25  // Extended direction
);
```

**Problems:**
1. Pins are passed as empty vector (should extract from `constraints.pins`)
2. Wall parameters are hardcoded (should extract from `constraints.walls`)
3. Line search can't enforce constraints it doesn't know about
4. Result: Every step is rejected as infeasible

## Required Fixes

### 1. Extract Pins from Constraints

```cpp
// Convert PinConstraint to Pin for LineSearch
std::vector<Pin> pins_for_search;
for (const auto& pin : constraints.pins) {
    if (pin.active) {
        pins_for_search.push_back(pin);
    }
}
```

### 2. Extract Wall from Constraints

```cpp
// Get first active wall (currently support single wall)
Vec3 wall_normal(0, 0, 1);
Real wall_offset = 0.0;
bool has_wall = false;

for (const auto& wall : constraints.walls) {
    if (wall.active) {
        wall_normal = wall.normal;
        wall_offset = wall.offset;
        has_wall = true;
        break;  // Use first wall for now
    }
}

// If no wall, pass zero normal to disable wall checks
if (!has_wall) {
    wall_normal = Vec3(0, 0, 0);
}
```

### 3. Fix constraints.h Pin Type

Current issue: `LineSearch` expects `Pin` but `Constraints` uses `PinConstraint`.

**Solution**: Already added `using Pin = PinConstraint;` alias in constraints.h

## Workaround for Now

Use `demo_simple_fall` to demonstrate physics:
```bash
./build/demos/demo_simple_fall
# Creates output/simple_fall/frame_*.obj
```

This bypasses the integrator and uses simple forward Euler with basic ground collision.

## Next Steps

1. **Fix integrator constraint extraction** (high priority)
   - Extract pins from constraints
   - Extract wall parameters from constraints
   - Pass to line search properly

2. **Test with full integrator** (after fix)
   - Run `demo_cloth_drape` again
   - Should see cloth falling and draping
   - Line search should succeed

3. **Add more constraint types** (future)
   - Support multiple walls simultaneously
   - Add ceiling/box constraints
   - Proper multi-constraint line search

## Files to Modify

- `src/core/integrator.cpp` lines 115-125: Fix LineSearch::search() call
- Add helper functions to extract constraints for line search

## Test Plan

1. Fix integrator
2. Rebuild: `./build.sh`
3. Clean output: `rm -rf output/cloth_drape`
4. Run: `./build/demos/demo_cloth_drape`
5. Verify: Line search should not fail
6. Check output: Frames should show cloth falling

## Current Output Example

**Before fix (broken):**
```
Frame 0: vertices at y=0.5
Frame 50: vertices at y=0.5  (no movement!)
Line search failed, stopping β accumulation
```

**After fix (expected):**
```
Frame 0: vertices at y=0.5
Frame 50: vertices at y=0.3  (falling!)
Frame 100: vertices at y=0.0  (on ground)
```

## Alternative: Simpler Demo

If integrator proves too complex, we can create intermediate demos:
1. ✅ `demo_simple_fall` - Works now (forward Euler)
2. `demo_implicit_fall` - Single Newton step per frame
3. `demo_full_physics` - Full β accumulation (current goal)

This allows progressive testing of each component.
