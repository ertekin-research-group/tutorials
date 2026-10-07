"""
vasp_tools.py -- small shared helpers for running and parsing VASP.

Deliberately plain: no pymatgen, only the standard library. The point is
that you can read every line of this and know exactly what it does. You
will use pymatgen's parsers later (module 06 onwards) once you trust them,
but the first time you extract an energy from an OUTCAR you should see
exactly how it is done.
"""
from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

# --------------------------------------------------------------------------
# Configuration -- read from the environment so nothing is hard-coded to one
# machine. Set these in ~/.zshrc (see module 02).
# --------------------------------------------------------------------------
VASP_STD = os.environ.get("VASP_STD")
NPROC = int(os.environ.get("VASP_NP", "8"))

# The final total energy line in OUTCAR looks like:
#   free  energy   TOTEN  =       -43.58912550 eV
# Note the irregular internal spacing -- match on \s+ rather than exact runs.
_TOTEN = re.compile(r"free\s+energy\s+TOTEN\s*=\s*(-?\d+\.?\d*)")

# VASP prints this when the electronic loop hits EDIFF (i.e. it converged).
_EDIFF_REACHED = "aborting loop because EDIFF is reached"

# VASP prints this when an ionic relaxation converges on forces.
_FORCES_REACHED = "reached required accuracy"


class VaspError(RuntimeError):
    """Raised when a calculation fails or produces an unusable result."""


def check_setup() -> None:
    """Fail early and clearly if the environment is not ready."""
    if VASP_STD is None:
        raise VaspError(
            "VASP_STD is not set. Add this to ~/.zshrc:\n"
            '    export VASP_STD="$HOME/software/vasp.6.x.x/bin/vasp_std"\n'
            "then open a new terminal.")
    if not Path(VASP_STD).is_file():
        raise VaspError(f"VASP_STD points at {VASP_STD}, which is not a file.")
    if shutil.which("mpirun") is None:
        raise VaspError("mpirun not found. Did you `conda activate defects`?")
    if not Path("POTCAR").is_file():
        raise VaspError(
            "No POTCAR in this directory. Copy one here first:\n"
            "    cp ~/vasp_pseudo/Si/POTCAR POTCAR\n"
            "(POTCARs are licensed, which is why one is not shipped with "
            "these tutorials.)")


def n_atoms(poscar: Path = Path("POSCAR")) -> int:
    """Number of atoms in a POSCAR: sum of the counts on line 7."""
    lines = poscar.read_text().splitlines()
    return sum(int(n) for n in lines[6].split())


def run_vasp(workdir: Path, quiet: bool = True) -> float:
    """
    Run VASP in `workdir` and return the final total energy in eV.

    Raises VaspError if the run fails or the electronic loop did not
    converge -- an unconverged number is worse than no number, because it
    looks like data.
    """
    log = workdir / "run.log"
    cmd = ["mpirun", "-np", str(NPROC), VASP_STD]

    with log.open("w") as fh:
        proc = subprocess.run(cmd, cwd=workdir, stdout=fh,
                              stderr=subprocess.STDOUT)

    if proc.returncode != 0:
        raise VaspError(f"VASP exited with code {proc.returncode}. "
                        f"See {log}")

    outcar = workdir / "OUTCAR"
    if not outcar.is_file():
        raise VaspError(f"No OUTCAR produced in {workdir}. See {log}")

    text = outcar.read_text()

    energies = _TOTEN.findall(text)
    if not energies:
        raise VaspError(f"No total energy found in {outcar}. "
                        "The run probably died early -- read the OUTCAR.")

    # A static run converges the electronic loop once; a relaxation does so
    # once per ionic step. Either way we require at least one.
    if _EDIFF_REACHED not in text:
        raise VaspError(
            f"Electronic loop did NOT converge in {workdir}. "
            "Raise NELM, or loosen EDIFF, but do not use this number.")

    return float(energies[-1])


def ionic_converged(workdir: Path) -> bool:
    """True if an ionic relaxation reached its force criterion."""
    outcar = workdir / "OUTCAR"
    return outcar.is_file() and _FORCES_REACHED in outcar.read_text()


