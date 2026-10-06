# 电磁仿真 Skills

Reusable electromagnetic-engineering Agent Skills by [shao36058-png](https://github.com/shao36058-png). Repository: [shao36058-png/skills](https://github.com/shao36058-png/skills).

## HFSS TE01 Bend Engineering

A reusable Agent Skill for convergence diagnosis, MATLAB dimension screening, actual HFSS modal acceptance, memory-guarded solves, and reproducible delivery of TE01 overmoded circular-waveguide 90-degree miter bends.

Skill directory: [skills/hfss-te01-bend](skills/hfss-te01-bend/SKILL.md). It uses the standard `SKILL.md` format plus supporting scripts and references.

This public package contains no original `.aedt` project, native field/mesh results, personal workstation paths, private project history, or thesis PDF. The numerical search grids are illustrative. The owner's local project-specific skill remains separate.

## Dependencies and scope

- CSV acceptance: Python standard library only; never connects to HFSS.
- Solver guard: Windows, psutil, PyAEDT, and a user-owned licensed HFSS installation; reference environment HFSS 2025.2/PyAEDT 1.1.0.
- MATLAB screening: user-owned licensed MATLAB; reference environment R2024b.
- The method preserves the requested miter-bend topology and accepts results from real HFSS modal data. It does not guarantee a particular efficiency for arbitrary dimensions.

The CSV helper has been checked against real saved data and invalid/incomplete samples. MATLAB source files are unchanged from the reference project. The guard's portability edits have been syntax checked; this release task does not run another full-wave simulation.

## Example use

Install this individual skill with the [open skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add shao36058-png/skills --skill hfss-te01-bend
```

This command requires the skill files to have been uploaded to the public repository. Installing the skill does not install HFSS, MATLAB, or their licenses.

Copy the skill directory into the supported skill directory of your agent, then invoke `$hfss-te01-bend` to review an existing project or request an authorized solve.

```bash
python skills/hfss-te01-bend/scripts/verify_band.py --csv path/to/band.csv
```

Use the workflow documentation to configure the solver guard. Do not execute it solely to inspect existing results.

## License and discovery

MIT License, copyright 2026 shao36058-png. See [LICENSE](LICENSE). This license applies to this repository's distributable code and instructions, not to HFSS, MATLAB, or the referenced thesis.

SkillsMP indexes public GitHub repositories; publication to GitHub does not guarantee indexing or a review outcome. See [SkillsMP About](https://skillsmp.com/about) and the [Agent Skills specification](https://agentskills.io/specification).
