---
name: hfss-te01-bend
description: Optimize dimensions and validate modal transmission of HFSS TE01 overmoded circular-waveguide 90-degree miter bends using MATLAB candidate screening and actual HFSS feedback. Use for TE01 bend convergence, memory-limited solves, bandwidth acceptance, and reproducible delivery while preserving the requested topology.
license: MIT
metadata:
  author: "shao36058-png"
  version: "0.1.0"
---

# HFSS TE01 Circular-Waveguide Bend

Use actual modal HFSS results to evaluate a circular-waveguide 90-degree miter bend. First establish the user's frequency, bandwidth, power-efficiency thresholds, length definition, permitted dimension changes, and current simulation state. This workflow targets circular guides, linear tapers, and a 45-degree miter reflector; do not substitute a smooth curved bend unless requested.

## Choose the current operation

- For saved-result review, run `scripts/verify_band.py` against an exported CSV. Report that this verifies saved samples; it does not rerun HFSS.
- For convergence and memory failures, read [references/hfss-workflow.md](references/hfss-workflow.md). Inspect ports, modes, boundaries, mesh, sweep settings, and Windows committed-memory headroom before changing a working copy.
- For dimension search, read [references/matlab-search.md](references/matlab-search.md). Copy the MATLAB scripts into a work directory; use their proxy values only to rank candidates, then verify with HFSS.
- For final delivery, use the save/reopen/verify procedure in [references/hfss-workflow.md](references/hfss-workflow.md). Delete only authorized task-owned candidates after verifying the final native results.

## Engineering invariants

For an air-filled PEC guide, keep the solved cavity as air and check metal-wall boundaries separately from ports and symmetry planes. Use symmetry only when the target mode and physical geometry support that symmetry.

Identify TE01 from modal fields, cutoff/propagation constants, and alignment of degenerate modes. Port numbering and required mode count depend on geometry and frequency. When input TE01 is port 1 mode 4 and output TE01 is port 2 mode 4, efficiency is `abs(S(2:4,1:4))^2`. Amplitude and total transmitted power across all modes are different quantities.

Distinguish magnitude, phase, and complex S-parameter mesh-change criteria. A single-frequency adaptive mesh with a discrete sweep provides sampled-band evidence, not continuous-frequency extrema or multifrequency mesh independence. Include the actually tested scope in every acceptance report.

Use the current user's acceptance thresholds. The CSV helper defaults to 28 GHz power greater than 0.98 and 101 equally spaced samples from 27.5 to 28.5 GHz above 0.96; these are configurable example requirements, not a performance guarantee. Reject incomplete, duplicate, nonfinite, or off-grid acceptance data.

## Solver and optimization controls

Preserve an accepted project while searching in a working copy. Record dimensions, setup, status, and actual results for each candidate. Reject a fitted or proxy optimum that fails real HFSS acceptance, and stop when the user's requested outcome is reached.

When asked to stop adding points, stop queued follow-on jobs, retain complete computed samples, and save a sweep definition consistent with the accepted dataset. Do not restart computation during a documentation-only task.

Discover the current AEDT PID and gRPC port; never reuse a historical PID. Verify that the intended project and design already exist in the session before calling `scripts/run_guarded.py`. This helper submits a solve; it must not run merely to view results. Review its status JSON after a run, including stop reasons and new execution errors.

The solver helper is Windows-specific and adapted from an HFSS 2025.2/PyAEDT 1.1.0 workflow. MATLAB scripts were used with R2024b. Users need their own licensed HFSS/MATLAB installations; this package contains neither software nor proprietary project files. Portability changes to the solver helper have not been exercised with a new full-wave simulation.
