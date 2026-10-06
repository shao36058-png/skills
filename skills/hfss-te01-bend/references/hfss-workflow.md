# HFSS Validation and Resource Control

## Start from evidence

Find the requested project, design, dimensional variables, solver setup, port definitions, and saved sweep. Review current simulation state before attaching or submitting a job. Connect to a confirmed AEDT session using its PID and gRPC port; never silently create another desktop or blank project after an attachment failure.

After a restart, verify saved native data and completed frequency samples before resuming. A reboot scheduled by the user is not evidence of memory exhaustion. A stale lock may only be cleared after its owner process has exited and the lock is confirmed to belong to this task.

## Modes, walls, and mesh

Check TE01 field patterns and degenerate-mode integration-line alignment. Include all relevant propagating modes and investigate decay lengths of the first omitted evanescent modes near discontinuities. A mode count that was adequate at one radius or frequency may be inadequate at another. A half model may change mode indices relative to a full model.

Keep air inside the solved cavity; verify PEC walls and separate symmetry and wave-port assignments. Check the impedance multiplier appropriate to any symmetry reduction. Compute power balance using propagating modes and examine reciprocity; a multimode Touchstone file is not a conventional two-port 50-ohm file.

For resource-limited candidate screening, a tested starting configuration was second-order basis functions, curved-element slider 3, wavelength target 0.5, 15% refinement per pass, four cores, one task, and discrete sweeps without saved fields. These settings do not establish mesh independence by themselves. Inspect actual mesh growth and the configured convergence criterion; never claim convergence solely because the maximum pass count was reached.

Use actual center-frequency transmission to screen candidates before complete bandwidth solves. Separate results from different meshes and convergence levels in the candidate table.

## Memory-guard helper

Dependencies: Windows, Python with `psutil` and PyAEDT, and an installed/licensed HFSS. The helper currently targets HFSS 2025.2 by default. Discover software paths on the user's machine; if installation discovery fails, set the correct `ANSYSEM_ROOT252` environment variable explicitly.

Before execution, verify the project and design are already open in the selected session and that the working copy is authorized for computation. Supply an empty output directory; the helper refuses to overwrite previous run evidence.

```powershell
$env:HFSS_AEDT_PID='<verified current PID>'
$env:HFSS_AEDT_PORT='<verified current gRPC port>'
$env:HFSS_PROJECT='<existing working project name>'
$env:HFSS_DESIGN='<existing design name>'
$env:HFSS_RUN_DIR='<absolute empty run directory>'
$env:HFSS_AEDT_VERSION='2025.2'
$env:HFSS_SETUP='Setup1'
$env:HFSS_CORES='4'
$env:HFSS_TASKS='1'
python '<skill directory>/scripts/run_guarded.py'
```

The guard measures physical available memory, committed-memory total/limit/headroom, and the resident memory of newly created solver processes every two seconds. Default stop lines are 4 GiB physical available memory or 3 GiB commit headroom. It also responds to a `STOP_REQUEST` file in the run directory. If stopping stalls or memory falls further, it terminates only recorded newly created solver processes whose PID and creation time still match. It does not change system page-file settings or terminate unrelated applications.

These stop lines came from a 31.3 GiB workstation and can be conservative or insufficient elsewhere. Set resource limits appropriate to the current machine rather than assuming safe completion. A normal script exit does not imply valid results: inspect `run_status.json`, especially `successful`, `guard`, and `execution_errors`.

Optional live early-stop reads use `HFSS_BAND_SWEEP` (default `Band_27p5_28p5`) and `HFSS_TE01_EXPRESSION` (default `S(2:4,1:4)`). Enable `HFSS_STOP_BAND_BELOW` only after validating that mapping and the current solved variation. Incomplete live samples are progress evidence only.

## CSV review and delivery

```powershell
python '<skill directory>/scripts/verify_band.py' --csv '<exported band CSV>'
```

Columns required: `frequency_GHz` and `TE01_transmission_power` in fractional power units. The defaults require all 101 samples at 10 MHz spacing, including an explicit 28 GHz sample. Configure `--band-start`, `--band-end`, `--points`, `--center-ghz`, `--center-min`, and `--band-min` for the actual task. Exit code 0 means sampled acceptance, 1 means valid data below thresholds, and 2 means invalid or incomplete input.

For delivery, report dimensions and how overall length is measured, mode identity, center power, sampled-band minimum/frequency, actual convergence criterion, frequency coverage, and memory observations. State whether losses are ideal PEC and what additional numerical checks were actually performed.

Save the accepted design to the requested location with its native `.aedtresults` directory. Close and reopen the project, then confirm geometry, variables, sample coverage, and native modal data. Verify hashes of copied exports. Only after that should authorized task-owned old variants and temporary files be deleted. Keep unrelated projects, required native results, and source references. Use verified absolute targets and native filesystem operations; never clear a shared project or solver-temp root with broad wildcards.
