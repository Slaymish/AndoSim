# AndoSim: Ando Barrier Physics

![AndoSim Logo](docs/example_images/teaser-image.jpg)

AndoSim is a Blender add-on that ports the SIGGRAPH 2024 method from ["A Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness"](https://doi.org/10.1145/3687908) into day-to-day cloth and shell work. The solver matches the paper’s barrier formulation, supports live viewport playback, and exposes all the knobs you’d expect inside Blender.

### Why it stands out
- Real-time cloth/shell simulation that actually stays stable when you pile up contacts, thanks to the cubic barrier with dynamic stiffness.
- Pin constraints, ground contacts, strain limiting, and experimental friction are all wired in and visible through Blender overlays.
- C++ core (Eigen + pybind11) keeps the math fast and faithful to the paper; the Python layer is just orchestration and UI.
- Optional CUDA backend via the PPF contact solver submodule for tackling dense contact stacks on NVIDIA GPUs.
- Rich debug tools: per-contact overlays, solver stats, scripted demos, and validation scenes.

### Try it
- Artists and tech animators: follow [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md). It walks through installing the add-on, linking the core module, and running your first cloth drop in the viewport.
- Developers: prerequisites are CMake, Eigen3, and pybind11. From the project root run `./build.sh` (tests: `./build.sh -t`). This compiles the C++ extension into `blender_addon/` so Blender can import it.
- Need binaries fast? CI artifacts target Blender releases that ship Python 3.11 (4.1–4.5). Older Blender versions require rebuilding with the bundled interpreter—notes are in the getting started guide.
- Trying the CUDA backend? Make sure `extern/ppf-contact-solver` is pulled via `git submodule update --init --recursive`, then pick **PPF Contact Solver** in the add-on preferences. The realtime panel will guide you through launching a streaming session.

### Want to dig deeper?
- [docs/BLENDER_QUICK_START.md](docs/BLENDER_QUICK_START.md) summarizes the add-on panels, realtime playback workflow, and common troubleshooting steps.
- `docs/dev/PROJECT_SPEC.md` and `docs/dev/MILESTONE_ROADMAP.md` trace every decision back to the paper and outline what’s coming next.
- Standalone demos live in `demos/`, and `tests/` holds the C++ unit suite that guards the solver math.

### Join in
- File bugs or feature requests on GitHub: `https://github.com/Slaymish/AndoSim`
- Reach out on Discord (Slaymish) or email (hamishapps@gmail.com) if you want to contribute, pair on a feature, or share a scene.
- Fresh perspectives are especially welcome on friction, export tooling, and performance tuning: there’s plenty of room to shape where AndoSim goes next.
