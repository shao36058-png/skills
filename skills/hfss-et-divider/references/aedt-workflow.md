# AEDT / PyAEDT workflow for an existing HFSS divider

Read this reference when inspecting, retuning, recovering, or delivering an HFSS E-plane T divider in an existing AEDT session. It covers application state and result integrity; use the RF reference for design physics.

The API behaviors below were checked against PyAEDT 1.1.0 and AEDT 2025 R2. Treat these as a tested environment, not required versions. Discover the installed tools and inspect local API signatures when another version differs. Paths, process IDs, project names, setup names, port numbers, and numerical tolerances in a past run are not defaults for another project.

## Bind to the intended session and design

1. Discover the available AEDT session-list and connection tools, then list running sessions before connecting. Record the selected session's process ID and, where applicable, broker/gRPC port. A PID and a network port are different identifiers. Never infer the active project from a window title alone.
2. Bind explicitly to that session, using the installed API's supported PID/port arguments. Query the project list, active project, absolute project file, design list, active design, and solution type. Confirm the intended identity before a mutation. A matching project basename is insufficient when two directories contain copies.
3. Enumerate variables, bodies, boundaries, ports, analysis setups, sweeps, and existing results. Identify the physical common port from its face and propagation direction. Port numbers do not identify an E-T input by themselves.
4. Keep unattended session ownership explicit: attach to the existing desktop, preserve it on exit, and release only the automation connection when done. Saving, closing, deleting, and replacing apply only to the authorized target. Avoid save-all, close-all, and desktop shutdown in a user's shared session.

For substantial changes, save an authorized working copy with an unambiguous absolute path. Verify the new `project_file` immediately: `save_project(new_path)` uses SaveAs and changes the current project's identity. Record the source and destination so a retry does not accidentally reconnect to or overwrite the source.

## Verify coordinates and port definitions

Distinguish global coordinates from an object's creation coordinate system. A branch created relative to a coordinate system at a T-junction wall has its length measured from that wall, not from the global origin. Record the actual coordinate-system origin, axes, and box extents before changing length expressions.

When lengthening uniform arms, preserve the junction and matching features unless their movement is intentional. Check the three new port-face centers against the intended geometry. For an E-plane T, the common branch and the collinear arms have different face normals; inspect faces instead of reusing one integration line blindly.

Mode-1 integration lines must lie within each port face and span the intended electric-field direction. Keep their direction consistent with the chosen modal phase reference. Changing a line's direction can change a reported transmission phase by 180 degrees without changing the physical divider.

HFSS boundary properties can preserve literal integration-line coordinates even when the geometry is parameterized. After a dimensional edit, read back `Modes -> Mode1 -> IntLine`, `UseIntLine`, alignment, and de-embedding properties. In the tested environment, explicit evaluated coordinates with units were reliable for boundary updates. Do not assume that a symbolic expression accepted in a geometry field will be evaluated in an integration-line property. Read back and verify the resulting numeric line and port face; update it after subsequent dimensional changes.

Preserve existing mode counts and normalization unless an identified error requires a change. Multiple requested port modes are not intrinsically incorrect. Interpret propagating and evanescent modes at the operating band, and use the explicit modal expression, such as `S(i:1,j:1)`, when reporting the fundamental mode.

## Create and identify setups and sweeps reliably

Use the user's existing convergence settings for initial tuning unless the user requested a different accuracy or the existing result demonstrably fails its stated checks. Agree on the design objective and a bounded tuning pass. A better-looking curve alone does not justify repeated mesh tightening or adding more solved frequencies. If the user asks to stop refinement, complete and report the result at the authorized precision.

Deleting and recreating a setup under the same name exposed a PyAEDT cache pitfall in the tested version:

- `app.setup_names` reads native `GetSetups()`.
- `app.setups` caches Python setup objects.
- A setup's first `sweeps` access can load sweep definitions from `app.design_properties`, which is parsed from the saved `.aedt` file.
- Deleting a setup updates native state and the Python setup list, but does not itself save the project. A same-name replacement can therefore see the old sweep definition on disk.
- `create_linear_count_sweep()` checks the Python sweep list and automatically gives a conflicting name a random suffix. The returned sweep name can differ from the requested name.

For an authorized setup replacement, delete only the intended setups, verify their absence through native setup names, and save before recreating them. Save the replacement setup before its first sweep discovery. Capture both objects returned by creation rather than assuming either requested name survived:

