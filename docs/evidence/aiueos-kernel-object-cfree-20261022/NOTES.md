# aiueos kernel object route, C-free — receipt notes

* `cfree-kernel-object.json` — **current**: measured on the merged tree
  (branch `hermes/jun31-selfhost-kernel-qemu-20261022`, merge commit bringing
  in origin/main `452a1b51` = #1465's C-free root re-pin). Producer:
  `selfhost-bootstrap.py` (arm64 Linux, Amu-produced root, no C compiler or
  loader); gate: `check-x86_64-aiueos-object-cfree.py` (Linux x86_64,
  qemu-user). Result: PASS, 8 objects + 30 refusals, route parity byte-identical.
  aarch64 fixed point S1=S2=S3 = `8256bfd8462c2014`.
* `cfree-kernel-object-pre1465-root.json` — superseded: the same gate measured
  on the pre-#1465 root (`7c63bc33d3d3`). Kept byte-identical as historical
  evidence (RETIRED.md convention). Its receipt no longer matches the tree
  (source pins `seed/75-x86_64-static.kotoba`, `76`, `77`, `80` drifted with
  #1465).

Finding: the root re-pin changed the bootstrap root, the S1=S2=S3 fixed point,
`S-x86_64.elf` and `R-x86_64.elf`, but the eight emitted kernel objects are
byte-identical across both measurements (`probe 0e04108e3896`,
`flat-args c59da78cf2f2`, `helper-loop cc46478dc344`, `big-fuel 7ef9fe2b2aa3`)
— the x86_64-aiueos-kernel-v1 object route is invariant under the runtime
re-pin, and both C-free producers stay byte-identical to each other.

Boundary (unchanged): kernel OBJECT ABI only; not the kernel image route; no
emitted object has run in a kernel. Native x86_64 seccomp enforcement stays
unmeasured until a native x86_64 host (JUN-34 OCI VM) runs this gate.
