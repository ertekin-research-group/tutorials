# Ertekin Research Group — Tutorials

Shared, reusable teaching material for the group. Unlike the
`YYYY-Name-Topic` project repositories, content here is meant to outlive any
one student's project and to be improved by whoever uses it next.

## Contents

### [`DFT_Onboarding/`](DFT_Onboarding/) — getting started with plane-wave DFT

An eight-module, laptop-first series taking someone from a fresh MacBook to a
complete DFT workflow: building VASP from source, converging numerical
parameters, relaxing a crystal, computing a band structure, and moving the
whole thing onto the campus cluster. Written for someone who has never
compiled a code, run a DFT calculation, or used Git.

**Start at [`DFT_Onboarding/index.html`](DFT_Onboarding/index.html)** — open
it in a browser.

| Module | Topic |
|---|---|
| `00_shell_basics` | Command line on macOS |
| `01_toolchain` | miniforge, conda env, Git, Materials Project, POTCARs |
| `02_vasp_build_mac` | Compiling VASP with a conda-only toolchain |
| `03_vasp_inputs` | POSCAR, POTCAR, INCAR, KPOINTS; running locally |
| `04_convergence` | ENCUT and k-mesh convergence; Pulay stress |
| `05_si_relax` | Cell relaxation; comparing to experiment |
| `06_si_bands` | SCF/non-SCF band structure; the DFT band gap problem |
| `07_hpc_slurm` | SSH, Lmod, SLURM, rsync; moving to the cluster |

Modules 00–06 run entirely on a laptop. Module 07 is only needed once
calculations outgrow it.

### [`O2_ChemPot/`](O2_ChemPot/) — oxygen chemical potentials

Mathematica notebook and write-up on oxygen reference energies and chemical
potentials. Directly relevant to defect formation energies in oxides, where
the O₂ reference is a well-known difficulty.

## Conventions

- **No licensed material, ever.** VASP source and POTCAR files are licensed
  and must never be committed here or anywhere else. Tutorials instruct
  readers to obtain them from Elif.
- **No large binaries.** Tutorials ship inputs and scripts; readers generate
  their own output.
- **Fix what you find.** If instructions are wrong or incomplete on your
  machine, correct them and open a PR. That is how this gets better — the
  corrections a newcomer finds are exactly the ones an expert cannot see.

## Contributing

Tutorials are plain HTML with a shared stylesheet
(`DFT_Onboarding/style.css`), so they render from disk with no build step and
no dependencies. Keep it that way.
