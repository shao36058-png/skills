# 电磁仿真 Skills

Reusable electromagnetic-engineering Agent Skills by [shao36058-png](https://github.com/shao36058-png). Repository: [shao36058-png/skills](https://github.com/shao36058-png/skills).

## Available skills

| Skill | Purpose |
|---|---|
| [hfss-te01-bend](skills/hfss-te01-bend/SKILL.md) | TE01-to-TE01 circular-waveguide miter-bend convergence, MATLAB screening and modal acceptance |
| [hfss-te10-te01-converter](skills/hfss-te10-te01-converter/SKILL.md) | Rectangular TE10-to-circular TE01 converter reproduction, port cutoff checks and saved modal-result auditing |
| [hfss-te01-directional-coupler](skills/hfss-te01-directional-coupler/SKILL.md) | Circular TE01 orthogonal two-hole coupler: wave ports, broad-wall geometry, hole pitch, weak-signal convergence and saved-result audit |

These skills cover different components. Match apertures, reference planes and full modal bases before claiming performance of a combined transmission chain.

## HFSS TE01 Bend Engineering

A reusable Agent Skill for convergence diagnosis, MATLAB dimension screening, actual HFSS modal acceptance, memory-guarded solves, and reproducible delivery of TE01 overmoded circular-waveguide 90-degree miter bends.

Skill directory: [skills/hfss-te01-bend](skills/hfss-te01-bend/SKILL.md). It uses the standard `SKILL.md` format plus supporting scripts and references.

This public package contains no original `.aedt` project, native field/mesh results, personal workstation paths, private project history, or thesis PDF. The numerical search grids are illustrative. The owner's local project-specific skill remains separate.

## Dependencies and scope

- CSV acceptance: Python standard library only; never connects to HFSS.
- Solver guard: Windows, psutil, PyAEDT, and a user-owned licensed HFSS installation; reference environment HFSS 2025.2/PyAEDT 1.1.0.
- MATLAB screening: user-owned licensed MATLAB; reference environment R2024b.
- The method preserves the requested miter-bend topology and accepts results from real HFSS modal data. It does not guarantee a particular efficiency for arbitrary dimensions.

The bend CSV helper has been checked against real saved data and invalid/incomplete samples. MATLAB source files are unchanged from the reference project. The guard's portability edits have been syntax checked; skill creation does not run another full-wave simulation.

## HFSS TE10 to TE01 Converter

The converter skill organizes the cumulative TE10→TE20→cross-guide TE22→circular TE01 design method, geometry/cutoff constraints, and converter-to-bend interface checks. It includes standard-library cutoff and modal-audit helpers and a PyAEDT exporter that reads an explicitly selected existing desktop's saved data.

The exporter and metrics were exercised on real saved HFSS 2025.2/PyAEDT 1.1.0 converter results. Those results showed high target transmission, but native convergence and output-port completeness remained pending. This is validation of the inspection workflow, not a certified reference design. No additional full-wave solve was run. No dedicated converter MATLAB surrogate is included or claimed as validated.

Install the converter skill:

```bash
npx skills add shao36058-png/skills --skill hfss-te10-te01-converter
```

Invoke `$hfss-te10-te01-converter` with an open project or a saved modal export. Use `scripts/modal_metrics.py` for saved-result review; the exporter does not launch a solve. The portable skill contains no private workstation paths, original project, thesis PDF or native field data.

## HFSS TE01 Directional Coupler

This skill packages the best verified simplified 24 GHz circular TE01-to-rectangular-waveguide directional coupler. It includes one portable HFSS model archive without native field/mesh results, a read-only PyAEDT exporter, a standard-library CSV audit helper, and five solved reference frequency samples.

At 24 GHz the reference model gives -62.35 dB coupled output, -109.80 dB isolated output and 47.45 dB directivity. Its actual hole-center pitches are X=4.90 mm and Z=5.04 mm. These optimized pitches differ from the paper's 2.45/2.44 mm labels; the package does not establish that the paper labels represent half-offsets. Standard-waveguide and transition sections described in the paper remain outside this simplified model. Five samples do not certify a continuously scanned bandwidth.

The archive was restored and its geometry, ports and unique design/setup validated. The exporter was exercised against the saved best-design data, and the CSV auditor was checked against real results and invalid data. Creation of this skill did not launch another full-wave solve. A licensed HFSS installation is required to restore and solve the model; neither HFSS nor the source paper PDF is included.

Install and invoke:

```bash
npx skills add shao36058-png/skills --skill hfss-te01-directional-coupler
```

Invoke `$hfss-te01-directional-coupler`, or audit the included reference data:

```bash
python skills/hfss-te01-directional-coupler/scripts/coupler_metrics.py --csv skills/hfss-te01-directional-coupler/assets/reference-results.csv --min-directivity 40
```

## Example use

Install this individual skill with the [open skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add shao36058-png/skills --skill hfss-te01-bend
```

Installing the skill does not install HFSS, MATLAB, or their licenses.

Copy the skill directory into the supported skill directory of your agent, then invoke `$hfss-te01-bend` to review an existing project or request an authorized solve.

```bash
python skills/hfss-te01-bend/scripts/verify_band.py --csv path/to/band.csv
```

Use the workflow documentation to configure the solver guard. Do not execute it solely to inspect existing results.

## License and discovery

MIT License, copyright 2026 shao36058-png. See [LICENSE](LICENSE). This license applies to this repository's distributable code and instructions, not to HFSS, MATLAB, or the referenced thesis.

SkillsMP indexes public GitHub repositories; publication to GitHub does not guarantee indexing or a review outcome. See [SkillsMP About](https://skillsmp.com/about) and the [Agent Skills specification](https://agentskills.io/specification).
