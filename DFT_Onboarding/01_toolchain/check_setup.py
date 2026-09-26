#!/usr/bin/env python
"""
check_setup.py -- verify that the Week 1 toolchain is actually working.

Run this at the end of module 01:

    python check_setup.py

It checks each piece independently and keeps going after a failure, so you
get the full picture in one pass rather than fixing one thing at a time.
Anything marked FAIL needs sorting out before module 02.
"""
import os
import sys
import shutil

results = []


def check(label, fn, required=True):
    """Run one check; record PASS/FAIL plus a short detail string."""
    try:
        detail = fn()
        results.append(("PASS", label, detail or ""))
    except Exception as exc:                      # noqa: BLE001
        results.append(("FAIL" if required else "WARN", label, str(exc)))


# ---------------------------------------------------------------- Python
def _python():
    if sys.version_info < (3, 10):
        raise RuntimeError(f"Python {sys.version.split()[0]} is too old")
    in_conda = os.environ.get("CONDA_DEFAULT_ENV")
    if not in_conda:
        raise RuntimeError("not running inside a conda environment "
                           "(did you `conda activate defects`?)")
    return f"Python {sys.version.split()[0]} in env '{in_conda}'"


# ------------------------------------------------------- core packages
def _imports():
    import numpy, scipy, matplotlib, pandas   # noqa: F401
    return (f"numpy {numpy.__version__}, scipy {scipy.__version__}, "
            f"matplotlib {matplotlib.__version__}")


def _ase():
    import ase
    from ase.build import bulk
    si = bulk("Si", "diamond", a=5.43)
    return f"ase {ase.__version__}; built Si cell with {len(si)} atoms"


def _pymatgen():
    import pymatgen.core as pmg
    s = pmg.Structure.from_spacegroup(
        "Fd-3m", pmg.Lattice.cubic(5.43), ["Si"], [[0, 0, 0]])
    return f"pymatgen {pmg.__version__}; built Si with {len(s)} sites"


def _spglib():
    import pymatgen.core as pmg
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    s = pmg.Structure.from_spacegroup(
        "Fd-3m", pmg.Lattice.cubic(5.43), ["Si"], [[0, 0, 0]])
    sga = SpacegroupAnalyzer(s)
    sg = sga.get_space_group_symbol()
    if sg != "Fd-3m":
        raise RuntimeError(f"symmetry detection gave {sg}, expected Fd-3m")
    return f"space group correctly identified as {sg}"


# ------------------------------------------------------------- POTCARs
def _potcar_path():
    psp = os.environ.get("PMG_VASP_PSP_DIR")
    if not psp:
        from pymatgen.core import SETTINGS
        psp = SETTINGS.get("PMG_VASP_PSP_DIR")
    if not psp:
        raise RuntimeError("PMG_VASP_PSP_DIR is not set anywhere")
    if not os.path.isdir(psp):
        raise RuntimeError(f"PMG_VASP_PSP_DIR points at {psp}, "
                           "which does not exist")
    return psp


# pymatgen names each POTCAR set after the release it came from. The group
# library is currently potpaw_PBE.64 -> "PBE_64", but older sets are still in
# circulation, so try the plausible ones rather than hard-coding one and
# failing on a library that is perfectly fine.
POTCAR_FUNCTIONALS = ["PBE_64", "PBE_54", "PBE_52", "PBE"]


def _potcar_generate():
    from pymatgen.io.vasp.inputs import Potcar
    errors = []
    for functional in POTCAR_FUNCTIONALS:
        try:
            pot = Potcar(["Si"], functional=functional)
        except Exception as exc:                      # noqa: BLE001
            errors.append(f"{functional}: {type(exc).__name__}")
            continue
        enmax = pot[0].keywords.get("ENMAX")
        return (f"generated Si POTCAR with functional={functional}, "
                f"ENMAX = {enmax} eV")
    raise RuntimeError(
        "could not generate a POTCAR with any known functional set. "
        "Check that PMG_VASP_PSP_DIR points at a directory produced by "
        "`pmg config -p`, and note which set you were given "
        f"(tried: {'; '.join(errors)})")


# ------------------------------------------------- Materials Project key
def _mp_key():
    key = os.environ.get("MP_API_KEY")
    if not key:
        from pymatgen.core import SETTINGS
        key = SETTINGS.get("PMG_MAPI_KEY")
    if not key:
        raise RuntimeError("no MP API key found in MP_API_KEY or PMG_MAPI_KEY")
    return f"key found ({len(key)} characters, starts '{key[:4]}...')"


def _mp_query():
    from mp_api.client import MPRester
    key = os.environ.get("MP_API_KEY")
    with MPRester(key) as m:
        doc = m.materials.summary.search(
            material_ids=["mp-149"], fields=["material_id", "formula_pretty"])
    return f"queried mp-149 -> {doc[0].formula_pretty}"


# ------------------------------------------------------------- tooling
def _git():
    if not shutil.which("git"):
        raise RuntimeError("git not found on PATH")
    import subprocess
    name = subprocess.run(["git", "config", "--get", "user.name"],
                          capture_output=True, text=True).stdout.strip()
    email = subprocess.run(["git", "config", "--get", "user.email"],
                           capture_output=True, text=True).stdout.strip()
    if not name or not email:
        raise RuntimeError("git user.name / user.email not configured")
    return f"{name} <{email}>"


def _mpi():
    if not shutil.which("mpirun"):
        raise RuntimeError("mpirun not found -- conda MPI not installed yet "
                           "(this is expected before module 02)")
    return shutil.which("mpirun")


def _gfortran():
    exe = shutil.which("gfortran")
    if not exe:
        raise RuntimeError("gfortran not found (expected before module 02)")
    return exe


# ------------------------------------------------------------------ run
print("\n" + "=" * 68)
print("  Ertekin Group -- Week 1 setup check")
print("=" * 68 + "\n")

check("Python / conda environment", _python)
check("Core packages (numpy, scipy, matplotlib, pandas)", _imports)
check("ASE", _ase)
check("pymatgen", _pymatgen)
check("Symmetry detection (spglib)", _spglib)
check("POTCAR directory configured", _potcar_path)
check("POTCAR generation via pymatgen", _potcar_generate)
check("Materials Project API key present", _mp_key)
check("Materials Project query works", _mp_query)
check("Git configured", _git)
check("MPI available (module 02)", _mpi, required=False)
check("Fortran compiler available (module 02)", _gfortran, required=False)

width = max(len(label) for _, label, _ in results)
for status, label, detail in results:
    mark = {"PASS": "  ok ", "FAIL": " FAIL", "WARN": " warn"}[status]
    print(f"[{mark}] {label.ljust(width)}  {detail}")

n_fail = sum(1 for s, _, _ in results if s == "FAIL")
n_warn = sum(1 for s, _, _ in results if s == "WARN")

print("\n" + "-" * 68)
if n_fail:
    print(f"{n_fail} required check(s) failed. Sort these out before "
          f"module 02 -- bring the output to the meeting if you are stuck.")
else:
    print("All required checks passed."
          + (f" ({n_warn} module-02 item(s) not yet installed, "
             "which is fine.)" if n_warn else ""))
print("-" * 68 + "\n")

sys.exit(1 if n_fail else 0)
