#!/usr/bin/env python
"""
pulay_demo.py -- show why convergence must come BEFORE relaxation.

This is the experiment that justifies the ordering of modules 04 and 05.

The idea
--------
Relax the silicon cell (ISIF = 3, so both ions and cell are free) twice:
once with a deliberately low ENCUT, once with a well-converged ENCUT.
Compare the resulting lattice constants.

They will differ -- and not by a little. The low-ENCUT run does not just
give a noisier answer, it gives a systematically WRONG one, biased in a
predictable direction.

Why
---
The stress tensor VASP computes is the derivative of the energy with respect
to strain at FIXED basis set. But the plane-wave basis set is defined by a
cutoff energy in reciprocal space, so when the cell changes shape or volume,
the number of plane waves that fit under the cutoff changes too. The
calculated stress therefore misses a term -- the derivative with respect to
the changing basis. That missing term is Pulay stress.

It shrinks as ENCUT grows (a denser basis is less sensitive to the boundary),
and it is essentially absent for fixed-cell calculations, where the basis
never changes. This is exactly why:

  * convergence testing is done on a FIXED structure (module 04), and
  * cell relaxation is only trustworthy afterwards (module 05).

Usage
-----
    python pulay_demo.py                        # 250 vs 550 eV
    python pulay_demo.py --low 220 --high 600
"""
from __future__ import annotations

import argparse
from pathlib import Path

import vasp_tools as vt

# Experimental cubic lattice constant of silicon at room temperature.
A_EXPERIMENT = 5.431


def relax_at(encut: int, nk: int) -> dict:
    """Run a full cell relaxation at one ENCUT; return the result."""
    incar = Path("INCAR.relax.template").read_text().replace("{ENCUT}",
                                                             str(encut))
    kpts = Path("KPOINTS.template").read_text().replace("{NK}", str(nk))
    workdir = Path(f"pulay_encut_{encut:04d}")
    vt.prepare(workdir, incar, kpts)

    print(f"  relaxing at ENCUT = {encut} eV ...", end="", flush=True)
    with vt.Timer() as t:
        energy = vt.run_vasp(workdir)
    a, vol = vt.lattice_from_contcar(workdir)
    conv = vt.ionic_converged(workdir)
    print(f" done ({t.elapsed:.0f} s)")

    if not conv:
        print(f"    WARNING: ionic relaxation did not reach the force "
              f"criterion. Raise NSW.")

    return {"encut": encut, "a": a, "volume": vol,
            "energy": energy, "converged": conv}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--low", type=int, default=250,
                   help="deliberately under-converged cutoff (eV)")
    p.add_argument("--high", type=int, default=550,
                   help="well-converged cutoff (eV)")
    p.add_argument("--nk", type=int, default=9, help="k-mesh subdivisions")
    args = p.parse_args()

    vt.check_setup()
    nat = vt.n_atoms()

    print("\nPulay stress demonstration")
    print("=" * 62)
    print("Relaxing the SAME cell twice, changing only ENCUT.\n")

    lo = relax_at(args.low, args.nk)
    hi = relax_at(args.high, args.nk)

    print("\n" + "=" * 62)
    print(f"{'ENCUT (eV)':>12}  {'a (Ang)':>10}  {'volume (Ang^3)':>15}  "
          f"{'err vs expt':>12}")
    print("-" * 62)
    for r in (lo, hi):
        err = (r["a"] - A_EXPERIMENT) / A_EXPERIMENT * 100.0
        print(f"{r['encut']:>12}  {r['a']:>10.4f}  {r['volume']:>15.3f}  "
              f"{err:>11.2f}%")

    da = lo["a"] - hi["a"]
    dvol = (lo["volume"] - hi["volume"]) / hi["volume"] * 100.0

    print("-" * 62)
    print(f"\nDifference in lattice constant: {da:+.4f} Ang "
          f"({da / hi['a'] * 100:+.2f}%)")
    print(f"Difference in cell volume:      {dvol:+.2f}%")
    print(f"\nExperimental a = {A_EXPERIMENT} Ang")

    print("\nWhat to take from this")
    print("-" * 62)
    print("Both runs relaxed successfully. Neither reported an error. The")
    print("low-ENCUT run produced a confident, converged, WRONG lattice")
    print("constant -- and nothing in its output says so.")
    print()
    print("That is the whole argument for module 04 preceding module 05.")
    print("You cannot detect this by looking at one calculation; you can")
    print("only detect it by having converged your parameters first.")
    print()
    print("Note also that the well-converged PBE result will still sit")
    print("slightly ABOVE experiment. That residual error is physics, not")
    print("numerics -- it is PBE's known tendency to overbind slightly and")
    print("no amount of convergence will remove it. Distinguishing 'my")
    print("numerics are not converged' from 'this functional has a known")
    print("systematic error' is a skill worth acquiring early.")

    print(f"\n({nat} atoms per cell; results in "
          f"pulay_encut_{args.low:04d}/ and pulay_encut_{args.high:04d}/)")


if __name__ == "__main__":
    main()