def lattice_from_contcar(workdir: Path) -> tuple[float, float]:
    """
    Return (a, volume) from a CONTCAR, in Angstrom and Angstrom^3.

    Assumes the cubic-ish conventional silicon cell, where the length of
    the first lattice vector is the cubic lattice constant.
    """
    lines = (workdir / "CONTCAR").read_text().splitlines()
    scale = float(lines[1])
    vecs = [[float(x) * scale for x in lines[i].split()[:3]]
            for i in (2, 3, 4)]

    def norm(v):
        return sum(c * c for c in v) ** 0.5

    a = norm(vecs[0])
    # scalar triple product = cell volume
    (a1, a2, a3), (b1, b2, b3), (c1, c2, c3) = vecs
    vol = abs(a1 * (b2 * c3 - b3 * c2)
              - a2 * (b1 * c3 - b3 * c1)
              + a3 * (b1 * c2 - b2 * c1))
    return a, vol


def prepare(workdir: Path, incar_text: str, kpoints_text: str) -> None:
    """Create a run directory with all four input files."""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "INCAR").write_text(incar_text)
    (workdir / "KPOINTS").write_text(kpoints_text)
    shutil.copy("POSCAR", workdir / "POSCAR")
    shutil.copy("POTCAR", workdir / "POTCAR")


class Timer:
    """Context manager returning elapsed wall time in seconds."""

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self._t0
        return False

# --------------------------------------------------------------------------
# Cell geometry and pseudopotential limits
# --------------------------------------------------------------------------
def potcar_enmax(potcar: Path = Path("POTCAR")) -> float:
    """
    Largest ENMAX in the POTCAR, in eV.

    Every pseudopotential states its own minimum recommended plane-wave
    cutoff. The largest one in a multi-element system is the floor for the
    whole calculation: below it the numbers are not merely unconverged, they
    are meaningless.
    """
    vals = []
    for line in potcar.read_text(errors="ignore").splitlines():
        if "ENMAX" in line:
            # e.g.  "   ENMAX  =  400.000; ENMIN  =  300.000 eV"
            m = re.search(r"ENMAX\s*=\s*([\d.]+)", line)
            if m:
                vals.append(float(m.group(1)))
    if not vals:
        raise VaspError(f"No ENMAX found in {potcar}")
    return max(vals)


def lattice_vectors(poscar: Path = Path("POSCAR")) -> list[list[float]]:
    """The three lattice vectors from a POSCAR, scaled, in Angstrom."""
    lines = poscar.read_text().splitlines()
    scale = float(lines[1])
    return [[float(x) * scale for x in lines[i].split()[:3]] for i in (2, 3, 4)]


def reciprocal_lengths(poscar: Path = Path("POSCAR")) -> list[float]:
    """
    |b1|, |b2|, |b3| for the cell in `poscar`, in inverse Angstrom.

    A long real-space axis gives a short reciprocal axis, which needs fewer
    k-points. This is what makes a uniform n x n x n mesh the wrong shape for
    anything but a cubic cell.
    """
    a1, a2, a3 = lattice_vectors(poscar)

    def cross(u, v):
        return [u[1] * v[2] - u[2] * v[1],
                u[2] * v[0] - u[0] * v[2],
                u[0] * v[1] - u[1] * v[0]]

    def dot(u, v):
        return sum(x * y for x, y in zip(u, v))

    def norm(u):
        return dot(u, u) ** 0.5

    vol = abs(dot(a1, cross(a2, a3)))
    two_pi = 2.0 * math.pi
    return [two_pi * norm(cross(a2, a3)) / vol,
            two_pi * norm(cross(a3, a1)) / vol,
            two_pi * norm(cross(a1, a2)) / vol]


def kmesh_for(n: int, poscar: Path = Path("POSCAR")) -> tuple[int, int, int]:
    """
    Mesh divisions shaped to the cell, with `n` along the longest reciprocal
    vector and the others scaled down in proportion to their own lengths.

    For cubic cells this returns (n, n, n). For wurtzite GaN with c/a = 1.63
    and n = 7 it returns (7, 7, 4) -- comparable sampling in every direction
    rather than oversampling along c.
    """
    b = reciprocal_lengths(poscar)
    bmax = max(b)
    return tuple(max(1, round(n * bi / bmax)) for bi in b)

