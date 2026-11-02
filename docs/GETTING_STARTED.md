# AndoSim Getting Started Guide

Welcome to **AndoSim**, a high-accuracy barrier-based physics solver that now runs directly inside Blender. This guide walks you through installation, core concepts, and a first simulation so you can evaluate the add-on in minutes.

---

## 1. Requirements

- **Blender** 3.6 LTS or newer (tested with Blender 4.x)
- **Python** version that matches your Blender build (see compatibility table below)
- CMake + a C++17 compiler (only needed if you plan to rebuild the native `ando_barrier_core` module)
- *(Optional for CUDA backend)* NVIDIA GPU drivers with `nvidia-smi` available on your PATH to run the bundled PPF contact solver.

> Tip: If you are using Blender from Steam or a custom install, locate the bundled Python interpreter under `<blender>/python/bin` for rebuilds.

### Prebuilt Module Compatibility

Release binaries built against **CPython 3.11** require the **same Python major
and minor version** in Blender. “Python 3.11+” is not sufficient: a normal
`cp311` extension cannot be loaded by Python 3.12 or 3.13. Matching Python is
necessary but does not guarantee compatibility; the binary must also match the
operating system, CPU architecture, and required native libraries.

Check the actual Blender runtime in its Python Console:

```python
import sys, platform
print(sys.version)
print(platform.system(), platform.machine())
```

For example, Blender running Python 3.13 needs a module rebuilt for Python 3.13;
a Python 3.11 release binary will not work. A “compiled extension required”
message means the active module lacks the native simulation API. It does not
by itself establish an ABI mismatch or a Windows-specific failure.

Rebuild using the target Blender installation's bundled Python executable:

```bash
./build.sh --python /absolute/path/to/blender/python/bin/python3.13
```

Use the actual executable path and version from your installation. For Windows,
use the CMake build instructions in the README with
`-DPython3_EXECUTABLE="C:/path/to/Blender/python/bin/python.exe"`. Configure in a
fresh build directory when switching interpreters, and confirm CMake reports the
target Python version and development files. Copy the resulting `.so` (Linux or
macOS) or `.pyd` (Windows) into `blender_addon/`, then restart Blender. Renaming a
`cp311` binary does not change its ABI.

The bundled Python fallback allows the add-on to load without a matching native
binary, but baking and real-time simulation require the compiled core. Keep both
`ando_barrier_core.py` and `_core_fallback.py` when copying the add-on. Background
Blender does not open the manual core-selection dialog.

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

### Pick a solver backend

The add-on now ships with two interchangeable solver backends:

1. **Ando Core (default).** Pure CPU implementation that mirrors the SIGGRAPH 2024 paper. This is the right choice for offline baking, determinism, and machines without NVIDIA hardware.
2. **PPF Contact Solver.** CUDA implementation pulled in as the `extern/ppf-contact-solver` submodule. Sync it once with:
   ```bash
   git submodule update --init --recursive extern/ppf-contact-solver
   ```

After enabling the add-on, open `Edit → Preferences → Add-ons → Ando Barrier Physics` and switch the **Solver backend** dropdown:

- Pick **Ando Core** to continue using the compiled module inside `blender_addon/`.
- Pick **PPF Contact Solver** to run the CUDA backend. The preferences panel reports whether `nvidia-smi` was detected and the frontend libraries imported correctly. If something is missing (drivers, toolkit, etc.), fix the warning before launching a session.

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
   - **Ando Core backend:** `Real-Time Preview` → **Initialize**, then press **Play** to start the simulation. Use **Show Overlays** in `Debug & Statistics` to visualize contacts and pinned vertices.
   - **PPF backend:** `Real-Time Preview` → **Start PPF Session**. The solver runs out-of-process (CUDA), streaming `vert_*.bin` files back into Blender. When finished—or if you want to abort—click **Terminate Session** in the same panel.

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

- **Add-on not visible?** Confirm the folder name is `ando_barrier` and that it contains `__init__.py` and both bundled fallback files.
- **"Core module not loaded" error?** Check the System Console for import errors and confirm both fallback files are present. For native simulation, rebuild with `./build.sh --python /path/to/blenders/python` and copy the matching binary into `blender_addon`.
- **PPF session cancels immediately?** Make sure `nvidia-smi` works from a terminal and that the `extern/ppf-contact-solver` submodule is synced. The add-on preferences panel echoes the exact status message detected at startup.
- **Simulation won't initialize?** Ensure you selected a mesh object and triangulated geometry; check Blender's System Console for stack traces.
- **Low frame rate?** Reduce mesh resolution, increase timestep slightly, or disable debug overlays.

---

## 6. Next Steps

- Explore the deeper **Real-Time Simulation Quick Start** in [`docs/BLENDER_QUICK_START.md`](./BLENDER_QUICK_START.md) for advanced panels and scripted demos.
- Review [`docs/dev/MILESTONE_ROADMAP.md`](./dev/MILESTONE_ROADMAP.md) to track ongoing feature development.
- Share feedback or questions via the issue tracker—community test scenes help tune upcoming stability work.

Happy simulating!
