#!/bin/bash
# run_local.sh -- run this stage of the band-structure workflow locally.
set -euo pipefail
: "${VASP_STD:?VASP_STD is not set -- see module 02}"
NP="${VASP_NP:-8}"
for f in POSCAR POTCAR INCAR KPOINTS; do
    [[ -f "$f" ]] || { echo "ERROR: missing $f"; exit 1; }
done
command -v mpirun &>/dev/null || { echo "ERROR: mpirun not found. conda activate defects"; exit 1; }
echo "Running VASP on $NP cores in $(basename "$PWD")"
time mpirun -np "$NP" "$VASP_STD" | tee run.log
if grep -q "aborting loop because EDIFF is reached" OUTCAR; then
    echo "OK: electronic loop converged."
else
    echo "WARNING: electronic loop did NOT converge. Do not use this result."
fi
grep "free  energy   TOTEN" OUTCAR | tail -1
