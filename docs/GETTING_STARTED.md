# AndoSim Getting Started Guide

Welcome to **AndoSim**, a high-accuracy barrier-based physics solver that now runs directly inside Blender. This guide walks you through installation, core concepts, and a first simulation so you can evaluate the add-on in minutes.

---

## 1. Requirements

- **Blender** 3.6 LTS or newer (tested with Blender 4.x)
- **Python** version that matches your Blender build (3.10 for Blender 3.6, 3.13 for Blender 4.1+)
- CMake + a C++17 compiler (only needed if you plan to rebuild the native `ando_barrier_core` module)

> Tip: If you are using Blender from Steam or a custom install, locate the bundled Python interpreter under `<blender>/python/bin` for rebuilds.

---

## 2. Install the Add-on

1. **Clone or download** this repository to a local folder.
2. Build the native module (optional if you use prebuilt wheels):
   ```bash
   ./build.sh
   ```
3. **Install into Blender** using one of the following options:
   - **Symlink** for development:
     ```bash
     ln -s /path/to/AndoSim/blender_addon ~/.config/blender/4.0/scripts/addons/ando_barrier
     ```
   - **Copy** for a standalone install:
     ```bash
     cp -r /path/to/AndoSim/blender_addon ~/.config/blender/4.0/scripts/addons/ando_barrier
     ```
4. Launch Blender → `Edit` → `Preferences` → `Add-ons`
5. Search for **"Ando"** and enable **Physics: Ando Barrier Physics**

You should now see an **Ando Physics** tab in the 3D Viewport sidebar (`N` panel).

---

## 3. First Simulation: Cloth Drop

Follow these steps to validate your install and learn the basic workflow.

1. **Create the cloth mesh**
   ```text
   Shift+A → Mesh → Plane
   Tab (Edit Mode) → Right-click → Subdivide (5 cuts)
   ```
   This yields a 20×20 cloth suitable for real-time preview.

2. **Pin the top edge**
   ```text
   Edit Mode → Select top row of vertices
   N panel → Ando Physics → Contact & Constraints → Add Pin Constraint
   ```

3. **Configure physics**
   - `Main` panel → keep default timestep (`dt = 0.002 s`) and solver limits
   - `Contact & Constraints` → enable **Ground Plane** at height `0.0`
   - `Material` → use the **Cloth** preset (Young's Modulus `1e6 Pa`, Poisson `0.3`, Density `300 kg/m³`, Thickness `0.0005 m`)

4. **Run the preview**
   - `Real-Time Preview` → **Initialize**
   - Press **Play** to start the simulation
   - Use **Show Overlays** in `Debug & Statistics` to visualize contacts and pinned vertices

5. **Bake keyframes (optional)**
   - Once satisfied, run `Bake to Keyframes` in the `Real-Time Preview` panel to convert the sim into standard Blender animation data.

---

## 4. Parameter Cheatsheet

| Panel | Key Controls | What They Do |
| ----- | ------------- | ------------- |
| **Time Integration** | `dt`, `beta_max` | Controls timestep size and barrier accumulation; smaller values increase accuracy. |
| **Newton Solver** | `min_iterations`, `max_iterations` | Sets the bounds for nonlinear solve iterations; raise for stiff materials. |
| **PCG Solver** | `tolerance`, `max_iterations` | Adjust for convergence speed vs. precision in the linear solve. |
| **Material Properties** | `E`, `ν`, `ρ`, `thickness` | Young's modulus, Poisson ratio, density, and shell thickness. |
| **Contact Parameters** | `ccd`, `gap`, `friction` | Enables continuous collision detection and contact friction. |
| **Damping** | `alpha_d`, `beta_d` | Rayleigh damping weights to stabilize oscillations. |

### Common Presets

| Material | Young's Modulus | Poisson Ratio | Density | Thickness |
| -------- | --------------- | ------------- | ------- | --------- |
| Cloth | `1e6 Pa` | `0.3` | `300 kg/m³` | `0.0005 m` |
| Rubber | `5e5 Pa` | `0.49` | `1100 kg/m³` | `0.003 m` |
| Metal Sheet | `5e7 Pa` | `0.33` | `7800 kg/m³` | `0.002 m` |

Use **hot-reload** (changing values while the preview runs) to study stability ranges for your scene.

---

## 5. Troubleshooting

- **Add-on not visible?** Confirm the folder name is `ando_barrier` and that `ando_barrier_core*.so` exists inside.
- **"Core module not loaded" error?** Re-run `./build.sh` with Blender's Python, or copy the prebuilt module from `build/` into `blender_addon`.
- **Simulation won't initialize?** Ensure you selected a mesh object and triangulated geometry; check Blender's System Console for stack traces.
- **Low frame rate?** Reduce mesh resolution, increase timestep slightly, or disable debug overlays.

---

## 6. Next Steps

- Explore the deeper **Real-Time Simulation Quick Start** in [`docs/BLENDER_QUICK_START.md`](./BLENDER_QUICK_START.md) for advanced panels and scripted demos.
- Review [`docs/dev/MILESTONE_ROADMAP.md`](./dev/MILESTONE_ROADMAP.md) to track ongoing feature development.
- Share feedback or questions via the issue tracker—community test scenes help tune upcoming stability work.

Happy simulating!
