# Mac selfhost to native Linux compiler candidates — 2026-10-26

The [exact-head Actions run #40236493734](https://github.com/kotoba-lang/amu/actions/runs/40236493734)
passed three jobs on commit `4d49bcff93688add3f509928236db0fc26ac455c`:

1. `mac-root` rebuilt the 47-module Amu compiler to its Mac native F1=F2
   source fixed point, then used signed F2 to emit the Linux candidates. No
   Linux, JVM, Node or C compiler process produced these bytes. Python staged
   source and checked identities. The Mac candidate artifact is
   `mac-cross-linux-candidates` in the run.
2. `native-cross-arm64` downloaded that artifact and ran the Mac-produced ARM
   image on a native ARM Linux kernel. It reproduced the exact KSEED2
   container and the ARM packed image for two further generations.
3. `native-cross-x86_64` ran the Mac-produced full compiler on a native x86
   Linux kernel and rebuilt the full image twice, byte for byte.

| Source/artifact | SHA-256 | Bytes |
| --- | --- | ---: |
| FULL47 source unity | `60c49f2fb1a49175a3ad2a7efd5cd7bd21f68c5d91f3455663be9656e34006fd` | 3,462,309 |
| Mac F2's full compiler container | `8f932700219ccd15b9ac980db8f978084a11577831f3114e3842ec9da074a638` | 3,257,875 |
| ARM packed root | `f8b81bb77abd0be866fc597c231e14af8d7ae266bc21a36037c66f81259d7f87` | 3,568,128 |
| x86 full public compiler candidate | `7413a64485ab7e27e9a26434a2e6b0d06cca68aa4e2a17e3634360c2b027f291` | 9,343,488 |
| x86 selfhost compiler candidate | `cd3ee8ee0a86441a3ed10d195674143f226a92c7698454bb78bbc22c37a34a8d` | 2,327,040 |

The adopted ARM root and `bin/amu` on this draft branch are copied from the
same Mac-generated candidates. `check-native-identities.py` passes for the
new source and images. The previous qualified artifacts remain in the JSON
history/previous qualification records. The new artifacts' qualification
fields are marked pending while the existing broad native gates rerun.

This is cross-target production and narrow native fixed-point evidence. The
first checked-in Mac root's historical producer bridge used Linux; this run
does not establish an independently trusted Mac release bootstrap. The full
ARM/x86 corpus, public aliases and source locks, controller roles, shared
components, AIUEOS release media, Itonami agent loop and physical hardware
still have separate gates. The Linux jobs above verify Mac-produced artifacts;
they are not part of the Mac build or local OS execution path.
