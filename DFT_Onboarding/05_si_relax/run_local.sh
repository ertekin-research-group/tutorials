#!/bin/bash
# run_local.sh -- run VASP on your laptop.
#
# The laptop equivalent of a cluster submit script. There is no queue and
# no scheduler: the calculation runs in your terminal, right now.
#
# Usage:  ./run_local.sh          (uses VASP_NP cores, default 8)
#         VASP_NP=4 ./run_local.sh

set -euo pipefail

: "${VASP_STD:?VASP_STD is not set -- see module 02. Add to ~/.zshrc: export VASP_STD=\$HOME/software/vasp.6.x.x/bin/vasp_std}"
NP="${VASP_NP:-8}"

# Fail early rather than halfway through a calculation.
for f in POSCAR POTCAR INCAR KPOINTS; do
    [[ -f "$f" ]] || { echo "ERROR: missing $f"; exit 1; }
done

if ! command -v mpirun &>/dev/null; then
    echo "ERROR: mpirun not found. Did you 'conda activate defects'?"
    exit 1
fi

# POTCAR/POSCAR consistency: a silent-wrong-answer check worth doing every time.
n_species_poscar=$(sed -n '6p' POSCAR | wc -w | tr -d ' ')
n_species_potcar=$(grep -c "End of Dataset" POTCAR || true)
if [[ "$n_species_poscar" != "$n_species_potcar" ]]; then
    echo "ERROR: POSCAR line 6 lists $n_species_poscar species but POTCAR"
    echo "       contains $n_species_potcar. These must match, in order."
    exit 1
fi

echo "Running VASP on $NP cores: $VASP_STD"
echo "Start: $(date)"
echo "Watch progress in another terminal with:  tail -f OSZICAR"
echo

time mpirun -np "$NP" "$VASP_STD" | tee run.log

echo
echo "End: $(date)"
echo

# Report convergence rather than leaving you to assume it.
if grep -q "reached required accuracy" OUTCAR; then
    echo "OK: ionic relaxation reached the force criterion."
else
    echo "WARNING: ionic relaxation did NOT reach the force criterion."
    echo "         Increase NSW, or restart from CONTCAR:  cp CONTCAR POSCAR"
fi

echo -n "Final energy: "
grep "free  energy   TOTEN" OUTCAR | tail -1
