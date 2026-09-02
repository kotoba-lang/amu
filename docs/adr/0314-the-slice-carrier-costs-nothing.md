# ADR-0314: The slice carrier costs nothing

- Status: accepted
- Date: 2026-09-02

## Context

ADR 0285 decided that a bulk carrier must be addressable memory, not a bigger
vector. ADR 0292 landed the machine half of it — `slice-{load,store}-u{8,16,32,64}`,
element-indexed, ceilinged at 2^40, one unsigned compare and one scaled load per
element, no context callback — and said out loud that the **value** was not
landed:

> `[:slice T]` is not a type. ADR 0285 asks for a two-word (base, length)
> carrier a `let` binds, a function parameter carries and `slice-sub` narrows.
> What exists is the machine layer it lowers to: three separate i64 operands.

So a traversal took `base` and `length` as two parameters out of five and
re-proved the base's provenance at every call site, which is what the aiueos
objects do.

## Decision

kotoba-sema ADR 0022 gives `[:slice T]` a value in the **source syntax only**,
erased into those two i64 words before HIR. This repository's part is the
evidence that the erasure is free and the pins that carry it.

## The measurement that matters

The carried source and the machine-spelled source compile to **the same bytes**,
on both ISAs, at every element width:

| target | element | carried | machine-spelled | identical |
|---|---|---|---|---|
| `x86_64-aiueos-kernel-v1` | `:u8` | 227 B | 227 B | yes |
| | `:u16` | 243 B | 243 B | yes |
| | `:u32` | 242 B | 242 B | yes |
| | `:u64` | 242 B | 242 B | yes |
| `aarch64-aiueos-kernel-v1` | `:u8` | 196 B | 196 B | yes |
| | `:u16` | 204 B | 204 B | yes |
| | `:u32` | 204 B | 204 B | yes |
| | `:u64` | 204 B | 204 B | yes |

Not vacuous: crossing the widths (a carried `[:slice :u8]` against a
machine-spelled `slice-load-u16`, and `[:slice :u64]` against `slice-load-u32`)
differs on both ISAs. The comparison can tell two programs apart.

Everything the frontend refuses about slices — returning one, putting one in a
record, exporting one, computing a base — is therefore bought with nothing.

## The object, compiled without a JDK

`test/fixtures/slice-carrier-sum.kotoba` through
`bin/amu compile --target x86_64-aiueos-kernel-v1 --jvm-free`, 1504 bytes,
disassembled with `llvm-objdump -d --triple=x86_64`:

```
  5e: 49 ba 00 00 00 00 00 01 00 00   movabsq $0x10000000000, %r10
  83: 4e 8d 1c 2b                     leaq    (%rbx,%r13), %r11
  87: 45 0f b6 03                     movzbl  (%r11), %r8d
 103: 49 ba 00 00 00 00 00 01 00 00   movabsq $0x10000000000, %r10
 138: 4e 8d 1c eb                     leaq    (%rbx,%r13,8), %r11
```

Both traversals are spelled `(slice-get s index)` in the source. **The element
width comes from the slice's type, not from the operation's name**, and it
lands in the SIB scale field: 1 for a `[:slice :u8]`, 8 for a `[:slice :u64]`.

`grep -cE 'call[q]?[[:space:]]+\*'` over the disassembly is **0**. The four
`call` instructions in the object are direct `rel32` — the entry plumbing and
the three traversals. The loops contain none.

The `slice-sub` narrowing is readable, and it is a check rather than an
addition:

```
 198: ba 10 00 00 00       movl  $0x10, %edx        ; offset  16 elements
 19d: 41 b8 20 00 00 00    movl  $0x20, %r8d        ; count   32 elements
 1a3: 48 85 c0             testq %rax, %rax         ; non-null parent
 1a6: 0f 84 ...            je    trap
 1ac: 48 39 ca             cmpq  %rcx, %rdx         ; offset within length
 1af: 0f 87 ...            ja    trap
 1b5: 49 89 ca             movq  %rcx, %r10
 1b8: 49 29 d2             subq  %rdx, %r10         ; the remainder
 1bb: 4d 39 d0             cmpq  %r10, %r8          ; count within it
 1be: 0f 87 ...            ja    trap
 1c4: 48 89 c3             movq  %rax, %rbx
 1c7: 48 01 d3             addq  %rdx, %rbx         ; base + offset
 1cf: 0f 0b                ud2
 1d1: b8 20 00 00 00       movl  $0x20, %eax        ; the NARROWED length
```

The narrowed slice carries its own length — 32 elements, which is what the
traversal bounds against — not the parent's.

## Pins

| dependency | from | to | why |
|---|---|---|---|
| kotoba-sema | `e42b74ef` | `bb0d47c6` | the carrier (kotoba-sema ADR 0022) |
| kotoba-kir | `1e00f830` | *unchanged at main's `08bdab8b`* | see below |
| kotoba-verifier | `4b2d2f1f` | `7a8cdcd9` | the same refusal, re-derived (ADR 0028); and that commit unsticks kotoba-verifier's own 302-commit-stale kotoba-native pin (ADR 0027) |

**kotoba-kir is deliberately not advanced**, and the reason is a collision
between two changes that landed 2026-09-02 and belong to neither this stream
nor each other. kotoba-kir `984a507` ("control effects bridge through as
keywords, so `:abort` reaches the sealed row") and this repository's
`definition_identity_test` (ADR 0300: "`:abort` names no authority, so the
bridge has no catalog keyword for it and refuses") decided the same question
in opposite directions. Advancing this pin past `984a507` turns **8
assertions** in that test red — measured, not predicted. Nothing here needs
the kotoba-kir side of the slice work: the carrier is erased in kotoba-sema,
and `native-boundary-type-refusal` names a shape that cannot arrive if that
erasure ran. So the pin waits for that adjudication rather than forcing it.

`kotoba-native` is **not** advanced here. It needs nothing: `pilot-expression?`
already answers `:scalar` for a four-operand `slice-load-u8`, and no head is
new. The routes kotoba-native's `docs/lang-authority-diff.md` listed as
prerequisites — a second `pilot-expression?` value shape, a two-slot spill in
the x86-64 fallback, a two-register SSA value in GMIR/MIR — turned out not to
be needed at all rather than merely to be dearer.

## Evidence

- `kotoba.compiler.slice-value-test`, 6 tests: byte identity on both ISAs at
  four widths, the fixture compiling for the freestanding kernel target, the
  movabs ceiling and both SIB scales, no context callback (with a direct-call
  control so the negative is not vacuous), the narrowing's three comparisons
  and its own length, and four frontend refusals still refusing after
  `compile-source` has had its chance at them.
- Full suite at the advanced pins: **1261 tests / 9162 assertions / 0 failures**,
  `test-runner: COMPLETE -- 163 of 163 namespaces`.
- The `--jvm-free` route produced the object quoted above (exit 0, 1504 bytes,
  provenance and publication records beside it).

## Not done

- No aiueos object is rebuilt to use the carrier. The 66 kernel objects still
  thread `base`/`length`; converting one is a separate change with its own
  byte-diff to justify.
- `[:slice :f32]` is declared and refused — there is no `slice-load-f32` on
  either ISA. It is the element type the carrier is *for*, and naming it while
  refusing it is the honest record rather than a gap left silent.
