# PyVista Visualization Fixes

## Problem
The PyVista window was opening but not responding to user interaction:
- Camera orbit/pan controls not working
- Keyboard controls (space, arrows) not responding  
- Animation not playing
- Only showing first frame

## Root Causes

1. **Status text recreation**: The status text was being recreated on every update using `plotter.add_text()` with the same `name='status'`, which caused issues. Should use `SetText()` on the text actor instead.

2. **Premature rendering**: Called `plotter.render()` in `update_frame()` before `plotter.show()` was called, which doesn't work in PyVista. The plotter must be shown first before rendering.

3. **Initial frame not set**: The mesh geometry wasn't being properly updated to frame 0 before showing the window.

4. **Duplicate status updates**: Key callbacks were calling both `update_frame()` and `set_status()`, causing redundant updates.

## Fixes Applied

### 1. Fixed status text handling
```python
# Create status text actor ONCE
status_actor = plotter.add_text(
    f"Frame 0/{len(self.frames)-1} | Paused",
    position='upper_left',
    font_size=12,
    name='status'
)

def set_status():
    status_text = f"Frame {anim_state['frame']}/{len(self.frames)-1} | {'Playing' if anim_state['playing'] else 'Paused'}"
    # Update existing text actor, don't create new one
    status_actor.SetText(2, status_text)
```

### 2. Conditional rendering
```python
def update_frame(frame_idx, force_render=True):
    """Update mesh to specific frame"""
    positions = self.frames[frame_idx]
    np_positions = np.asarray(positions)
    current_points = mesh.points
    if current_points.shape == np_positions.shape:
        current_points[:] = np_positions
    else:
        mesh.points = np_positions
    mesh.compute_normals(inplace=True)
    mesh.modified()
    set_status()
    # Only render if window is already shown
    if force_render and hasattr(plotter, '_rendering_initialized'):
        plotter.render()
```

### 3. Proper initialization sequence
```python
# Set initial frame (without rendering yet)
update_frame(0, force_render=False)
anim_state['last_update'] = time.time()

# Mark that we're about to show the window
plotter._rendering_initialized = True

# Show (this starts the render loop and blocks until window closes)
plotter.show()
```

### 4. Cleaned up key callbacks
```python
def on_right():
    """Step forward"""
    try:
        anim_state['playing'] = False  # Stop playing first
        anim_state['frame'] = min(anim_state['frame'] + 1, len(self.frames) - 1)
        update_frame(anim_state['frame'])  # This handles status update AND render
        print(f"Frame {anim_state['frame']}/{len(self.frames)-1}")
    except Exception as e:
        print(f"Error in on_right: {e}")
        traceback.print_exc()
```

## Testing

### Quick Test
Run the test script:
```bash
python test_pyvista_fix.py
```

### Using Cached Simulations
All demos now support a `--cached` flag to skip simulation and load pre-existing OBJ files:

```bash
# Run simulation and export OBJ files
python demos/demo_flag_wave.py

# Later, visualize cached results without re-running simulation
python demos/demo_flag_wave.py --cached

# Customize output location
python demos/demo_flag_wave.py --output output/my_test
python demos/demo_flag_wave.py --cached --output output/my_test
```

**Available options:**
- `--cached`: Load from cached OBJ files instead of running simulation
- `--frames N`: Number of frames to simulate (ignored with `--cached`)
- `--output DIR`: Directory for OBJ files (default varies by demo)
- `--dt SECONDS`: Time step size (demo_cascading_curtains only)

**Demos with cached support:**
- `demo_flag_wave.py` (300 frames, output/flag_wave)
- `demo_cascading_curtains.py` (500 frames, output/cascading_curtains)
- `test_pyvista_fix.py` (50 frames, output/quick_test)

Or run any demo:
```bash
python demos/demo_flag_wave.py
```

Expected behavior:
- ✅ Window opens showing frame 0
- ✅ Mouse drag rotates camera (orbit controls)
- ✅ Space bar toggles play/pause
- ✅ Left/Right arrows step through frames
- ✅ Status text updates correctly
- ✅ Animation plays smoothly when playing
- ✅ Q or Escape closes window

## Files Modified
- `demos/demo_framework.py`: Fixed `_visualize_with_pyvista()` method
- `test_pyvista_fix.py`: Created quick test script for verification
