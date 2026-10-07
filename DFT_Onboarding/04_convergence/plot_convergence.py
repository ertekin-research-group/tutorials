#!/usr/bin/env python
"""
plot_convergence.py -- plot a convergence sweep and report the converged value.

Usage
-----
    python plot_convergence.py encut
    python plot_convergence.py kpoints
    python plot_convergence.py encut --tol 5          # tolerance, meV/atom
    python plot_convergence.py encut --enmax 400      # grey out points below the floor

Produces <kind>_convergence.png: energy per atom with a shaded tolerance band
around the reference, and the deviation from that reference on a log scale.

The converged value is the smallest one beyond which *every* point stays
inside the band -- not merely the first point that dips into it. A single
value can wander inside the band and back out again, especially below the
pseudopotential's own ENMAX, and that is not convergence.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402

LABELS = {"encut": "ENCUT (eV)", "kpoints": "k-mesh divisions along the longest b"}
DEFAULT_TOL = 10.0      # meV/atom; 0.01 eV/atom


def load(kind: str) -> list[dict]:
    path = Path(f"{kind}_results.csv")
    if not path.is_file():
        sys.exit(f"{path} not found. Run:  python sweep.py {kind}")
    with path.open() as fh:
        rows = [{k: float(v) for k, v in r.items() if v not in ("", None)}
                for r in csv.DictReader(fh)]
    return sorted(rows, key=lambda r: r["value"])


def converged_value(xs, devs, tol):
    """Smallest x beyond which every point stays inside the band."""
    for i, x in enumerate(xs):
        if all(d < tol for d in devs[i:]):
            return x
    return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=["encut", "kpoints"])
    p.add_argument("--tol", type=float, default=DEFAULT_TOL,
                   help=f"convergence tolerance in meV/atom (default {DEFAULT_TOL:g})")
    p.add_argument("--enmax", type=float, default=None,
                   help="largest POTCAR ENMAX; points below it are excluded")
    args = p.parse_args()

    rows = load(args.kind)
    x = [r["value"] for r in rows]
    e = [r["energy_per_atom_eV"] for r in rows]
    ref = e[-1]
    dev = [abs((v - ref) * 1000.0) for v in e]

    # Points below the pseudopotential's own cutoff are not meaningful.
    floor = args.enmax if (args.enmax and args.kind == "encut") else None
    usable = [i for i, xi in enumerate(x) if floor is None or xi >= floor]
    if floor is not None and not usable:
        sys.exit(f"Every point is below ENMAX = {floor:g} eV. Sweep higher.")

    conv = converged_value([x[i] for i in usable[:-1]],
                           [dev[i] for i in usable[:-1]], args.tol)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    band_lo = (ref - args.tol / 1000.0)
    band_hi = (ref + args.tol / 1000.0)
    ax1.axhspan(band_lo, band_hi, color="#2e7d32", alpha=.15,
                label=f"reference ± {args.tol:g} meV/atom")
    ax1.axhline(ref, color="#2e7d32", lw=1, ls="--")
    ax1.plot(x, e, "o-", color="#1f4e79", lw=1.6, ms=6)
    if floor is not None:
        ax1.axvspan(min(x) - 1, floor, color="#c0392b", alpha=.10)
        ax1.text(floor, max(e), "  below ENMAX", color="#c0392b",
                 fontsize=8, va="top")
    if conv is not None:
        ax1.axvline(conv, ls=":", color="#2e7d32")
    ax1.set_xlabel(LABELS[args.kind])
    ax1.set_ylabel("Energy per atom (eV)")
    ax1.set_title("Energy per atom, with tolerance band", fontsize=10)
    ax1.legend(fontsize=8)
    ax1.grid(alpha=.3)

    ax2.semilogy([x[i] for i in usable[:-1]],
                 [max(dev[i], 1e-4) for i in usable[:-1]],
                 "o-", color="#c0392b", lw=1.6, ms=6)
    ax2.axhline(args.tol, ls="--", color="#2e7d32",
                label=f"{args.tol:g} meV/atom")
    if conv is not None:
        ax2.axvline(conv, ls=":", color="#2e7d32",
                    label=f"converged at {conv:g}")
    ax2.set_xlabel(LABELS[args.kind])
    ax2.set_ylabel("|E − E_ref| per atom (meV)")
    ax2.set_title("Deviation from reference (log scale)", fontsize=10)
    ax2.grid(alpha=.3, which="both")
    ax2.legend(fontsize=8)

    fig.suptitle(f"{args.kind} convergence", fontweight="bold")
    fig.tight_layout()
    out = Path(f"{args.kind}_convergence.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")

    print(f"\nSaved {out}")
    print(f"Criterion: energy per atom within ±{args.tol:g} meV/atom "
          f"({args.tol / 1000:g} eV/atom) of the reference,")
    print(f"           and staying inside the band for every larger value.")
    print(f"Reference: {LABELS[args.kind]} = {x[-1]:g}, {ref:.6f} eV/atom")
    if floor is not None:
        n_excl = len(x) - len(usable)
        print(f"Excluded:  {n_excl} point(s) below ENMAX = {floor:g} eV")

    if conv is None:
        print(f"\nNOT CONVERGED to ±{args.tol:g} meV/atom below the reference.")
        print("The energy is still moving at the top of your range. Extend it")
        print("upward and rerun -- do not adopt the largest value you happened")
        print("to test.")
    else:
        cost = next(r["wall_s"] for r in rows if r["value"] == conv)
        print(f"\nConverged at {LABELS[args.kind]} = {conv:g}  ({cost:.0f} s per run)")
        print(f"Most expensive run tested: {rows[-1]['wall_s']:.0f} s")
        print("\nUse this value, not the largest one. Write it down with this")
        print("plot as the evidence.")


if __name__ == "__main__":
    main()