```python
st = app.create_setup(name=setup_name, **chosen_setup_properties)
assert st
assert app.save_project()
sw = app.create_linear_count_sweep(
    setup=st.name, name=sweep_name, unit="GHz",
    start_frequency=f_start, stop_frequency=f_stop,
    num_of_freq_points=n_output, sweep_type=sweep_type,
    save_fields=False,
)
assert sw
solution = f"{st.name} : {sw.name}"
native_sweeps = list(app.oanalysis.GetSweeps(st.name))
assert sw.name in native_sweeps
assert solution in app.existing_analysis_sweeps
```

If the intended final design has one setup and one sweep, verify that exact count using native names. `existing_analysis_sweeps` may also include `LastAdaptive`; it is not a count of frequency sweeps. If Python and native lists disagree, save and refresh the binding before result requests. Do not blindly edit private caches or interpret an automatic suffix as proof of damaged solver results.

Store the complete verified `setup : sweep` string alongside extracted metrics. Recovery, plotting, SaveAs checks, and publishing must reuse it. A request for a nonexistent sweep preceded native crashes in this case, but that observation does not establish a general crash mechanism. The reusable safeguard is to verify the requested solution exists before querying it.

The tested `app.analyze()` wrapper recognizes setup names, not a general `setup : sweep` string. An unrecognized name can fall through without solving and still return `True`. Do not use that return value to infer a sweep was solved. To solve one sweep with this wrapper, enable that sweep, disable other sweeps under the setup, and analyze the setup by its actual name. Do not transplant an `AnalyzeSweep` command from HFSS 3D Layout into a 3D HFSS design without checking the appropriate API.

## Select the intended variation explicitly

Default report families can silently include historical geometry variations. Build extraction families from the current nominal independent variables:

```python
nominal = app.available_variations.nominal_variation(dependent_params=False)
families = {name: [value] for name, value in nominal.items()}
assert solution in app.existing_analysis_sweeps
data = app.post.get_solution_data(
    expressions=expressions,
    setup_sweep_name=solution,
    variations=families,
)
assert data
```

Record the nominal values with the data, including waveguide dimensions and matching-feature positions. For frequency reports, also select `Freq: ["All"]`. Compare units and numeric values where appropriate; equivalent evaluated dimensions may have different string representations.

When a final package should contain only one solved geometry, inspect `list_of_variations(setup_name, sweep_name)` or the corresponding installed API and compare it to the intended nominal state. Historical entries in an `.asol` VariationIDs index are not, by themselves, proof that every indexed variation has retained solution data.

## Choose a sweep and verify completion

A discrete linear-count sweep requests direct solutions at its listed frequencies, subject to reuse of existing solved points. An interpolating sweep chooses its own solved basis frequencies and produces interpolated outputs on the requested frequency grid. Thus 21 output points from 23 to 25 GHz do not imply 21 independent full-wave solves. Record the sweep type, output grid, adaptive settings, and interpolation tolerance separately.

In the tested `SweepHFSS` API, changing `sw.props["Type"]` to `"Interpolating"` or `"Discrete"` followed by `sw.update()` calls native `EditFrequencySweep`. Preserve the intended range/count, set `IsEnabled=True`, and check the interpolation properties when changing types. `change_type()` documented on another sweep class is not necessarily available on this class.

For a workflow that needs responsive monitoring, submit `app.analyze(actual_setup_name, ..., blocking=False)` using the installed API. Emit flushed log markers before submission, after its return, before extraction, and after extraction. Poll the native running state at a modest interval and inspect fresh result/profile timestamps. Allow for job startup before interpreting an initial idle state as completion. Bound waiting by evidence of progress and the task's allowed runtime.

In the tested version, the blocking path calls native `odesign.Analyze(name, True)` directly; it does not implement a Python frequency-progress loop. A quiet Python process does not locate the blockage without stage markers. An asynchronous `True` return indicates submission without a caught exception, and an idle status indicates no current simulation; neither proves a successful solution.

Validate the actual nominal result before delivery:

