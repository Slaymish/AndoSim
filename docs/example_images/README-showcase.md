# Native sphere contact follow-up

The suspended-sail record below is retained as historical evidence. The new `--scene sphere` preset drops a free teal/copper sheet over a **registered native
rigid collider**. Its 16-frame Blender bake is rendered at 960×540 to
`docs/example_images/sphere-contact.gif` (22 GIF frames at 12 fps including a
half-second hold on the final solver frame). The README and portfolio story use
that same GIF. The earlier `showcase` preset and GIF remain as a contact-free
comparison.
The sphere has 162 vertices / 320 flat triangles; its rendered geometry matches
its collision mesh. The cloth has 289 vertices / 512 solver triangles, no pins,
no wind and no post-bake vertex animation. A slight initial tilt and corrugation
are rest geometry. The only animation is the addon's native bake shape keys.

## Root cause and strict red-green evidence

Each fix followed a failing native reproducer:

| Test | Red result | Change |
| --- | --- | --- |
| `RigidSphereCrossingTest` | Patch crossed from z=1.2 to z=0.2 through a unit octahedral sphere | Swept rigid checks include candidates outside the current barrier range; final test strengthens speed to cross the whole sphere |
| `RigidSphereFaceCrossingTest` | Sphere pierced a large cloth face with every cloth vertex outside | Reverse rigid-vertex/cloth-face detection and CCD; barycentric cloth support |
| `RigidEdgeCrossingTest` | No contact; line search returned alpha=1 across perpendicular edges | Interior edge/edge contacts and swept edge checks; red alpha=1, green alpha below 0.1 |
| `ElasticHessianPSDTest` | Relative uniform-translation error 0.799097 | Preserve the whole PSD membrane approximation and its translation nullspace; remove independent off-diagonal SPD projection |
| `PCGSmallSPDTest` | Identity matrix, RHS=1e-9: false nonconvergence, relative residual=1 | Replace absolute pAp cutoff with finite/positive curvature checks and double-precision dot products |

`RigidSphereHoldingTest` additionally checks one second (500 native steps at
2 ms) of gravity, contact and frictionless sliding against the octahedral sphere.
It requires positive exterior clearance and at least 100 contact steps. It does
not require a tiny free patch to remain balanced on the pole forever.

The old unsigned distance is retained for exterior mesh proximity. Its normal
flips after tunneling; changing its sign alone would not repair missed events.
The line search previously ignored rigid contacts entirely, and its existing
10-sample deformable CCD was not a conservative rigid test. New rigid CCD uses
conservative distance advancement with a Lipschitz speed bound for each feature
pair and a 10 micrometre clearance. Contacts refresh at every Newton iterate.
Reverse contacts distribute normal gradients/Hessians over the cloth support;
endpoint edge minima use the existing vertex/face contacts to avoid duplicate
lateral forces. No force-direction regression was waived.

The elastic matrix in the original small test was PSD; the PCG warning did not
prove indefiniteness. Its absolute cutoff also rejected valid tiny SPD systems.
The repaired elastic Hessian remains an approximation to the moving-frame
energy gradient, rather than an exact constitutive Hessian.

## Reproduce the final bounded bake

From this repository, using its existing Python 3.13 build configuration:

```bash
cmake --build build -j 4
ctest --test-dir build --output-on-failure
mkdir -p scratch/sphere-followup
blender -b --factory-startup --python-exit-code 1 \
  --python docs/example_images/render_demo.py -- \
  --scene sphere --frames 16 --dt 2 --gap .08 --render-every 8 \
  --res 800 640 --samples 32 --cam-dir .9 -1 .65 \
  --core build/ando_barrier_core.cpython-313-x86_64-linux-gnu.so \
  --out scratch/sphere-followup/final16 \
  > scratch/sphere-followup/final16.log 2>&1
```

The explicit binary is preloaded before addon import, and its actual `__file__`
is checked. Otherwise CPython can reuse the previously imported installed
extension even when another path is requested. No installed binary is replaced.
For geometry-only validation, add `--check` and choose a new output directory.
Use a matching extension suffix if reproducing with another Python ABI.

The script observes each native step without changing state. It rejects mesh
intersections and cloth vertices inside the convex sphere. For disjoint meshes,
it measures minimum vertex/face distances in both directions and all edge/edge
segment distances, including cloth triangle interiors. It checks all native
step snapshots, rather than just the rendered keys. The separately printed
analytic enclosing-sphere bound can be negative because the actual collider is
faceted; it is not substituted for the actual mesh clearance. Collider surface
motion is measured, bounded by 0.1 mm, and must be smaller than the measured
clearance so the displayed initial collider also remains separate. Camera,
finite-coordinate, complete-key and temporal-motion checks still apply.

