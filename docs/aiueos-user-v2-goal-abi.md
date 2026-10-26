# AIUEOS user-v2 Goal input ABI

`x86_64-aiueos-user-v2` is a separately selected, freestanding user ELF
target. It extends the zero-capability scalar v1 image with one bounded input
region. It is a compiler-side contract until AIUEOS admits the v2 image,
populates the region, and executes it at CPL3.

## Image and call contract

| Item | v2 contract |
| --- | --- |
| ELF | x86-64 `ET_EXEC`, entry `0x1e1000`, one RX and one RW `PT_LOAD` |
| RX page | file offset `4096`, virtual address `0x1e1000`, at most 4096 bytes |
| RW page | file offset `8192`, virtual address `0x1e2000`, 88 file bytes and 320 memory bytes |
| Private context | first 88 bytes at `0x1e2000`; result is an i64 at offset 0 |
| Goal request | 64 bytes at `0x1e2100` (RW page offset 256), absent from the ELF file and initially zero |
| Entry | exactly `main(request :i64, request-bytes :i64) :i64`; RDI is `0x1e2100`, RSI is 64 |
| Host call | sealed syscall-5 trampoline at `0x1e1030`; capability bitmap stays zero |

The intended OS-to-user input format is a little-endian u32 byte length at
offset 0, followed by at most 60 Goal bytes at offset 4. The OS must reject a
length above 60, write the selected Goal bytes, and zero the remaining bytes
before starting the user program. The compiler only reserves and passes the
region; it cannot establish that the current OS has written a Goal. Text
encoding, admission identity and approval for later external operations must
be defined and verified on the OS/Itonami side.

The compiler appends only the private `kernel-load-u32` intrinsic. Its emitted
machine code checks the base, 512-byte maximum extent and four-byte access
window before reading. The compiler requires the read base and length to be
the original adjacent exported parameters or a proven rooted alias. It
refuses a calculated base, substituted length, wrong entry name/arity/type,
or undeclared effect without creating an ELF. It does not add Linux syscalls,
heap, model access, storage access or ambient authority.

Example Kotoba source:

```clojure
(ns aiueos-user-goal-v2 (:export [main]))
(defn main [request :i64 request-bytes :i64] :i64
  (kernel-load-u32 request request-bytes 0))
```

The example returns the Goal byte length only after AIUEOS writes the input.
It is not an Itonami agent turn. The v1 scalar image remains byte-identical
to its previous SHA-256
`7f5a8c0a31b5bdf191410f007973413d16e497a20ae7fe86c734b9fea85808b1`.

## Native qualification and next guest gate

On Apple Silicon, run
[`check-aiueos-user-v2-macos-native.py`](../scripts/seed/check-aiueos-user-v2-macos-native.py)
through `native_build_queue.py` with a pinned signed Amu compiler and native
packager. It rebuilds the full 47-module compiler to an F1=F2 fixed point,
reruns the v1 gate, compiles the v2 positive sources, checks the ELF bytes,
and requires seven named source refusals plus two malformed-image controls.
The [source-bound receipt](evidence/aiueos-user-v2-macos-native-20261026/README.md)
records the exact local run. Python stages and observes; Kotoba/Amu native
artifacts compile and package. The Mac gate launches no Linux, JVM, Node or C
compiler process.

AIUEOS must separately add a v2 validator/loader rule, copy the 64-byte Goal
request into the mapped user RW page, bind it to the selected author/session,
and prove positive and refusal cases in a fresh QEMU CPL3 boot. The current
v1 verifier and scalar QEMU result do not prove those steps. A real Itonami
turn additionally needs trusted per-operation approval, a model/tool effect,
receipt, durable workspace and reboot continuation on the same image.
