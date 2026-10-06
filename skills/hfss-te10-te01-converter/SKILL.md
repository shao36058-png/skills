---
name: hfss-te10-te01-converter
description: Design, reproduce, inspect, and validate HFSS rectangular TE10 to circular TE01 waveguide mode converters, especially linear cross-shaped converters through TE20 and cross-guide TE22 intermediates. Use for thesis reproduction, modal purity, port cutoff checks, saved-result auditing, dimension optimization, and converter-to-bend interfaces.
license: MIT
metadata:
  author: "shao36058-png"
  version: "0.1.0"
---

# HFSS TE10 to TE01 Mode Converter

Capture the user's actual topology, frequency range, dimensions, and acceptance requirements before choosing a design or interpreting a near-zero-dB trace. This skill covers rectangular-to-circular mode conversion. A TE01-to-TE01 bend is a separate component.

## Select the operation

- To reproduce the cross-shaped converter, read [references/reproduction.md](references/reproduction.md). Map the paper's physical sections to the project's actual variables; preserve the user's structure. Tune cumulative TE10→TE20, rectangular→cross-guide, and cross-guide→circular assemblies.
- To inspect an open project or a negligible-loss claim, read [references/validation.md](references/validation.md). Inspect the existing session and export saved modal data before considering a new solve.
- To optimize dimensions, identify allowed variables and mechanical limits, calculate cutoff constraints, then rank candidates using actual HFSS feedback. An axisymmetric circular-taper coupled-wave model does not describe a T-shaped or cross-shaped transition. MATLAB can schedule searches or fit HFSS samples; surrogate optima still need a real HFSS solve.
- To connect a converter to a TE01 bend, match aperture, axis, orientation, reference plane and complete modal bases. A full-circle converter's TE01 index must not be copied from a symmetry-reduced bend. Scalar efficiency multiplication is an ideal matched approximation; mismatched cascades need a multimode network calculation or an assembly solve.

## Engineering decisions

Identify input rectangular TE10 and output circular TE01 using fields and cutoff/propagation constants. TE01 can be degenerate with TM11; matching cutoff or being the sixth port mode does not uniquely establish identity. Reidentify modes after radius, symmetry, mesh, or port changes.

Keep conversion efficiency, total transmission, reflection, and mode purity separate. For verified power-normalized propagating input `i` and target `t`, target efficiency is `abs(S(t,i))^2`. Real-power sums include propagating modes only. Evanescent S coefficients are not lost real power.

Read native convergence. `SOLVED`, a completed last pass, a favorable trace, and a successful process exit do not prove the requested ΔS criterion was met. Record interpolation separately from discrete solves. Inspect saved parameter variations rather than confusing an imported historical table with current geometry.

An air-filled PEC model omits conductor dissipation. State the tested model and frequency coverage; near-unity efficiency is not a physical zero-loss or power-handling guarantee. A balanced truncated modal S column does not prove omitted propagating channels are harmless.

Skill creation or saved-result review does not require a new solve. For a later authorized solve, check the current session and memory/commit headroom, preserve the validated structure in a working copy, and stop when current requested requirements are met.

## Deterministic helpers

- `scripts/waveguide_cutoffs.py`: standard-library cutoff and mode-count diagnostic for uniform air/PEC rectangular and circular guides. Counts circular degeneracy, excludes TE00, and does not assign HFSS indices. Supports circular electrical size `k0*radius <= 12`.
- `scripts/export_saved_modes.py`: reads an explicitly selected existing AEDT PID and gRPC port; requires psutil/PyAEDT and confirmed PEC ports. Includes native convergence and parameter provenance. Never starts a solve or saves a project.
- `scripts/modal_metrics.py`: standard-library audit of saved modal JSON. Computes target efficiency, represented-mode purity and power budget; rejects nonfinite, duplicate, incomplete and nonpropagating-target data. Final acceptance requires convergence, identity, completeness and normalization evidence. Exit 0 without a threshold means an audit completed, not that the device passed.

Use user-specific thresholds. Do not import the former bend's 28 GHz, 1 GHz bandwidth, 98% or 96% requirements into a different converter automatically.
