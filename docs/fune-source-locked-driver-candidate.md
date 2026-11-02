# Source-locked producer in the fixed driver (JUN-782)

The fixed driver now pins an ARM64 Linux producer built from the 14 canonical
Kotoba fune project sources via source-locked AArch64 KSEED and the packed
Linux runner. The reproducible build entry and its boundaries are described in
`kotoba-lang/kotoba` under `lib/kotoba.fune/RUNNABLE-PRODUCER.md`. This is a
fixed test identity, not artifact authentication or a general OCI runtime.

Native ARM64 Linux observations on 2026-11-03:

* The newly built source-pinned compiler produced the same producer ELF
  SHA-256 `175f19a6186b4773de88e0be950c062e3e884f800201857f8ab7b3033fb2cd72`
  as the previous bootstrap build. The source-pinned driver factory produced
  driver `928876cc16982f7291ca4c9809c4f011f3281760c85d0b6fd23cca3e91e3311a`.
* The existing fixed OCI driver observer passed its output, refusal, cgroup
  ownership, cleanup, failure and mutation controls using that producer. An
  additional check refused the previously pinned producer without stdout.
* Mac ARM64 selfhost rebuild and 72 public CLI observations passed. The 24
  x86 cross-compiled fixture hashes matched the prior recorded hashes; this is
  not a new native x86 qualification or a hosted CI result.

The older producer provenance statement in
`docs/fune-native-fixed-driver-candidate.md` describes the earlier generated
source artifact and has not yet been revised. Both versions retain the same
fixed-fixture restrictions, delegated-cgroup requirement, unqualified
same-principal races, and absence of a crash-recovery collector. The new
producer can emit partial commands before an error; the supervisor and worker
must be discarded when it fails. Registry, arbitrary images and workloads,
full isolation and general lifecycle commands remain outside this result.
