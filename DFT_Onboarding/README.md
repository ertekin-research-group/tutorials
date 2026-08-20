# Getting Started: DFT for Defects in Semiconductors

**Open [`index.html`](index.html) in a browser to begin.** These are HTML
pages with a shared stylesheet — no build step, no server, no dependencies.
Cloning the repo and opening `index.html` is the intended workflow.

## What this series covers

Eight modules taking a newcomer from a fresh Mac to a full DFT workflow.
Laptop-first by design: modules 00–06 need nothing but your own machine, and
the cluster does not appear until module 07.

| Module | Topic | Assigned week |
|---|---|---|
| [`00_shell_basics`](00_shell_basics/) | Command line on macOS | 1 |
| [`01_toolchain`](01_toolchain/) | miniforge, conda env, Git, MP API key, POTCARs | 1 |
| [`02_vasp_build_mac`](02_vasp_build_mac/) | Compiling VASP, conda-only toolchain | 2 |
| [`03_vasp_inputs`](03_vasp_inputs/) | The four input files; running locally | 2 |
| [`04_convergence`](04_convergence/) | ENCUT and k-mesh convergence; Pulay stress | 4 |
| [`05_si_relax`](05_si_relax/) | Cell relaxation; error vs experiment | 5 |
| [`06_si_bands`](06_si_bands/) | Band structure; the band gap problem | 5 |
| [`07_hpc_slurm`](07_hpc_slurm/) | SSH, Lmod, SLURM, rsync | 12 |

Week numbers refer to a first-semester onboarding plan; ignore them if you
are working through this on your own.

## Note on module ordering

Convergence testing (04) comes **before** the first relaxation (05). This is
deliberate: an unconverged plane-wave cutoff produces Pulay stress, which
specifically corrupts cell relaxations, so a lattice constant relaxed at low
`ENCUT` is wrong for a reason no amount of careful relaxation will fix.
Module 04 includes a script that demonstrates this on silicon.

## What you need to supply

Nothing licensed ships with these tutorials:

- **POTCAR files** — ask Elif. Every module needing one says so.
- **VASP source** — ask Elif. Module 02 covers building it.
- **A Materials Project API key** — free, from materialsproject.org.

## Placeholders to replace

- `ENCUT = 450` in modules 05 and 06 — intentional. Replace with the value
  *you* converge in module 04.
- `cluster.address.edu`, `~/bin/vasp_std`, and the Intel module versions in
  `07_hpc_slurm/vasp_submit` — cluster-specific; adjust for your account.
  These affect cluster runs only, never local ones.

## Found something wrong?

Fix it and open a PR. Every module asks its reader to keep notes on what did
not work as written; those notes are the intended source of improvements.
