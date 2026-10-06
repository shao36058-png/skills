# Modal audit and acceptance

## Inspect existing results first

Discover the open AEDT process, select its PID and gRPC listener, and verify the active project/design. Creating a skill or reproducing a report does not require a new desktop or solver run.

Record actual frequencies, independent geometry variables, solved variation, port definitions, de-embedding/renormalization, incident and target channels, materials/boundaries, native convergence and sweep type. Imported `Setup - ... : Table` entries may contain historical dimensions; do not accept them as current geometry's native results.

Exporter syntax, replacing every placeholder with the observed session:

```powershell
python scripts/export_saved_modes.py --pid CURRENT_PID --port CURRENT_GRPC_PORT --version AEDT_VERSION --project PROJECT --design DESIGN --solution "SETUP : SWEEP" --input-mode INPUT_PORT:MODE --target-mode OUTPUT_PORT:MODE --pec-ports --out NEW_EMPTY_DIRECTORY
```

The output directory must be empty. `modal_data.json` leaves identity, completeness and normalization pending until verified; do not change flags solely to obtain a passing result. Confirm `convergence.txt`, solution and saved variation match.

## Identity and channel completeness

Rectangular TE10 has a single half-wave transverse pattern. Circular TE01 has azimuthal electric field, ideally no longitudinal electric field, and no azimuthal dependence. Check complex vectors, not only `Mag_E`, favorable S values or mode order. Circular TE01 and TM11 share a cutoff; their fields resolve what Gamma alone cannot.

Include all propagating channels at the highest frequency, including two polarizations for circular `m>0` modes. Include relevant evanescent channels near discontinuities. Gamma is imaginary for propagation and real for cutoff in the ideal air/PEC case used by the exporter. Lossy guides require a different classification.

```bash
python scripts/waveguide_cutoffs.py --radius-mm RADIUS --upper-GHz BAND_UPPER
python scripts/waveguide_cutoffs.py --rectangle-mm BROAD_WALL NARROW_WALL --upper-GHz BAND_UPPER
```

The helper counts a full uniform guide. Apply the model's actual symmetry separately; a full-circle count is not a symmetry-reduced port count.

## Power metrics

For verified power-normalized propagating channels:

- Conversion efficiency: `eta_target = abs(S(target,input))^2`.
- Insertion loss: `IL_dB = -10*log10(eta_target)`. HFSS `dB(S)` normally equals `20*log10(abs(S))`, negative for attenuating transmission.
- Represented total transmitted power: sum `abs(S(j,input))^2` over represented propagating output channels.
- Represented reflection: analogous sum over propagating input-port channels.
- Represented mode purity: target power divided by represented total transmission.
- Budget residual: `1 - reflection - transmission`.

Evanescent S coefficients do not belong in real-power sums. Do not call the residual ohmic loss before checking normalization, completeness, radiation boundaries and numerical error. A truncated PEC port can balance its represented S column while omitting physically open channels.

JSON schema: arrays share `frequencies_GHz`; `s_parameters` maps `port:mode` to real/imag arrays; `propagating` supplies a boolean array per represented mode. Declare `input_mode`, `output_port`, `target_mode`, `metadata.sweep_kind` and evidence flags. The exporter creates this schema.

```bash
python scripts/modal_metrics.py --json modal_data.json --output metrics.json
python scripts/modal_metrics.py --json modal_data.json --min-efficiency USER_THRESHOLD
```

Exit 0 without a threshold means a numerical audit completed. With a threshold, exit 0 requires all four evidence flags, no represented power gain above a 1e-4 numerical allowance, and every sample strictly above the threshold; exit 1 means below/equal threshold with verified evidence; exit 2 means invalid data or pending evidence. The helper does not prove requested bandwidth coverage: check endpoints, center and spacing separately, distinguishing interpolated from discrete data.

## Convergence and tested scope

Read native `Converged : Yes/No` and actual ΔS criterion. MaximumPasses with `Converged : No` is unconverged even when the target trace is near 0 dB. Inspect target-channel and relevant matrix changes before requesting refinement. Interpolating output frequencies are not all independent full-wave solves. An even-count sweep can omit its center; use the saved adaptive center result when frequencies match.

Skill creation reviewed saved HFSS 2025.2/PyAEDT 1.1.0 data without another solve. The reference converter showed near-unity target transmission while convergence and port-completeness checks remained pending. It demonstrates auditing, not a convergence-certified or fabrication-validated design.

For a later authorized solve, monitor available RAM and committed-memory headroom, bound parallel solves, and preserve geometry. Finite conductivity, roughness and machining/interface tolerances require additional modeling; PEC results cannot certify physical loss or power capacity.

## Primary references

- [PyAEDT solution-data access](https://aedt.docs.pyansys.com/version/stable/API/visualization/_autosummary/ansys.aedt.core.visualization.post.solution_data.SolutionData.get_expression_data.html).
- [HFSS port mode count and Gamma](https://ansyshelp.ansys.com/public/views/secured/electronics/v252/en/subsystems/hfss/Content/HFSS/Modes.htm).
- [Wave-port placement and evanescent decay](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v242/en/Subsystems/HFSS/Content/HFSS/WaveportPlacement.htm).
