# ADR 0383: extern calls with up to eight arguments on the object route

Status: accepted (JUN-556 E)

## Context

ADR 0380 (D1) lets the aiueos kernel object route call a declared `extern-<symbol>` function with
at most five parameters, passed in `rdi rsi rdx rcx r8` (the route's own convention; `r9` is the fuel
context register). The C functions that remain to be replaced by Kotoba objects call externs that
take six to eight arguments, and a System V callee expects the sixth in `r9` and the rest on the stack.

## Decision

* A declared extern may take up to eight parameters (`XO-EXT-MAX-ARGS`). Every other function of the
  object route is still capped at five; image and user routes are unchanged.
* At an extern call site the arguments follow System V: `rdi rsi rdx rcx r8 r9`, then the stack.
  The stack arguments are `push`ed from the last to the seventh, below the frame, so they cannot alias
  a temporary slot. An odd number of stack arguments is preceded by `sub rsp,8` to keep the 16-byte
  alignment. After the call and the existing `mov r9,[rbp-8]` context restore, `add rsp,8*(count+pad)`
  removes them. The relocation and the call tail the verifier reads (`e8 rel32`, `4c 8b 4d f8`) are
  unchanged.
* The shared call-site arity check in seed/70 admits up to eight arguments in mode 0; the callee's own
  parameter count must still equal the call's, and non-extern callees are capped at five by the
  function check, so no other call becomes admissible.
* Sources that declare no extern with six or more parameters compile to the same bytes as before
  (the pinned digests of the exports and windows gates are unchanged).

## Consequences

* `check-aiueos-object-externs.py` replaces the six-parameter refusal with a nine-parameter one and
  checks the 6/7/8-parameter call shape (r9 load, pushes, pad, cleanup).
* `verify-kotoba-kernel-object.py` in the kotoba repository must learn the push/pad/`add rsp`
  bracket before an object that uses it is adopted (follow-up; no object uses it yet).
* No x86 machine ran the new shape here; it was read back with llvm-objdump. A QEMU differential
  against a C callee with 6/7/8 arguments is the next verification step.
