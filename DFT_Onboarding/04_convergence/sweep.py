#!/usr/bin/env python
"""
sweep.py -- run a convergence sweep over ENCUT or the k-point mesh.

Usage
-----
    python sweep.py encut
    python sweep.py encut --values 250 300 350 400 450 500 550 600
    python sweep.py kpoints --encut 500
    python sweep.py kpoints --values 3 5 7 9 11 13 --encut 500

Results are appended to encut_results.csv / kpoints_results.csv and printed
as a running table so you can watch convergence happen.

Before running, in this directory:
    cp ~/vasp_pseudo/Si/POTCAR POTCAR
and make sure VASP_STD is set (module 02).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import vasp_tools as vt

# --------------------------------------------------------------------------
# Defaults. These ranges are chosen to bracket convergence for silicon --
# ENMAX for the Si POTCAR is about 245 eV, so we start just below it and go
# well past. You should look at the resulting curve and decide whether the
# range was adequate; if the curve is still sloping at the last point, it
# was not.
# --------------------------------------------------------------------------
DEFAULT_ENCUT = [250, 300, 350, 400, 450, 500, 550, 600]
DEFAULT_NK = [3, 5, 7, 9, 11, 13]

# Fixed values used while sweeping the *other* parameter. The k-mesh here is
# deliberately generous so it is not the thing limiting the ENCUT sweep.
FIXED_NK_FOR_ENCUT = 9
FIXED_ENCUT_FOR_NK = 500


def sweep(kind: str, values: list[int], other: int) -> Path:
    """Run one sweep and write a CSV. Returns the CSV path."""
    incar_tpl = Path("INCAR.template").read_text()
    kpts_tpl = Path("KPOINTS.template").read_text()
    nat = vt.n_atoms()

    csv_path = Path(f"{kind}_results.csv")
    rows = []

    print(f"\nSweeping {kind.upper()} over {values}")
    print(f"  fixed: {'NK' if kind == 'encut' else 'ENCUT'} = {other}")
    print(f"  cell: {nat} atoms")
    print(f"  running on {vt.NPROC} cores\n")

    header = f"{'value':>8}  {'E (eV)':>16}  {'E/atom (eV)':>14}  {'wall (s)':>9}"
    print(header)
    print("-" * len(header))

    for v in values:
        if kind == "encut":
            encut, nk = v, other
        else:
            encut, nk = other, v

        workdir = Path(f"{kind}_{v:04d}")
        vt.prepare(workdir,
                   incar_tpl.replace("{ENCUT}", str(encut)),
                   kpts_tpl.replace("{NK}", str(nk)))

        try:
            with vt.Timer() as t:
                energy = vt.run_vasp(workdir)
        except vt.VaspError as exc:
            print(f"{v:>8}  FAILED: {exc}")
            continue

        rows.append({"value": v,
                     "encut": encut,
                     "nk": nk,
                     "natoms": nat,
                     "energy_eV": energy,
                     "energy_per_atom_eV": energy / nat,
                     "wall_s": round(t.elapsed, 1)})

        print(f"{v:>8}  {energy:>16.6f}  {energy / nat:>14.6f}  "
              f"{t.elapsed:>9.1f}")

    if not rows:
        print("\nNo calculations succeeded. Read a run.log before continuing.")
        sys.exit(1)

    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    _report(rows, kind)
    print(f"\nWrote {csv_path}")
    print(f"Now plot it:  python plot_convergence.py {kind}")
    return csv_path


def _report(rows: list[dict], kind: str) -> None:
    """Print convergence relative to the best-converged (last) point."""
    ref = rows[-1]["energy_per_atom_eV"]
    label = "ENCUT (eV)" if kind == "encut" else "k-mesh (n x n x n)"

    print(f"\nConvergence relative to the largest {kind} value tested")
    print(f"(reference: {rows[-1]['value']}, {ref:.6f} eV/atom)\n")
    print(f"{label:>20}  {'dE/atom (meV)':>15}  {'converged?':>12}")
    print("-" * 51)

    for r in rows:
        d_meV = (r["energy_per_atom_eV"] - ref) * 1000.0
        flag = "yes" if abs(d_meV) < 1.0 else ""
        print(f"{r['value']:>20}  {d_meV:>15.3f}  {flag:>12}")

    print("\n'converged?' marks |dE| < 1 meV/atom against the reference.")
    print("Choose the SMALLEST value that is converged -- larger is not")
    print("better, it is just slower, and you will run thousands of these.")

    print("\nCAUTION: the reference is the largest value you tested, not")
    print("truth. If the last few rows are still drifting in one direction,")
    print("your range was too narrow -- extend it and rerun.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", choices=["encut", "kpoints"])
    p.add_argument("--values", type=int, nargs="+", default=None,
                   help="values to sweep (defaults are sensible for Si)")
    p.add_argument("--nk", type=int, default=FIXED_NK_FOR_ENCUT,
                   help="fixed k-mesh while sweeping ENCUT")
    p.add_argument("--encut", type=int, default=FIXED_ENCUT_FOR_NK,
                   help="fixed ENCUT while sweeping the k-mesh")
    args = p.parse_args()

    vt.check_setup()

    if args.kind == "encut":
        values = args.values or DEFAULT_ENCUT
        sweep("encut", values, args.nk)
    else:
        values = args.values or DEFAULT_NK
        sweep("kpoints", values, args.encut)


if __name__ == "__main__":
    main()
