# Geometry review

This is an assistant-produced mathematical review of the planned solver. It is separate from the executed analytic fixtures and separately implemented dense-grid checker. It provides no independent empirical validation and no formal floating-point certificate.

## Cell enclosure in real arithmetic

Let a rectangular cell have center c and circumscribed radius r, and let L be a landmark at distance d from c. For d > r, every point of the cell lies inside the closed disk of radius r about c. The two tangents from L to this disk subtend a half-angle alpha = asin(r/d). Therefore the circular distance between the bearing at c and the bearing at any point of the cell is at most alpha. Angles must use one consistent unit.

For d <= r, the disk bound cannot exclude a bearing singularity and alpha = 180 degrees is a safe, deliberately loose enclosure. A rectangular cell can still exclude L in this case, but the disk calculation alone cannot establish that fact.

The circular distance on the bearing circle obeys the reverse triangle inequality. If the center residual from a measured bearing is q, its value anywhere in the cell belongs to [max(0, q-alpha), min(180, q+alpha)]. An outer cell survives if the lower endpoint is at most the declared tolerance. An inner cell is valid if the upper endpoint is at most the tolerance and the cell contains no used landmark singularity. Requiring d > r for all used landmarks is a sufficient conservative singularity guard.

An unsigned angle between two landmark rays is their circular distance, in [0,180]. Applying the metric triangle inequality to both arguments bounds its variation by alpha1+alpha2. Clipping this bound at 180 degrees remains safe. The same interval construction therefore applies to an unsigned-angle observation, including observations near zero or 180 degrees. A dot-product angle implementation must clamp its cosine to [-1,1]; a stable alternative uses abs(atan2(cross,dot)).

Intersecting all outer tests preserves every feasible point in real arithmetic. An inner cell must pass every upper-bound test. Adding an observation cannot add outer cells or inner cells when the domain, final grid, padding, and observation values remain fixed. It can turn previously inner cells into boundary cells. Restricting observations can restore cells.

## Numerical qualification

Ordinary Python arithmetic and libm calls do not direct rounding outward. A small angular pad helps at boundaries but does not prove the real-arithmetic enclosure survives all rounding. State the result as a conservative geometric construction with numerical padding and measured inclusion checks. Do not label the implementation certified, rigorously enclosing in floating point, or guaranteed inclusion without a proved rounding budget or interval arithmetic with directed rounding.

Use outward padding for the outer test and inward padding for the inner test. Validate finite coordinates, finite observation values, nonnegative tolerances, positive domain dimensions, and valid resolution. Calculate cell centers and dimensions from integer grid indices to avoid recursive coordinate drift. Handle a bearing point at an observed landmark as undefined in every acceptance implementation. Observations that reference the same landmark twice have angle zero away from that landmark; either reject this input or document that special case.

## Area and connectivity

For a uniform final grid, the count of retained outer cells times cell area is an upper bound on feasible area in real arithmetic. The count of inner cells times cell area is a lower bound. Cell boundary overlap has zero area, so closed-cell storage does not invalidate the sum. Clip cells to the search domain if its partition is not exact. The bounds concern feasible area inside the chosen domain; they say nothing about locations beyond it. A center witness proves existence but supplies no positive lower bound on area. A feasible line or isolated point can have zero area and no grid-center witnesses.

Eight-neighbor clusters describe connectivity of the retained cell cover at the chosen resolution. They can merge separate feasible branches through uncertain cells or a single corner contact. A connected exact feasible set is contained in one cover cluster when cells are closed and corner neighbors are included, but one cluster need not contain only one exact component. Report these as outer-cover components. Component counts across different resolutions need not be monotone. Witness groups do not certify exact components either.

An empty outer cover is numerical evidence of incompatible observations within the domain under the implementation's arithmetic assumptions. A nonempty cover with no witness is unresolved. A nonempty witness proves compatibility only to the numerical point predicate and tolerance used; report that distinction. Do not infer incompatibility from an empty center grid. Incorrect correspondence may yield consistent observations at a different location.

## Analytic checks

Take landmarks A=(0,0), B=(4,0), and camera C=(0,3). The absolute bearings are 270 degrees to A and 360-arctan(3/4) degrees to B. Their directed supporting lines intersect at C; the ray direction distinguishes the intended intersection. The unsigned angle ACB is arctan(4/3), about 53.130102 degrees. Reflecting C to (0,-3) preserves this unsigned angle. A single unsigned angle also admits an arc of positions, so this pair alone must not be described as exactly two candidate points.

To produce exactly two reflected positions with angle observations, use A=(-1,0), B=(0,0), D=(1,0), and impose angle ACB=45 degrees and angle BCD=45 degrees. At C=(0,1) and C=(0,-1) both hold. For each length-one segment AB or BD, a 45-degree subtended angle lies on a circle of radius sqrt(1/2), with centers (-1/2, plus or minus 1/2) for AB and (1/2, plus or minus 1/2) for BD. Matching the signs gives circle intersections B and (0, plus or minus 1); opposite signs give only the tangent point B. Excluding the undefined camera position B leaves exactly C=(0,1) and C=(0,-1). Direct substitution confirms each retained point has the required unsigned angles. With positive error bounds these points become regions. An absolute bearing to A can select a reflected region. An unsigned angle to an additional landmark outside the reflection axis can also separate them, provided its predicted angles differ by more than the combined uncertainty.

For an exact unique two-bearing fixture, use A=(0,0), B=(4,0), bearings 225 degrees to A and 315 degrees to B, with C=(2,2). The directed rays intersect uniquely. Explicitly checking ray direction catches confusion between a bearing from camera to landmark and its reverse.

Useful boundary fixtures include a bearing centered on 359 degrees with an allowed interval crossing zero, opposite rays at 180 degrees, zero-width tolerances, a landmark exactly at a cell corner, collinear landmarks with multiple admissible intervals, and an exact feasible point on a grid boundary. Dense sampling independently checks sampled behavior but cannot establish continuous inclusion or exact topology.

## Implementation review and adversarial checks

The subsequent source review inspected solver.py, reference.py, generate.py, and evaluate.py. The implemented angle residual encloses the unsigned angle first and then computes the minimum and maximum distance to the reported value, which handles endpoint clipping correctly. The repeated-measurement conflict precheck is sound for both reversed unsigned landmark pairs and circular bearing intervals. It is a sufficient conflict test; pairwise overlap alone is not a general feasibility test. Rectangular domains use the diagonal radius, as required.

Six assistant-authored adversarial tests in tests/test_adversarial.py passed with `python3 -m unittest tests.test_adversarial -v`. They sample an analytic Thales circle, retain two exact reflected cameras, remove the reflected camera after adding a calibrated bearing, inspect a strongly rectangular domain, sample inner-cell corners with a separate point predicate, check refinement and added-constraint nesting, exercise wraparound conflict thresholds, and keep singular landmark cells out of the inner area. These bounded tests supply numerical evidence. They do not prove continuous correctness or formally certify floating-point arithmetic.

The exact reflected fixture produces three outer-cover components at n=128, although its exact solution set has two points. The extra unresolved cluster is near the excluded landmark B. This is an observed conservative artifact and confirms that the component count requires the cover qualification.

The reviewed fixes align solver and reference defaults: both select default_observations when present, otherwise all observations. The evaluator also passes identical selections explicitly. The generator's wraparound fixture now uses camera (-2,-0.95), and a reference test verifies that the bearing interval to B crosses 360 degrees. Inputs were regenerated after the correction. The final review also identified an incomplete evaluator failure gate; valid-truth exclusions and supplementary reference misses now contribute to failure counters, and the evaluation CLI exits nonzero on any failed check.