Material: E=2,000 Pa, thickness=1 mm, density=1,100 kg/m³, damping=0.2/s;
rigid density=20,000 kg/m³, gravity=9.81 m/s², 24 fps. Contact range is a deliberately
large 8 cm for this coarse mesh; timestep cap is 2 ms. These are demonstration
parameters, not textile calibration. Friction, restitution, strain limiting and
ground collision are disabled. This validates the bounded sphere case, not
arbitrary moving rigid bodies, self-contact, long-term stability or material
accuracy. Rigid geometry is frozen during each deformable solve; the separate
rigid integration is not a coupled moving-body CCD solve.

## Recorded follow-up evidence

Native build and all **26 CTest tests passed**, including the six tests named
above and every pre-existing test. Exact build/test output is preserved in
`scratch/sphere-followup/ando-final-build.log` and `ando-final-tests.log`.
Failed Blender explorations remain in the same directory. The 20-frame
vertex-only attempt and 12-frame reverse-only attempt failed clearance checks;
no images were rendered from them. The first fully checked 12-frame edge-contact
run passed across 484 native steps with minimum actual mesh clearance
0.005408522 m and peak temporal motion 1.195238 m. Later final-scene results are
recorded below.


Final run (`final16.log`, Blender 5.1.0, CPU Cycles) exited **0**:

```text
native steps:                    866
maximum sampled rigid contacts: 14
actual mesh minimum clearance:  0.005260944 m (every native step)
maximum rigid surface motion:   0.000029663 m
static displayed-mesh bound:    0.005231281 m
bake duration:                   81.1 s
keys:                           16, finite, full range 1:16
peak temporal displacement:     2.152323 m
camera coverage:                PASS
PCG nonconvergence warnings:     0
PCG diagnostic warnings:         0
line-search failures:            0
```

The static displayed-mesh bound subtracts the maximum native rigid surface
motion from the native mesh clearance. The separate analytic sphere-envelope
bound is -0.001790625 m; the sphere's flat facets lie inside that envelope.
No smoothing or render-only substitute sphere hides this distinction.

Files retained under `scratch/sphere-followup/final16/`:

- `f000.png`, `f001.png`, `f002.png`: frames 1, 9, 16, visually inspected.
- `sphere-contact.blend`: the actual baked scene, saved on frame 16; scrub 1–16.
- `collision_metrics.npz`: every baked key's coordinates, basis and measured
  native-step aggregates; this file is evidence, not an animation input.

The 16-frame sheet falls and wraps over the collider, leaving a supported canopy
as the free skirt continues down. This is contact-driven motion, not a suspended
curtain. The native stress face-crossing test deliberately attempts an extreme
400 m/s step and reports a line-search stop at its safe limit; that expected
stress-test diagnostic is separate from the warning-free bounded Blender run.
For exact individual test commands and values, see
`scratch/sphere-followup/focused-native-tests.log`, produced with:

```bash
ctest --test-dir build -V -R 'RigidSphere|RigidEdge|ElasticHessianPSD|PCGSmallSPD'
```

The pre-existing GIF was not opened for writing. Its SHA-256 remains
`b6c2501c860882a1b434652ec8adb7c396cbb4037276845b32aa8077c111fcf1`.
There were no commits, pushes, installed-extension replacements or changes to
other repositories.

---

# Suspended sail — solver showcase

`render_demo.py --scene showcase` releases a tapered, corrugated elastic sheet
55° from vertical. Its 29 upper-edge vertices stay pinned to a brass display
rail; gravity pulls the free sheet down, stretching and bending the upper region
while the lower corrugations catch the light. Teal fabric, copper stripes, a dark
stage and grazing studio lights make the changing silhouette legible.

This is a **short elastic membrane release**, not a validated silk model or a
settled drape. The mesh has 725 vertices and 1,344 solver triangles. The initial
corrugations are rest geometry, created before baking. All subsequent vertex
motion comes from `bpy.ops.ando.bake_simulation()` and its `frame_0001` …
`frame_0012` shape keys. The script never moves the mesh after baking, adds wind,
or animates the pins, camera, materials or lights.

Material: E = 1,200 Pa, Poisson ratio 0.35, density 1,100 kg/m³, thickness 1 mm;
velocity damping 0.005. These deliberately soft parameters produce visible
elastic deformation; they are not measured textile parameters. Gravity is the
addon's Z-down 9.81 m/s². The scene and addon bake use 24 fps. `--dt` is a timestep
**cap in milliseconds**; the addon can take smaller steps according to speed and
contact gap. Frame 1 is already one simulated interval after release.

## Reproduce

Run from the repository root with a Blender installation that can import this
repo's built `ando_barrier_core` extension through `blender_addon`. The run below
used Blender 5.1.0, CPU Cycles, factory startup. No installed addon preferences
are needed; the script registers the repository addon.

