# Cross-shaped converter reproduction

## Source and intended use

Qi Lanyue (戚蓝月), *Ka波段模式变换器与波导弯头的研究*, University of Electronic Science and Technology of China, master's thesis, Chapter 3, printed pp. 21–31. These notes paraphrase the design method; they do not distribute the thesis or its figures. Consult the user-provided copy for geometry details.

The chapter treats a linear cross-shaped converter: rectangular TE10 → rectangular TE20 → cross-guide TE22 → circular TE01. The cross-guide label belongs to that intermediate cross-section, not a circular TE22 mode or a universal HFSS mode index.

## Reproduction sequence

1. Inspect the user's solved geometry and actual band. Distinguish the original device, uniform frequency scaling and a modified realization. Do not silently substitute the thesis's frequencies or dimensions.
2. Identify the input rectangle, T transition, enlarged rectangle, cross-shaped transition, circular output and straight interface sections. Check loft orientation, connectivity and accidental air/metal gaps before optimization.
3. Develop the first TE10→TE20 assembly. Doubled rectangular broad wall `a_TE20 ≈ 2*a_TE10` is a cutoff-matching seed; its two linear section lengths remain search variables.
4. Append the rectangular-to-cross-guide section and optimize the cumulative device. Vary cross arms and transition length while maintaining intended symmetry. Independent section efficiencies miss interface reflections.
5. Append the cross-guide-to-circular section and optimize the full assembly. Keep its input consistent with the previous section; vary final transition length and circular radius under cutoff/mechanical constraints.
6. Verify full-assembly modal data, fields and convergence before tolerancing or delivery. Reidentify modes across changes in the port basis.

## Analytic seeds, not acceptance

For uniform air/PEC guides:

`fc_rect(m,n) = c0/2 * sqrt((m/a)^2 + (n/b)^2)`.

`fc_circular_TE(m,n) = c0*x'_mn/(2*pi*R)`; TM uses `x_mn`.

TE01 has `x'_01 ≈ 3.831706`; TE02 has `x'_02 ≈ 7.015587`.

Matching input TE10 to circular TE01 cutoff gives `R ≈ x'_01*a/pi`. Suppressing TE02 at the upper band edge requires `R < c0*x'_02/(2*pi*f_upper)` with margin. These constraints can conflict; tune the complete device rather than presenting a seed as an optimum.

Above cutoff, `lambda_g = c0 / sqrt(f^2-fc^2)` sets an initial length scale but does not predict cross-shaped-converter S parameters. Uniform frequency scaling is a seed for nondispersive PEC geometry: scale every dimension consistently, then validate the port basis and complete assembly. A modified aperture is not automatically a uniformly scaled reproduction.

## MATLAB or other search drivers

MATLAB can choose bounded candidates, call an HFSS evaluator or read completed sample files, and rank measured scores. Enforce topology, connectivity and cutoff constraints before submission. Keep normalization, target identity, solved variation and convergence with every score.

Do not reuse an axisymmetric circular-taper coupled-mode proxy as a validated cross-shaped converter model. No dedicated MATLAB surrogate has been validated by this skill's saved-result review.

Only optimize when currently requested. Every accepted candidate needs actual HFSS data; a surrogate maximum is a proposal. Check frequency holes/narrow dips, respect requested bandwidth coverage, and stop when requirements are satisfied.

## Converter and bend interface

Match circular radius/material; define connecting straight length and reference planes; align full modal bases and symmetry planes. Include propagating parasitic modes that can recouple. Multiplying isolated TE01 efficiencies is an ideal matched single-channel approximation; verify the multimode network or full HFSS assembly for system-performance claims.