- Inspect the solver's normal completion/termination status and messages for failure. Check the exported convergence history against the selected criterion and number of consecutive converged passes. A window title saying `SOLVED` is insufficient. Status labels can differ by version.
- Extract the expected complete frequency grid, checking units, endpoints, spacing or explicit frequencies, finite real/imaginary values, and array lengths. An `.asol` definition listing frequencies does not prove those frequencies were solved.
- Check the relevant return loss, both output transmissions, amplitude balance, and relative phase using complex data. Use a phase-error expression with a clear reference, such as `angle(-S12/S32)` for an intended 180-degree split, rather than treating the phase wrap at plus/minus 180 degrees as a discontinuity.
- Check power balance with the appropriate normalization and all relevant propagating modes. A closed, single-propagating-mode, PEC model should approximately conserve reflected plus transmitted power. Set tolerance consistently with the selected numerical accuracy. With conductive/dielectric losses or other radiation paths, account for those channels rather than enforcing a unit three-term sum.

A coarse sweep is appropriate for efficient tuning when it covers the stated objective; describe its limits honestly. Add independent frequency checks only when needed to resolve a concrete concern and within the user's requested refinement scope.

## Recover a stalled job without broad side effects

First distinguish a long-running solve, a dialog requiring attention, a solver failure, an extraction blockage, and stale results. Read the selected job's progress, messages, profile, output timestamps, and process activity. Do not diagnose file corruption from one crash or from a preserved historical variation index.

Prefer the selected job's normal Stop/Abort control. The tested API exposes `stop_simulations(clean_stop=True)` and a less graceful `clean_stop=False`; inspect its desktop-wide scope before using it in a session with other jobs. If a native blocking call prevents reliable API use, the UI may be the safer control. Escalate to a forceful abort only for the identified stalled work and retain completed data where possible. Do not kill a desktop that owns unrelated user projects or jobs.

After stopping, confirm that the old job has ended before another solve. Preserve completed meshes/results and resume the unchanged setup when valid. If a clean result rebuild is necessary, close only the authorized working project, confirm the relevant process/file ownership, and quarantine the exact working result directory within the controlled work area. Keep the source and unrelated projects intact. Do not remove live lock/semaphore files to force access.

Only clean variations or trial results that belong to the authorized task. In the tested API, `cleanup_solution("All", entire_solution=True, linked_data=True)` removes solution data across that target design's variations; it is broader than deleting a plot or sweep. Use such cleanup before the intended final solve when required, never after it. Deleting a setup does not itself prove that every historical result file was removed.

## Save, archive, and replace the final deliverable

Build in a fresh staging directory so old files cannot satisfy new validation checks. Keep project creation, validation, archival, and final destination replacement separate enough to diagnose a partial failure.

1. Verify the target design, geometry, port definitions, chosen settings, actual solution string, and intended variation. SaveAs the final staged `.aedt` path, then confirm `project_file` now points there.
2. Re-extract the staged solution after SaveAs and compare frequencies, nominal parameters, and complex S values to the verified result with a suitable tolerance. Export convergence and metrics with their settings and units.
3. Archive with result inclusion enabled. Inspect the archive entries and integrity instead of assuming a ZIP path layout. The tested AEDT archive used `$PROJECTDIR/<project>.aedt` and `$RESULTSDIR/...` entries, not literal `<project>.aedtresults/` paths. Other versions may differ. Verify actual nonempty solution files and the intended design are included; a CRC-valid archive alone proves neither.
4. Close only the staged/target project when needed for replacement, confirm it is no longer in the desktop project list, and verify its lock is released. A successful close wrapper return alone may not prove that a lock has disappeared.
5. Before moving or replacing a project/results pair, resolve the exact absolute source and destination paths and ensure they are within the authorized workspace/target. Back up an authorized existing final deliverable when appropriate. Replace the whole intended `.aedtresults` directory along with its matching `.aedt`; merging a fresh directory into old results can preserve unrelated variation files. Do not touch source backups or other projects.
6. Compute hashes for the approved staged and delivered artifacts and compare copied files. Hash equality verifies transfer integrity, not electrical correctness. Where feasible, reopen the delivered project or restore the archive in a separate controlled location and re-extract the intended saved solution. Confirm geometry, solution identity, full frequency data, and retained results without overwriting the original during this check.

Report the delivered settings, numerical result, and any remaining limits. The PEC matching result is not an OFHC-copper thermal model or a power-handling rating. Package cleanup and session release should leave the user's unrelated desktop projects untouched.