Check the actual bake without rendering:

```bash
blender -b --factory-startup --python-exit-code 1 \
  --python docs/example_images/render_demo.py -- \
  --scene showcase --frames 12 --dt 0.5 --check \
  --out scratch/showcase/final-check \
  > scratch/showcase/final-check.log 2>&1
```

Create `scratch/showcase` first (`mkdir -p scratch/showcase`) before redirecting
logs. This is a real bake, not a dry run. `--check` returns only after validation.
`--python-exit-code 1` makes Python failures visible to shell automation.

The inspected preview command:

```bash
blender -b --factory-startup --python-exit-code 1 \
  --python docs/example_images/render_demo.py -- \
  --scene showcase --frames 12 --dt 0.5 --render-every 5 \
  --res 640 520 --samples 24 --out scratch/showcase/final12 \
  > scratch/showcase/final12.log 2>&1
```

This writes `f000.png` … `f003.png` for simulation frames 1, 6, 11, 12. The final
frame is always included. For every baked frame, use `--render-every 1`; for a
larger still sequence use `--res 1200 1000 --samples 96` with the same 12-frame
bake. Higher-quality rendering settings are instructions, not verified outputs.
Do not lengthen the bake expecting a stable resting state.

The pre-existing `--margin 1.18` and `--cam-dir 0.52 -1.0 0.10` controls remain.
A static perspective camera fits the complete baked trajectory using the actual
image aspect ratio. `--margin` gives extra framing room. Camera coverage is
validated for every vertex of every baked key before any image is written.

## Checks and limits

The script raises an error before rendering on failed or missing bakes,
incomplete frame keys, nonfinite coordinates, less than 1 cm of temporal motion,
or camera clipping. It explicitly sets scene range 1–12 and 24 fps. For showcase
it also rejects proximity within 5 cm of the decorative floor and certifies a
non-self-intersecting surface at **each baked integer frame**: all projected XZ
triangles must retain a common strict orientation, and their disk boundary must
be simple. This conservative graph test can reject valid folded surfaces. It
checks geometry, not the correctness of a contact solver. It does not certify
continuous substep trajectories or interpolated subframes.

There are **no rigid collision bodies** in this scene. The rail and floor are
render-only objects; the ground constraint and friction are disabled. The scene
avoids contact rather than demonstrating reliable rigid or self contact.

Exploration exposed solver limitations. The first, stiffer 36-frame attempt at
1 ms logged NaN residuals and was terminated. An earlier flat 24-frame variant
finished baking but failed camera validation; it is not the delivered scene.
The final soft release still emits `PCG: pAp near zero, matrix may not be SPD`
and `PCG did not converge in Newton iteration 0` warnings. Finite moving keys
and nonintersection do **not** prove Newton convergence, energy conservation,
material accuracy, or long-term stability. No claim is made about collision
reliability, physical calibration, long bakes, other scene presets or other
Blender versions.

## Recorded run

Both commands above exited **0**. The standalone `--check` produced:

```text
[render] bake={'FINISHED'} 55.2s
[render] nonintersection=PASS (XZ graph certificate, baked frames only) floor_clearance=1.193463m
[render] framed centre=(0.0, -1.14, -0.1) radius=2.11 distance=6.50
[render] PASS keys=12 finite=True range=1:12 peak_from_basis=1.230021m temporal_peak=1.221398m rms_last=1.150918m camera=PASS
```

The 640×520 preview bake took 49.8 s and reported the same displacement and
clearance values, with camera distance 6.27 m because its aspect ratio differs.
It rendered and saved four PNGs at frames 1, 6, 11 and 12. All four were opened
and visually inspected: the pinned edge stays at the rail, the free hem drops,
the upper sheet bends and stretches, and the lower corrugations remain visible.
The images have no visible crossings or cropping. Camera coverage and finite
coordinates were checked across all 12 keys, not just these four images.

Peak temporal displacement is the maximum Euclidean distance of any vertex
from its frame-1 position over all baked frames. `rms_last` is the root mean
square vertex distance from frame 1 at the final frame. `peak_from_basis`
measures distance from the undeformed rest mesh. These measure movement, not
solver accuracy. The check log includes 740 PCG nonconvergence warnings; they
are retained rather than suppressed. No NaN residual messages occurred in that
final check log.

Local evidence (untracked, not distributed source assets):

- `scratch/showcase/final-check.log`: standalone bake and checks.
- `scratch/showcase/final12.log`: bake, checks and render output.
- `scratch/showcase/final12/f000.png` … `f003.png`: inspected final previews.
- Earlier attempts and their logs remain under `scratch/showcase/` for comparison.

Only `render_demo.py` and this README are source changes. No commits or solver
changes are part of this showcase.
