# Contributors

These tutorials are group teaching material, written to be person-agnostic so
they outlive any one student's time in the group — worked examples use
placeholder names. That applies to the *examples*, not to the people who built
this. Contributions are real work and are credited here.

If you contributed and are not listed, or are listed and would rather not be,
say so and it changes.

## Contributors

**Jaejun Lee** — wrote the original silicon VASP tutorial for the group's
campus cluster: the four-input-file walkthrough, the INCAR tag reference, and
the relax → SCF → non-SCF → band-structure workflow. Modules 00, 03, 05 and 06
are adapted from that work, and the `prep_bands.py` / `plot_bands.py` scripts
are substantially his.

**Alexander Jakopin** — first student through the restructured series, in
Fall 2026. Contributed the conda-only Apple Silicon build record
(`DFT_Onboarding/02_vasp_build_mac/BUILD_NOTES_2026-08_M5Pro.md`), and found
seven errors in the modules by hitting every one of them in practice —
including the k-point density conventions being conflated in module 04, and
`check_setup.py` hard-coding the wrong POTCAR set.

## Reporting problems

If instructions here are wrong or incomplete on your machine, fix them and
open a PR. The corrections a newcomer finds are exactly the ones the author
cannot see — most of the fixes in this repo arrived that way.
