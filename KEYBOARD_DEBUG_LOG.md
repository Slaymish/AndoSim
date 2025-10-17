# Final Keyboard Controls Investigation & Fix

**Date:** October 17, 2025 (Late Night)  
**Issue:** Keyboard controls completely unresponsive  
**Attempts:** 5 different fixes tried  
**Status:** 🔍 Under Investigation

---

## Problem History

User reports keyboard controls (Space, Left, Right) don't work in PyVista viewer. Only Q (quit) responds. Must use Ctrl-C to exit.

---

## Fix Attempts Timeline

### Attempt #1: Lambda with No Arguments
**Theory:** PyVista needs callbacks with no arguments  
**Change:** `lambda: on_timer()`  
**Result:** ❌ TypeError - PyVista passes step argument

### Attempt #2: Lambda Accepting Step
**Theory:** Timer callback needs to accept step argument  
**Change:** `lambda step: on_timer()`  
**Result:** ✅ Timer works, ❌ Keys still broken

### Attempt #3: Separate Key Callbacks
**Theory:** Each key needs individual callback function  
**Change:** Defined on_space(), on_right(), on_left()  
**Result:** ❌ Keys still not responding

### Attempt #4: Lambda Wrappers for Keys
**Theory:** Key callbacks also need lambda wrappers  
**Change:** `plotter.add_key_event(' ', lambda: on_space())`  
**Result:** ❌ Accidentally deleted function definitions!

### Attempt #5: Restore Functions + Debug
**Theory:** Functions missing, need error handling  
**Changes:**
- Restored all callback function definitions
- Added try/except with traceback
- Changed ' ' (space char) to 'space' (string)
- Removed lambda wrappers (PyVista doc says callbacks take no args)
- Added debug print statements

**Current Code:**
```python
def on_space():
    try:
        anim_state['playing'] = not anim_state['playing']
        print(f"{'Playing' if anim_state['playing'] else 'Paused'}")
        # ... update display ...
    except Exception as e:
        print(f"Error in on_space: {e}")
        traceback.print_exc()

plotter.add_key_event('space', on_space)  # 'space' not ' '
plotter.add_key_event('Right', on_right)
plotter.add_key_event('Left', on_left)
```

**Result:** 🔍 Testing needed

---

## Key Investigation Points

### 1. Key Name Format

**Question:** Does PyVista use 'space' or ' ' for spacebar?

Tried variations:
- `' '` (single space character)
- `'space'` (string "space")
- Capital vs lowercase

**Arrow keys:** 'Left', 'Right' (seem standard)

### 2. Callback Requirements

**PyVista docs say:** "The callback function must not have any arguments"

**BUT:** Timer callbacks receive step argument!

**Current understanding:**
- Timer: `callback(step)` - receives argument
- Keys: `callback()` - no arguments

### 3. Registration Timing

Keys registered BEFORE `plotter.show()`:
```python
# 1. Define callbacks
def on_space(): ...

# 2. Register events
plotter.add_key_event('space', on_space)

# 3. Show window
plotter.show()
```

This should be correct order.

### 4. Silent Failures?

Added error handling to detect if callbacks are:
- Being called but failing silently
- Not being called at all

If we see no error messages AND no success messages, callbacks aren't being invoked.

---

## Debugging Strategy

### Test 1: Are Callbacks Being Called?

Run demo and press keys. Look for:
- ✅ "Playing" / "Paused" messages → Callback working!
- ❌ "Error in on_space" → Callback called but failing
- ❌ No messages at all → Callback not registered/called

### Test 2: Simple Test Case

Created `test_keys_simple.py`:
- Minimal PyVista example
- Single sphere
- Simple callbacks
- Tests if ANY keys work at all

### Test 3: Check PyVista Version

```bash
python3 -c "import pyvista; print(pyvista.__version__)"
```

Maybe API changed between versions?

---

## Possible Root Causes

### Theory A: Wrong Key Names
- 'space' vs ' '
- 'Right' vs 'right' vs 'Right_Arrow'
- Case sensitivity

### Theory B: Event Loop Issue
- Interactor not processing events
- Timer consuming all events
- Need to call process_events() manually?

### Theory C: Platform/Backend Issue
- Linux-specific problem
- VTK backend configuration
- Qt/X11 event handling

### Theory D: API Misunderstanding
- Need to use plotter.iren.add_key_event()?
- Different method for interactive vs off-screen?
- Missing initialization step?

---

## Next Steps

1. **Run the current version** - Check if error handling reveals anything

2. **Test simple example** - Does `test_keys_simple.py` work?

3. **Check PyVista examples** - Find working key event code

4. **Try alternative approaches:**
   - Use plotter.iren directly
   - Use enable_terrain_style() (has built-in key handlers)
   - Custom VTK event observer

5. **Consider workarounds:**
   - Click-based controls instead of keyboard
   - Auto-play only (no manual control)
   - External control script

---

## What We Know Works

✅ **Timer callback** - Auto-play animation functional  
✅ **Q key** - Quit works (built-in PyVista)  
✅ **Mouse** - Camera controls work  
✅ **Physics** - Simulation correct  
✅ **Visualization** - Rendering perfect  

---

## What's Broken

❌ **Space key** - Play/pause toggle  
❌ **Arrow keys** - Frame stepping  
❌ **Custom key events** - All non-working  

---

## Files Modified (Latest)

**demos/demo_framework.py** (lines 205-265):
- Added extensive error handling
- Changed ' ' → 'space'
- Removed lambda wrappers
- Added debug print statements

---

## Test Command

```bash
cd demos
./run_showcase.py flag

# Watch console for:
# - "Keyboard controls:" message
# - Any error messages when pressing keys
# - "Playing"/"Paused" messages
```

---

## Status

🔍 **Under active investigation**

The keyboard controls are the LAST remaining issue preventing full functionality. Everything else (physics, visualization, timer, rendering) works perfectly.

This is frustrating because:
- PyVista docs seem straightforward
- Code looks correct
- No error messages
- But keys simply don't respond

**Need to determine:** Are callbacks not being called, or are they being called but failing silently despite error handling?

---

**Next:** User should test current version and report what (if anything) appears in console when pressing keys.
