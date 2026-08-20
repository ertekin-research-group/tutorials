#!/usr/bin/env python
"""
analyze_relax.py -- report the relaxed silicon structure and compare it to
experiment.

Run this after run_local.sh finishes:

    python analyze_relax.py
"""
from __future__ import annotations

from pathlib import Path

from pymatgen.core import Structure
from pymatgen.io.vasp import Outcar
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

# Silicon, room temperature. This is the number you are trying to reproduce.
A_EXPERIMENT = 5.431

HERE = Path(__file__).resolve().parent


def main() -> None:
    for f in ("POSCAR", "CONTCAR", "OUTCAR"):
        if not (HERE / f).is_file():
            raise SystemExit(f"Missing {f} -- run ./run_local.sh first.")

    initial = Structure.from_file(HERE / "POSCAR")
    final = Structure.from_file(HERE / "CONTCAR")
    outcar = Outcar(str(HERE / "OUTCAR"))

    text = (HERE / "OUTCAR").read_text()
    converged = "reached required accuracy" in text
    n_ionic = text.count("free  energy   TOTEN")

    a_i, a_f = initial.lattice.a, final.lattice.a
    sg = SpacegroupAnalyzer(final, symprec=1e-3).get_space_group_symbol()

    print("\n" + "=" * 60)
    print("  Silicon cell relaxation")
    print("=" * 60)

    print(f"\nIonic steps taken:      {n_ionic}")
    print(f"Force criterion met:    {'yes' if converged else 'NO'}")
    if not converged:
        print("  -> do not use these numbers; raise NSW and restart from CONTCAR")

    print(f"\n{'':22} {'initial':>12} {'relaxed':>12}")
    print("-" * 48)
    print(f"{'lattice constant a':22} {a_i:>12.4f} {a_f:>12.4f}   Angstrom")
    print(f"{'cell volume':22} {initial.volume:>12.3f} "
          f"{final.volume:>12.3f}   Angstrom^3")

    print(f"\nSpace group of relaxed cell: {sg}")
    if sg != "Fd-3m":
        print("  WARNING: expected Fd-3m for diamond silicon. Something moved")
        print("           that should not have -- check ISYM and the POSCAR.")

    err = (a_f - A_EXPERIMENT) / A_EXPERIMENT * 100.0
    print(f"\nExperiment:  a = {A_EXPERIMENT:.4f} Angstrom")
    print(f"This work:   a = {a_f:.4f} Angstrom")
    print(f"Error:       {err:+.3f}%  ({a_f - A_EXPERIMENT:+.4f} Angstrom)")

    print(f"\nFinal energy: {outcar.final_energy:.6f} eV "
          f"({outcar.final_energy / len(final):.6f} eV/atom)")

    print("\n" + "-" * 60)
    print("Interpreting the error")
    print("-" * 60)
    if err > 0:
        print("Your lattice constant is LARGER than experiment. This is the")
        print("expected direction for PBE, which systematically underbinds")
        print("and overestimates lattice constants of covalent semiconductors")
        print("by a few tenths of a percent.")
        print()
        print("This residual is PHYSICS, not numerics. It will not go away")
        print("with a higher ENCUT or a denser k-mesh -- you converged those")
        print("in module 04. It is a property of the functional.")
        if err > 1.5:
            print()
            print("However: more than about 1.5% is larger than PBE's usual")
            print("error for silicon. Check that you actually used your")
            print("converged ENCUT, and re-read module 04 Part D on Pulay")
            print("stress.")
    else:
        print("Your lattice constant is SMALLER than experiment, which is")
        print("unusual for PBE on silicon -- PBE normally overestimates.")
        print("Worth checking your ENCUT and POTCAR choice before believing it.")

    print("\nWrite this comparison into your report. Being able to say")
    print("'my error is +0.4% and that is the known PBE bias' is a different")
    print("thing from 'my number does not match and I do not know why'.\n")


if __name__ == "__main__":
    main()
