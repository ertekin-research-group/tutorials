<!--
  Build record contributed by a student, August 2026.
  Kept verbatim. This is a record of one real build on one real machine,
  not a recipe -- your machine and package versions will differ.
-->

> **A real build record.** Written by **a student** in August 2026
> while working through this module, on an Apple M5 Pro. Kept as-is.
>
> Treat it as evidence that this is possible and as a guide to the *kinds*
> of thing that go wrong — not as a script to follow. Package versions move
> and your errors will not be identical.

# VASP 6.4.3 build notes — Apple Silicon (macOS), conda-only toolchain

Written by Claude Code, documenting the build session it drove interactively,
per `DFT_Onboarding/02_vasp_build_mac/index.html`.

## Machine

| | |
|---|---|
| `uname -m` | `arm64` |
| macOS | 26.6.2 (build 25G83) |
| CPU | Apple M5 Pro, 18 cores |
| RAM | 48 GB |
| Kernel | Darwin 25.6.0, `RELEASE_ARM64_T6050` |

## Toolchain (all from the `defects` conda env, conda-forge channel)

```
$ conda list -n defects | grep -E "^gfortran |^gcc |^openmpi |^openblas |^libopenblas |^scalapack |^fftw "
fftw          3.3.11   nompi_haf1500d_100   conda-forge
gcc           16.1.0   h500d687_3           conda-forge
gfortran      16.1.0   h500d687_3           conda-forge
libopenblas   0.3.34   openmp_he657e61_0    conda-forge
openblas      0.3.34   openmp_hea878ba_0    conda-forge
openmpi       5.0.10   h07cac57_1           conda-forge
scalapack     2.2.0    ha4fe3f2_6           conda-forge
```

Nothing was installed with Homebrew or outside conda. `gfortran`, `mpif90`, `mpicc`
and `mpirun` all resolved to `~/miniforge3/envs/defects/bin/` — verified with
`which` before starting, per the module's step 1. No `ifort`/MKL anywhere;
this is the "less-trodden," GNU-on-arm64 path the module warns about.

