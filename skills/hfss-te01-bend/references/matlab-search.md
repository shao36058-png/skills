# MATLAB Screening and Actual HFSS Feedback

Copy `scripts/matlab/` into a work directory before running it: the functions write candidate CSV and check JSON next to their source. The four functions were used with MATLAB R2024b; no MATLAB installation is included.

`te01_taper.m` is a TE0n voltage/current coupled-mode taper model using segmented matrix exponentials and stable scattering-matrix cascading, including backward and cutoff modes. It is not a full 3D miter-bend model. `check_taper_model.m` checks a uniform-guide analytic case and lossless power balance.

`search_te01_dimensions.m` ranks mode-profile and mirror-phase agreement. Its `proxy_center`, `proxy_min`, and `score` are not HFSS bend efficiencies. The three-mode target power fractions 86.77%, 12.96%, and 0.27% were taken as a reference design target from Qi Lanyue's thesis, *Research on Ka-band Mode Converters and Waveguide Bends* (《Ka波段模式变换器与波导弯头的研究》). The thesis PDF is not redistributed.

The search uses `sqrt(1.0006*1.0000004)` for the reference air refractive index. Its default effective-length offset of 1.27 mm came from a local HFSS fit and is not universal. Set or recalibrate it for a new design family. Non-axisymmetric mode conversion, full 3D reflection, and narrow resonances remain outside the proxy.

```matlab
check_taper_model
cfg = struct('r1_mm',[21.25 21.5 21.75 22], ...
    'r2_mm',[16 16.25 16.5], 'l1_mm',[18 20 22], ...
    'l_mm',50:0.25:54, 'frequency_GHz',27.5:0.1:28.5);
T = search_te01_dimensions(cfg);
```

The numerical grid is a configurable example, not a claimed optimum. Confirm the intended geometry's dimension definitions. In the reference CAD parameterization, r1/r2 are radii, l is one straight-section length, and l1 is one taper length. The unfolded centerline length is `2*(l+l1+r1)`, while the single-direction air-cavity envelope is `l+l1+2*r1`. Wall thickness and flanges are excluded. These formulas must be checked against the actual CAD and must not be applied to arbitrary bends.

`minimum_envelope_mm` constrains the envelope, not unfolded length. Change the filtering equation if the user's requirement concerns unfolded length.

Retain a small set of candidates for actual center-frequency HFSS screening, then run the requested complete band for candidates meeting the center requirement. Save proxy and actual values in separate columns and include run status and mesh setup. Do not fill missing simulation results with predictions.

`fit_hfss_feasible_length.m` fits at least three actual HFSS samples at fixed r1/r2/l1 from CSV columns `l_mm,center`. The center values are fractional TE01 power, not percentages or amplitudes.

```matlab
R = fit_hfss_feasible_length('actual_hfss_samples.csv','candidate.json',0.981);
```

Its `final_verified=false` correctly marks a proposal. A quadratic fit can predict a feasible point that fails real HFSS; in such a case reject it and use actual evidence to select the next candidate. Meeting the user's requirements does not establish a global optimum.
