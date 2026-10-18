# Geometry and uncertainty specification

## Coordinate system and inputs

The scene is a two-dimensional closed rectangular search domain. Coordinates are arbitrary local metres, with positive x to the right and positive y upwards. They have no geographic datum or latitude/longitude interpretation. All landmark positions and correspondences are supplied exactly. There is no terrain occlusion, elevation, lens distortion, focal-length estimation or landmark-identification model.

Input files contain `id`, `title`, `split`, `bounds: [xmin, ymin, xmax, ymax]`, labelled `landmarks`, `observations`, `default_observations` and noise metadata. A landmark has `id`, `x`, `y` and `label`. An observation has an ID, a kind, a list of landmark IDs, a value in degrees and a nonnegative tolerance in degrees. The solver validates IDs, coordinates and finite angles. Supported coordinates are within ±1,000,000 m; domain sides range from 0.001 to 1,000,000 m. Tolerances range from 0° to 180°.

An answer key is a separate file with the same ID under `data/truth/`. It stores the source camera, noiseless observation values, noise draws and intentional-corruption annotations. The generator does not import the solver. The solver does not read answer keys. Teaching annotations are assistant-authored and are not human validation.

## Observation semantics

A **bearing** is the counterclockwise angle from positive x to the ray from camera to landmark. This is a calibrated world-frame bearing, not the usual clockwise-from-north compass convention. The camera orientation is assumed known. Circular residual is `abs(((predicted - observed + 180) % 360) - 180)`. An observation holds when its residual is at most its tolerance.

An **angle** is the unsigned smaller angle, in [0°,180°], between the two camera-to-landmark rays. The residual is the absolute difference from its observed angle. Camera orientation cancels. The landmark pair is unordered; the two landmark IDs must differ. A camera coinciding with any used landmark is undefined and excluded. Unused landmarks impose no singularity constraint.

Omitted observation selection uses `default_observations`, falling back to all observations if the field is absent. An explicit empty list applies no constraints and returns the entire search domain. A solver status applies only to the supplied domain and selected observations.

## Error models and data splits

The generator uses Python's seeded pseudorandom generator with seed 240017. Regenerating the whole dataset in its fixed order reproduces the inputs and answer keys on the recorded Python version. Four tuning scenes are separate from held-out camera configurations and observations. The solver has no fitted parameters.

- **Exact:** no added noise. Analytic fixtures use zero tolerance; teaching fixtures use noiseless central values and nonzero bounds to show regions.
- **Bounded:** independent uniform angular draws in [−tolerance,+tolerance]. Correct correspondences obey the declared bound by construction. Bearing values wrap modulo 360°; unsigned angles clip to [0°,180°], which cannot increase error from a valid noiseless angle.
- **Gaussian:** independent normal draws with standard deviation equal to the declared tolerance. Displayed intervals are ±1σ assumptions, not guaranteed bounds. Unsigned values are clipped to the physical range. Joint acceptance of several intervals differs from marginal one-sigma coverage. The report measures this on twelve trials without making a population-confidence claim.
- **Corruption:** one benchmark swaps a landmark identity and another inserts a contradictory bearing. Their source camera is retained in the answer key, but it need not satisfy the corrupted inputs. Consistent evidence at a wrong position would not establish a correct correspondence.

## Cell solver

The solver first enumerates an 8 × 8 coarse partition. Each retained cell is split into four children until the requested final resolution, a power of two from 8 through 256, is reached. The interface offers 32, 64, 128 and 256. Every output cell lies on one uniform final lattice.

For a cell with center c and circumscribed radius r, let d be its center-to-landmark distance. If d > r, every bearing within the cell lies within `asin(r/d)` of the center bearing. This follows by drawing tangents to the enclosing disk. If d ≤ r, the algorithm uses the full 180° circular uncertainty. For an unsigned pair angle, add the two bearing variation bounds and cap at 180°. The reverse triangle inequality then encloses every residual in the cell.

A cell is excluded only if some constraint's minimum possible residual exceeds its tolerance. It is **inner** only when every maximum residual is below tolerance and all used landmarks have d > r. Otherwise it is an unresolved **boundary** cell. The closed union of inner and boundary cells is the outer cover. No camera estimate or centroid is returned as the answer.

