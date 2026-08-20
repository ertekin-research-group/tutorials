"""
plot_bands.py
Read nscf/vasprun.xml + nscf/KPOINTS, save band-structure figure next to
this script, and compare the computed band gap to experiment.

The comparison is the point of the exercise. Your PBE gap will be roughly
half the experimental value, and that discrepancy -- not the figure -- is
what module 06 is actually teaching.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from pymatgen.io.vasp import BSVasprun
from pymatgen.electronic_structure.plotter import BSPlotter

HERE   = Path(__file__).resolve().parent
NSCF   = HERE / "nscf"
OUTPNG = HERE / "Si_bands.png"

# BSVasprun is the lightweight parser meant for band-structure runs
bsv = BSVasprun(str(NSCF / "vasprun.xml"),
                parse_projected_eigen=False)
bs  = bsv.get_band_structure(kpoints_filename=str(NSCF / "KPOINTS"),
                             line_mode=True)

gap = bs.get_band_gap()
vbm = bs.get_vbm()
cbm = bs.get_cbm()
print(f"Band gap: {gap['energy']:.3f} eV  ({'direct' if gap['direct'] else 'indirect'})")
print(f"  transition: {gap['transition']}")
print(f"VBM = {vbm['energy']:.3f} eV at kpoint index {vbm['kpoint_index']}")
print(f"CBM = {cbm['energy']:.3f} eV at kpoint index {cbm['kpoint_index']}")
print(f"E_fermi (vasprun): {bsv.efermi:.3f} eV")

plotter = BSPlotter(bs)
plotter.get_plot(zero_to_efermi=True, ylim=(-6, 8))
plt.title(f"Si band structure (PBE) — gap = {gap['energy']:.3f} eV "
          f"({'direct' if gap['direct'] else 'indirect'})")
plt.tight_layout()
plt.savefig(OUTPNG, dpi=200, bbox_inches="tight")
print(f"\nFigure saved: {OUTPNG}")

# ----------------------------------------------------------------------
# The actual lesson: compare to experiment.
# ----------------------------------------------------------------------
GAP_EXPERIMENT = 1.17      # Si indirect gap at low temperature, eV

computed = gap["energy"]
ratio = computed / GAP_EXPERIMENT

print("\n" + "=" * 62)
print("  Band gap: computed vs experiment")
print("=" * 62)
print(f"  This work (PBE):   {computed:6.3f} eV  "
      f"({'direct' if gap['direct'] else 'indirect'})")
print(f"  Experiment:        {GAP_EXPERIMENT:6.3f} eV  (indirect)")
print(f"  Ratio:             {ratio:6.2f}")
print(f"  Underestimate:     {(1 - ratio) * 100:5.1f}%")
print("=" * 62)

print("""
This is the DFT band gap problem, and it is not your mistake.

Semi-local functionals such as PBE systematically and severely
underestimate band gaps -- typically by 30-50%, and sometimes predicting
a metal where experiment finds a semiconductor. The cause is a genuine
deficiency of the approximation (missing derivative discontinuity in the
exchange-correlation energy, plus self-interaction error), not a
convergence problem. Raising ENCUT or the k-point density will not help
at all; you already converged those in module 04.

Note also that the topology is right even though the magnitude is not:
the gap is correctly indirect, and the valence band structure is quite
good. PBE gets the shape roughly right and the gap badly wrong.

Why this matters enormously for defects
---------------------------------------
A defect level is reported relative to the band edges -- "0.9 eV below the
conduction band minimum", say. If your gap is only half as wide as it
should be, there is only half as much room to place that level, and every
charge transition level you compute inherits the error. This is the single
biggest reason the modern defect literature uses hybrid functionals such
as HSE06, and it is why we will benchmark one in Week 15.

For this semester you will work in PBE deliberately: it is cheap enough
to let you learn the whole workflow, and every methodological step is
identical. When your Week 11 transition levels disagree with published
HSE numbers, this is why. That disagreement is expected -- write it down
rather than treating it as a bug.
""")
