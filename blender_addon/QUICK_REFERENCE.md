# Ando Barrier Physics - Quick Reference Card

## 🚀 Quick Start (5 Minutes)

### Automated Setup
1. Open Blender
2. Text Editor → Open → `blender_addon/create_example_scene.py`
3. Click **"Run Script"**
4. Press **N** → **Ando Physics** tab
5. Click **"Initialize"** → **"Play"**

### Manual Setup
1. Add → Mesh → Plane, subdivide 5 times
2. Edit Mode → Select 2 corners → **"Add Pin Constraint"**
3. **Preset** → "Cloth"
4. Enable **"Ground Plane"**, set height to -5.0
5. Click **"Initialize"** → **"Play"**

---

## 📊 Material Presets

| Preset | Use Case | Young's E | Friction | Behavior |
|--------|----------|-----------|----------|----------|
| **CLOTH** | Fabric, draping | 3.0×10⁵ Pa | 0.4 | Moderate stiffness, natural draping |
| **RUBBER** | Elastic sheets | 2.5×10⁶ Pa | 0.8 | Stretchy, high grip, bouncy |
| **METAL** | Stiff panels | 5.0×10⁸ Pa | 0.3 | Very stiff, minimal deformation |
| **JELLY** | Soft bodies | 5.0×10⁴ Pa | 0.5 | Very soft, large deformations |
| **CUSTOM** | Manual tuning | User-defined | Variable | Full control |

**Tip**: Start with a preset, then tweak individual parameters. Preset auto-switches to "CUSTOM" when edited.

---

## 🎮 Workflow Shortcuts

### Real-Time Preview (Interactive)
1. **N** → Ando Physics → Real-Time Preview
2. **"Initialize"** (once per session)
3. **"Play"** (ESC to pause)
4. **"Step"** (advance one frame)
5. **"Reset Real-Time"** (restart)

### Baking (For Animation)
1. **N** → Ando Physics → Cache & Baking
2. Set frame range (e.g., 1-100)
3. **"Bake Simulation"** (30-60 sec)
4. **Spacebar** to play animation

### Debug Visualization
1. **N** → Ando Physics → Debug & Statistics
2. **"Show Overlays"**
3. **Red** = Contacts, **Blue** = Pins, **Orange** = Edge contacts

---

## 🔧 Key Parameters

### Time Step (Δt)
- **Smaller** (1-2 ms): More stable, slower
- **Larger** (4-5 ms): Faster, may be unstable
- **Default**: 3 ms (good balance)

### Young's Modulus (E)
- **10⁴ Pa**: Jelly (very soft)
- **10⁶ Pa**: Cloth (moderate)
- **10⁸ Pa**: Metal (very stiff)

### Friction (μ)
- **0.1-0.3**: Low friction (ice, metal)
- **0.4-0.6**: Medium (cloth, wood)
- **0.7-0.9**: High (rubber, sticky)

### Contact Gap (ḡ)
- **0.0001-0.0005 m**: Tight (0.1-0.5 mm)
- **0.001-0.002 m**: Loose (1-2 mm)
- **Rule**: 0.1-0.5% of mesh size

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Cloth falls through ground | • Increase Wall Gap to 0.001 m<br>• Enable CCD<br>• Check ground plane height |
| Exploding/unstable | • Reduce time step to 2 ms<br>• Use stiffer material (Metal)<br>• Increase Max Newton Steps to 12 |
| Too slow | • Reduce mesh density (3-4 subdivisions)<br>• Increase time step to 4 ms<br>• Reduce frame count |
| No collision | • Check Enable CCD is ON<br>• Verify ground plane height<br>• Increase Contact Gap Max |
| Pins not working | • Use "Add Pin Constraint" in Edit Mode<br>• Check "ando_pins" vertex group exists<br>• Weight must be > 0.5 |

---

## 📈 Performance Guide

### Target Metrics (17×17 cloth, ~289 vertices)
- **Step Time**: 5-15 ms ✅
- **Physics FPS**: 60-200 ✅
- **Contacts on ground**: 10-50 typical

### Optimization
1. **Mesh**: Start small (10×10), scale up if needed
2. **Timestep**: Larger = faster but less stable
3. **Newton Steps**: 2-4 for speed, 8-12 for accuracy
4. **PCG Tolerance**: 1e-3 (default) is good balance

---

## 🎨 Color Coding (Debug Overlay)

| Color | Element | Meaning |
|-------|---------|---------|
| 🔴 Red | Contacts | Point-triangle collision |
| 🟠 Orange | Contacts | Edge-edge collision |
| 🟡 Yellow | Contacts | Wall collision |
| 🔵 Blue | Pins | Fixed constraint |
| 🟢 Green | Normals | Contact direction (scaled) |

---

## 💾 Export Workflows

### To Alembic
1. File → Export → Alembic (.abc)
2. Check "Apply Modifiers"
3. Use in Maya, Houdini, C4D

### To OBJ Sequence
```python
# Run in Blender Console after baking
import bpy
obj = bpy.context.active_object
for i, key in enumerate(obj.data.shape_keys.key_blocks):
    if key.name.startswith('frame_'):
        key.value = 1.0
        filepath = f"/tmp/cloth_{i:04d}.obj"
        bpy.ops.export_scene.obj(filepath=filepath, use_selection=True)
        key.value = 0.0
```

---

## 🔢 Parameter Units

| Parameter | Unit | Example |
|-----------|------|---------|
| Young's Modulus (E) | Pascal (Pa) | 3.0×10⁵ |
| Density (ρ) | kg/m³ | 1100 |
| Thickness | meters | 0.003 (3mm) |
| Time Step (Δt) | milliseconds | 3.0 |
| Contact Gap (ḡ) | meters | 0.0005 (0.5mm) |
| Friction (μ) | unitless | 0.4 |

---

## 📚 Additional Resources

- **Full Guide**: `blender_addon/EXAMPLE_SCENE_GUIDE.md`
- **Quick Start**: `BLENDER_QUICK_START.md`
- **Build Instructions**: `BUILD.md`
- **Paper Reference**: "A Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness" (Ando 2024)

---

## ⚡ Keyboard Shortcuts (Blender)

| Key | Action |
|-----|--------|
| **N** | Toggle sidebar (Ando Physics panel) |
| **Tab** | Edit/Object mode toggle |
| **Spacebar** | Play/pause animation |
| **Alt+A** | Deselect all |
| **ESC** | Stop modal operator (e.g., real-time play) |

---

## 🎯 Common Workflows

### Simple Cloth Drop
1. Preset: **CLOTH**
2. Pin: Top 2 corners
3. Ground: -5.0
4. Bake: 50 frames

### Bouncy Rubber Sheet
1. Preset: **RUBBER**
2. Pin: Top 4 corners
3. Ground: -3.0
4. Initial velocity: Push downward

### Stiff Metal Panel
1. Preset: **METAL**
2. Pin: One edge
3. No ground (bending test)
4. Watch minimal deformation

### Soft Jelly Block
1. Preset: **JELLY**
2. No pins (free fall)
3. Ground: 0.0
4. Watch large deformations

---

**Version**: 1.0.0 | **Updated**: October 19, 2025