For repeated measurements of the same bearing or unordered angle, disjoint allowed intervals establish a direct conflict away from excluded singularities. Other conflicts are detected when refinement eliminates all cells. A nonempty cover without sampled witnesses remains unresolved.

The cell array stores `[ix, iy, kind, component]`, where kind 1 means inner and 0 means boundary, and indices start at the lower left. Eight-neighbor adjacency labels connected components of the closed outer cover. An exact solution cannot connect across separated cover components under the real-arithmetic inclusion argument, but a cover component need not contain a solution. Uncertain bridges can merge exact branches.

## Numerical claims

In real arithmetic, the outer union contains the exact feasible set, and the inner union is contained in it. Their areas provide lower and upper bounds within the chosen domain. Adding a constraint intersects the exact set and cannot enlarge it. The implementation uses the same lattice and pad across constraint selections, allowing direct subset checks on retained cell indices.

The implementation uses Python binary floating point and libm with a 1e-8 degree outward comparison cushion and an inward cushion for inner cells. It is not directed interval arithmetic. Thus the delivered inclusion and incompatibility results are numerical evidence supported by an analytic construction and bounded independent checks, not a machine-certified continuous solver. The 1e-8 degree pad was chosen as a small engineering cushion, not fitted to held-out results.

`feasible` means the numerical predicate accepts at least one cell-center witness; `unresolved` means an outer cover exists with none; `incompatible` means the numerical outer cover is empty or the direct conflict check succeeds. No absence conclusion follows from an empty reference point grid alone.

The numerical area error envelope is `area_upper - area_lower`. It can remain large for thin regions. The cell diagonal is a discretization scale, not a Hausdorff error bound or position-confidence radius. No exact-topology or localization-accuracy claim is made. Reports explicitly retain conservative artifacts near landmark singularities.

## Independent checks

The truth generator uses dot-product/acos pair angles. The solver uses atan2 bearings and circular distances with disk bounds. The reference checker uses cross/dot angles between rays, including between a bearing ray and the observation's unit direction. It brute-force samples every center of a dense grid and imports no solver code. This is algorithmic separation, though all paths still use ordinary floating-point library operations.

Analytic tests cover a unique bearing-triangle intersection, reflected solutions from two angle constraints, contradictory bearings and a Thales circle. Additional tests cover angular wraparound, collinear repeated layouts, wrong identities, rectangular cells, zero-width and off-grid regions, singularities, and constraint/refinement nesting. Dense reference inclusion, inner corners/centers and known camera inclusion are different recorded checks; none substitutes for a formal prover run.

The stored analytic reflection fixture uses A=(-4,0), B=(0,0), C=(4,0). Its ideal angles have cotangents 7/6 and 1/2. The two upper-side circle equations are x²+y²+4x−(14/3)y=0 and x²+y²−4x−2y=0. Their intersections are B and (1,3). Reflection gives (1,−3). Combining opposite circle-center signs gives the extra candidate (40/61,48/61) and its reflection, but its second angle is supplementary to the required angle, so it is excluded. B is singular. Thus the ideal angle pair has exactly the two intended solutions. The JSON stores floating approximations of these angles; tests use the documented numerical tolerance.

## Sources checked

Sources were checked on 2026-10-17 (America/Toronto). The [SymPy geometry documentation](https://docs.sympy.org/latest/modules/geometry/index.html) identified version 1.14.0 and documents two-dimensional geometry primitives. No SymPy API is used. The requested [Blender manual](https://docs.blender.org/manual/en/latest/) and its index could not be retrieved by the browsing tool; the second attempt reported HTTP 402. No Blender feature or rendering claim is relied on.

The [Python HTTP server documentation](https://docs.python.org/3/library/http.server.html) was checked for the standard-library local service. Its moving documentation endpoint identified Python 3.15.0, while the executed interpreter was 3.14.8. The implementation uses the long-established HTTPServer and BaseHTTPRequestHandler APIs and verifies them with local HTTP tests. No external dataset, standard, paid service or image library is needed.
