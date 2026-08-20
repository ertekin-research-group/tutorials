"""
prep_bands.py
1) Read the relaxed CONTCAR from ../05_si_relax/ (8-atom conventional cell)
2) Convert to the primitive 2-atom FCC cell
3) Write the primitive POSCAR into scf/ and nscf/
4) Generate a line-mode KPOINTS file for nscf/ along the
   Setyawan-Curtarolo FCC high-symmetry path
"""
from pathlib import Path
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.symmetry.bandstructure import HighSymmKpath
from pymatgen.io.vasp import Poscar, Kpoints

# All paths are relative to THIS script's location
HERE     = Path(__file__).resolve().parent
CONTCAR  = HERE.parent / "05_si_relax" / "CONTCAR"
SCF_DIR  = HERE / "scf"
NSCF_DIR = HERE / "nscf"

if not CONTCAR.exists():
    raise FileNotFoundError(
        f"Cannot find {CONTCAR}. Run module 05 first (./run_local.sh in 05_si_relax/)."
    )

# 1) read & 2) primitivize
conv = Structure.from_file(CONTCAR)
sga  = SpacegroupAnalyzer(conv, symprec=1e-3)
prim = sga.get_primitive_standard_structure()
print(f"Conv: {conv.num_sites} atoms, a={conv.lattice.a:.4f} A")
print(f"Prim: {prim.num_sites} atoms, a={prim.lattice.a:.4f} A "
      f"(rhombohedral primitive of FCC)")
print(f"Space group: {sga.get_space_group_symbol()} (#{sga.get_space_group_number()})")

# 3) write primitive POSCAR
Poscar(prim).write_file(SCF_DIR  / "POSCAR")
Poscar(prim).write_file(NSCF_DIR / "POSCAR")
print(f"\nWrote primitive POSCAR -> scf/, nscf/")

# 4) line-mode KPOINTS  (Setyawan-Curtarolo FCC: G-X-W-K-G-L-U-W-L-K|U-X)
N_PER_SEG = 30
kpath = HighSymmKpath(prim, path_type="setyawan_curtarolo")
kp    = Kpoints.automatic_linemode(N_PER_SEG, kpath)
kp.write_file(NSCF_DIR / "KPOINTS")
print(f"Wrote line-mode KPOINTS -> nscf/ ({N_PER_SEG} points per segment)")
print(f"k-path: {kpath.kpath['path']}")