One extra thing not in the module's table: a C++ compiler was also needed
(VASP's small `parser` subdirectory, for `LOCPROJ`, is C++). `defects` has no
standalone `g++`/`gxx` package, but conda-forge's `clang++-22` was already
present as a dependency of something else, so that's what got used —
see the parser fix below for why that mattered.

## Source and starting template

- VASP source: `vasp.6.4.3.tgz`, extracted to `~/vasp/vasp.6.4.3/` (a licensed
  tarball, not a package — matches the module's framing exactly).
- Final executables live in `~/vasp/vasp.6.4.3/bin/`: `vasp_std`, `vasp_gam`, `vasp_ncl`.
- Starting template: **`arch/makefile.include.gnu_omp`** — the GNU + OpenMPI +
  OpenMP template. Picked over plain `gnu` (no OpenMP — leaves cores on the
  table) and over the `*_mkl_*`/`*_aocl_*` variants (wrong BLAS entirely; this
  machine has OpenBLAS, not MKL or AOCL).
- Final working file: [`makefile.include`](makefile.include) in this directory
  (copied from `~/vasp/vasp.6.4.3/makefile.include`, which is the copy that
  actually built the binaries).

## What changed in the template, and why

The template's job is mostly to point at `$CONDA_PREFIX` instead of made-up
paths, per the module's step 3. Concretely:

| Variable | Template said | Changed to |
|---|---|---|
| `OPENBLAS_ROOT` | `/path/to/your/openblas/installation` | `$(CONDA_PREFIX)` |
| `SCALAPACK_ROOT` | `/path/to/your/scalapack/installation` | `$(CONDA_PREFIX)` |
| `FFTW_ROOT` | `/path/to/your/fftw/installation` | `$(CONDA_PREFIX)` |
| `VASP_TARGET_CPU` | (x86 default, implicit `-march=native`) | `-mcpu=native` — the AArch64-correct spelling of "tune for this exact CPU" |
| `CXX_PARS` / `LLIBS` | `g++` / `-lstdc++` | `$(CONDA_PREFIX)/bin/clang++-22` / `-lc++` |
| `CFLAGS_LIB` | `-O` | `-O -std=gnu17` |

The `CXX_PARS`/`LLIBS` and `CFLAGS_LIB` rows aren't cosmetic path-substitution —
they're real platform fixes, explained below where they came up.

`CPP_OPTIONS` kept the template's flags as-is (`-DMPI -DscaLAPACK -Dvasp6
-Dtbdyn -Dfock_dblbuf` etc.) plus `-D_OPENMP` from the `_omp` variant; only
`-DHOST` was changed to a cosmetic `"MacOSXAppleSilicon"` string.

## Errors hit, and what actually fixed them

Four distinct problems showed up, in this order. Each one is a different
*category* from the module's table — a useful reminder that "compiles clean"
and "links clean" and "runs correctly" are three separate hurdles, not one.

### 1. `getrusage`/`gettimeofday`: C23 broke 30-year-old K&R prototypes

**Category:** none of the module's six — this is a *compile*-time C error,
new because the compiler is new, not because of macOS per se.

`src/lib/timing_.c` declares old K&R-style empty-parens prototypes:

```c
int  getrusage();
int  gettimeofday();
```

In pre-C23 C, `int foo();` means "takes unspecified arguments" — harmless,
even redundant, next to the real prototype from `<sys/resource.h>`. **C23
changed the meaning of empty parens to "takes zero arguments."** GCC 16
defaults to C23, so these stale forward-declarations now directly contradict
the real 2-argument prototypes, and the compiler errors:

```
timing_.c:26:31: error: too many arguments to function 'getrusage'; expected 0, have 2
```

Same failure, different file, on the next build attempt: `src/lib/dclock_.c`
has the identical pattern for `gettimeofday`.

**Fix, two parts:**
- `timing_.c` specifically: deleted the two stale prototypes and added
  `#include <sys/time.h>` so `gettimeofday`'s real prototype is in scope.
- Every other file in `src/lib/*.c` with the same pattern (`dclock.c`,
  `dclock_ds20.c`, `dclock_simple.c`, `timing.c`, `timing_ds20.c`): rather than
  hand-edit each one, added `-std=gnu17` to `CFLAGS_LIB` — pins the C library
  files to the pre-C23 standard where the K&R idiom is valid, without touching
  files that aren't even used by this build variant.

### 2. `ar`/`ld`: a non-object file inside a static archive

**Category:** the module's "`Symbol not found` / undefined reference at
link time" bucket, but the actual cause was stranger than a missing symbol.

`src/parser/makefile` builds `libparser.a` like this:

```make
libparser.a: $(CPPOBJ_PARS) $(COBJ_PARS) locproj.tab.h
	ar vq libparser.a $(CPPOBJ_PARS) $(COBJ_PARS) locproj.tab.h
```

Note `locproj.tab.h` — a **header file**, not a compiled object — gets `ar`'d
into the archive alongside the real `.o` files. GNU's `ar`/`ld` silently
tolerate a non-object archive member. Apple's `ld` does not:

```
ld: in parser/libparser.a(locproj.tab.h), archive member 'locproj.tab.h'
    with length 2696 is not mach-o or llvm bitcode file 'parser/libparser.a'
    for architecture arm64
collect2: error: ld returned 1 exit status
```

**Fix:** dropped `locproj.tab.h` from the `ar vq` command in
`src/parser/makefile`. It stays a build prerequisite (so the archive still
rebuilds if the header changes) but is no longer archived into the `.a` file.

**A wrinkle worth recording:** the first time this was "fixed," the rebuild
still failed with the exact same error. GNU Make's rule
`libparser.a: $(CPPOBJ_PARS) $(COBJ_PARS) locproj.tab.h` doesn't list the
Makefile itself as a prerequisite, so an already-built (bad) `libparser.a`
looked up-to-date and was never regenerated. Deleting the stale
`build/*/parser/libparser.a` by hand before rerunning `make` was what
actually forced the rebuild. Lesson: a Makefile edit doesn't retroactively
invalidate build artifacts that were already up-to-date under the old rule.

### 3. `_Unwind_Backtrace` infinite loop — a hang that looked like a deadlock

**Category:** none of the module's — genuinely new territory, and the
trickiest one to diagnose, because at first it looked exactly like the "no
obvious symptom" failure the module doesn't even list.

The very first parallel test job (`mpirun -np 6 vasp_std`) just... sat there.
All 6 processes pinned at ~100% CPU, `OUTCAR` frozen right after the
parameter-listing header, no progress after 3+ minutes on an 8-atom cell that
should take seconds. Re-running with `-np 1` hung at the *identical* point —
which ruled out an MPI collective deadlock (a single rank has no other ranks
to deadlock with) and pointed at something wrong in a single thread of
execution.

Attached macOS's built-in `sample` profiler to the stuck process instead of
guessing:

```
sample $(pgrep -x vasp_std) 3 -file /tmp/vasp_sample.txt
```

The call stack was not doing physics. It was recursing inside libgfortran's
own error-reporting machinery:

```
_gfortrani_show_backtrace -> backtrace_full -> _Unwind_Backtrace
  -> libunwind::UnwindCursor::step -> _sigtramp
  -> _gfortrani_backtrace_handler -> _gfortrani_show_backtrace -> ...
```

Translation: a real Fortran runtime error had occurred, gfortran's default
behavior (print the error, then print a backtrace) kicked in, and the
backtrace-printing routine itself — specifically stack-unwinding via
`libunwind` on Darwin/arm64 — loops forever instead of completing. This is a
gfortran/macOS-ARM64 interaction bug, not a VASP bug, but it completely
hides whatever the real error was.

**Fix to see the real error:** `export GFORTRAN_ERROR_BACKTRACE=0`, which
tells the runtime to skip the (broken) backtrace and just print the message
and exit. That's what surfaced the real problem — see #4.

**Fix to stop it recurring silently:** rather than remember to type that
export every time, it's now wired into
`~/miniforge3/envs/defects/etc/conda/activate.d/vasp.sh` (set on activate)
and the matching `deactivate.d/vasp.sh` (restored/unset on deactivate), right
next to the `PATH` addition for the VASP binaries. `conda activate defects`
is now sufficient on its own.

### 4. `Missing comma between descriptors` — the real bug underneath #3

**Category:** the module's "Preprocessor / `#define` errors" bucket doesn't
quite fit either — this is a runtime Fortran I/O error, not a preprocessor
one, but it's the same spirit: old code, new compiler, stricter rules.

With the backtrace disabled, the actual error printed cleanly:

```
At line 883 of file fock.F (unit = 8, file = 'OUTCAR')
Fortran runtime error: Missing comma between descriptors
(' Exchange correlation treatment:'  / '   ' A7  ' = ',A,  '    functional compo
```

`src/fock.F` has a `FORMAT` statement with a string literal directly abutting
an edit descriptor with no comma between them:

```fortran
10  FORMAT(' Exchange correlation treatment:'  / &
           '   ' A7  ' = ',A,  '    functional components'/ &
```

`'   '` and `A7` need a comma between them; older/other compilers were lenient
about this, gfortran 16 enforces the standard and rejects it *at runtime*
(this is I/O formatting, so it's not caught at compile time). This line runs
for essentially every VASP job — it's printed unconditionally in the routine
that reports the XC functional — so it broke `vasp_std`, `vasp_gam`, and
`vasp_ncl` identically.

**Fix:** added the missing comma. There turned out to be a second, identical
copy of the same malformed line at label `100` a bit further down in the same
file (evidently the same block, duplicated for a different code path) — found
by grepping the fixed pattern and confirmed by the exact same crash recurring
after the first fix and a rebuild. Fixed both; a subsequent search for the
same `'<string>' <descriptor>` shape elsewhere in `src/*.F` turned up no
further instances (checked, and ruled out several look-alikes in `lattlib.F`,
`lie.F`, `chain.F`, `subdftd3.F` that matched the regex but were legitimate
literal text, not format bugs).

Each of these four fixes triggered a real rebuild, not just a relink — Fortran
module dependencies mean changing one file used by many others (`fock.F`
especially) cascades into recompiling a large fraction of the tree. Full
sequence was roughly: build fails → fix → `make DEPS=1 -j18 <version>` →
(sometimes) fails differently → fix → rebuild, iterated until all three
variants (`std`, `gam`, `ncl`) linked and ran clean.

## Validation

### Test 1 — binary exists, correct architecture

```
$ file ~/vasp/vasp.6.4.3/bin/vasp_std
vasp_std: Mach-O 64-bit executable arm64
```
Same for `vasp_gam` and `vasp_ncl`. Not x86_64, not a Rosetta-translated
binary — a native arm64 build.

### Test 2 — runs in parallel as one job, not N copies

From `DFT_Onboarding/05_si_relax/`:

```
$ conda activate defects
$ mpirun -np 4 vasp_std
$ grep -i "running" OUTCAR
 running    4 mpi-ranks, with   18 threads/rank, on    1 nodes
```

One job, 4 MPI ranks confirmed in the `OUTCAR` header — not four independent
single-core runs. (Also spot-checked `vasp_std` with 9 ranks × 2 OpenMP
threads = all 18 physical cores on a smaller ad-hoc Si cell, and separately
`vasp_gam`/`vasp_ncl` with 4×2 = 8 cores — all reported the correct rank/thread
count and produced consistent energies, so this wasn't a std-only fluke.)

### Test 3 — the answer is physically right

Ran the actual module 05 Si-relaxation input set (`PREC = Accurate`,
`ENCUT = 450`, 9×9×9 Gamma-centered mesh, `ISIF = 3` cell+ion relaxation,
`EDIFFG = -0.01`):

```
$ grep "free  energy   TOTEN" OUTCAR | tail -1
  free  energy   TOTEN  =       -43.39970201 eV
```

8 atoms → **-5.425 eV/atom**, matching the module's expected "roughly -5.4
eV/atom" target. Relaxation reached the force criterion in 3 ionic steps
("`reached required accuracy - stopping structural energy minimisation`"),
and the lattice constant relaxed from the input 5.4437 Å to 5.4685 Å — a
sane, small adjustment for a reasonable starting guess, not a blown-up or
collapsed cell.

This is the test that actually matters per the module's framing: a clean
compile is not evidence of a correct build, since a silently mismatched BLAS
(wrong integer width, wrong threading model) would still link and run,
just produce garbage or `NaN`. Getting close to the reference number, from a
build that links against this exact OpenBLAS/ScaLAPACK/FFTW combination,
confirms the linear algebra and FFT libraries are wired up correctly, not
just present.

### Cross-check: three binaries agree with each other

Beyond the module's three tests, I also ran a smaller ad-hoc 8-atom Si cell
(Gamma point only, `ENCUT = 250`, single-point SCF) through **all three**
binaries — `vasp_std`, `vasp_gam`, and `vasp_ncl` (the last with
`LNONCOLLINEAR = .TRUE.` and a nonzero `MAGMOM`, to actually exercise the
noncollinear-specific code path rather than just running it like `std`) —
serially and under several MPI×OpenMP combinations. All three converged to
the same energy to 5-6 significant figures (~-33.058 eV) regardless of rank
count, which is a second, independent piece of evidence that the parallel
decomposition (band/plane-wave splitting across MPI ranks, OpenMP threading
within a rank) is numerically consistent and not silently corrupting results
under parallelism.

## Making it easy to call

Rather than a `~/.zshrc` alias pointing at a hardcoded path (the module's
suggestion), `vasp_std`/`vasp_gam`/`vasp_ncl` are put on `PATH` automatically
via the `defects` conda environment's own activation hooks:

- `~/miniforge3/envs/defects/etc/conda/activate.d/vasp.sh` — prepends
  `~/vasp/vasp.6.4.3/bin` to `PATH` and sets `GFORTRAN_ERROR_BACKTRACE=0`.
- `~/miniforge3/envs/defects/etc/conda/deactivate.d/vasp.sh` — undoes both on
  `conda deactivate`.

So `conda activate defects` alone is enough; no separate export or alias
needed. (Simple `mpirun -np N vasp_std`-style aliases like the module
suggests would still be easy to add on top of this if wanted — just not
necessary for the PATH/env-var part.)

## Pseudopotentials and auxiliary data

`potpaw_PBE.64` (346 potentials) and the van der Waals kernel
(`vdw_kernel.bindat`, gunzipped from the vendored `.gz`) were copied into
`~/vasp/` alongside the build, matching the module's "POTCAR library in
place" checklist item.
