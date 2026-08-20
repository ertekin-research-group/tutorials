#!/usr/bin/env python
"""
plot_convergence.py -- plot a convergence sweep and report the converged value.

Usage
-----
    python plot_convergence.py encut
    python plot_convergence.py kpoints
    python plot_convergence.py encut --tol 0.5     # tolerance in meV/atom

Produces <kind>_convergence.png with two panels: the absolute energy per
atom, and the difference from the reference on a log scale. The second panel
is the one that actually tells you where convergence happens -- on the first
panel everything looks flat.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402

LABELS = {"encut": "ENCUT (eV)", "kpoints": "k-mesh subdivisions (n)"}


def load(kind: str) -> list[dict]:
    path = Path(f"{kind}_results.csv")
    if not path.is_file():
        sys.exit(f"{path} not found. Run:  python sweep.py {kind}")
    with path.open() as fh:
        rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(fh)]
    return sorted(rows, key=lambda r: r["value"])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=["encut", "kpoints"])
    p.add_argument("--tol", type=float, default=1.0,
                   help="convergence tolerance in meV/atom (default 1.0)")
    args = p.parse_args()

    rows = load(args.kind)
    x = [r["value"] for r in rows]
    e = [r["energy_per_atom_eV"] for r in rows]
    ref = e[-1]
    d_meV = [abs((v - ref) * 1000.0) for v in e]

    # Smallest value meeting the tolerance.
    #
    # Note that the reference point is EXCLUDED from the candidates. Its
    # deviation from itself is trivially zero, so including it would make
    # every sweep self-report as converged -- which is exactly backwards:
    # if only the largest value "converges", the sweep has not converged
    # at all and the range needs extending.
    converged = next((xi for xi, di in zip(x[:-1], d_meV[:-1])
                      if di < args.tol), None)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    ax1.plot(x, e, "o-", color="#1f4e79", lw=1.6, ms=6)
    ax1.set_xlabel(LABELS[args.kind])
    ax1.set_ylabel("Energy per atom (eV)")
    ax1.set_title("Absolute energy\n(looks flat -- this panel misleads)",
                  fontsize=10)
    ax1.grid(alpha=.3)

    # the log panel: drop the reference point itself, whose delta is 0
    ax2.semilogy(x[:-1], [max(d, 1e-4) for d in d_meV[:-1]],
                 "o-", color="#c0392b", lw=1.6, ms=6)
    ax2.axhline(args.tol, ls="--", color="#2e7d32",
                label=f"{args.tol:g} meV/atom tolerance")
    if converged is not None:
        ax2.axvline(converged, ls=":", color="#2e7d32",
                    label=f"converged at {converged:g}")
    ax2.set_xlabel(LABELS[args.kind])
    ax2.set_ylabel("|E - E_ref| per atom (meV)")
    ax2.set_title("Deviation from reference\n(this is the useful panel)",
                  fontsize=10)
    ax2.grid(alpha=.3, which="both")
    ax2.legend(fontsize=8)

    fig.suptitle(f"Silicon {args.kind} convergence", fontweight="bold")
    fig.tight_layout()
    out = Path(f"{args.kind}_convergence.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")

    print(f"\nSaved {out}")
    print(f"Reference: {LABELS[args.kind]} = {x[-1]:g}, {ref:.6f} eV/atom")
    if converged is None:
        print(f"\nNOT CONVERGED: no value below the reference met the "
              f"{args.tol:g} meV/atom tolerance.")
        print("The energy is still changing at the top of your range, so the")
        print("range is too narrow. Extend it upward and rerun -- do not")
        print("simply adopt the largest value you happened to test.")
    else:
        cost = next(r["wall_s"] for r in rows if r["value"] == converged)
        print(f"\nConverged to {args.tol:g} meV/atom at "
              f"{LABELS[args.kind]} = {converged:g}  ({cost:.0f} s per run)")
        print(f"Most expensive run tested: {rows[-1]['wall_s']:.0f} s")
        print("\nUse the converged value, not the largest one. Write it down,")
        print("with this plot as the evidence -- every calculation you report")
        print("for the rest of the semester cites this.")


if __name__ == "__main__":
    main()
