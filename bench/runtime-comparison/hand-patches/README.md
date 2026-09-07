# Hand patches for the Reflect stage

`docs/codegen-coscientist.md`'s Reflect rule: falsify by hand-patching the
emitted code and measuring, before any compiler change. These are the patches
iteration 123 used, kept so its numbers can be re-derived rather than trusted.

## `strength-reduce-msub.py`

Rewrites every `MOV xM,#2147483647 … MSUB xD,xN,xM,xA` site into
`SUB xM,xN,xN,LSL #31` + `ADD xD,xA,xM` — clang's shape, one fewer multiply.
The scratch is xM (the constant's register, dead after the MSUB) and **not**
xN, because the quotient is live past the site in some domains.

```sh
python3 strength-reduce-msub.py <base.raw> <patched.raw>
```

**It is only exact where MOV and MSUB are 1:1.** `kernel_wide` and
`kernel_deep` hoist the constant into x13 once and share it across 16 and 24
MSUBs; rewriting that MOV destroys the constant for every later site. The
script reports how many sites it patched — compare that count against the MSUB
count before believing the output, and always re-run the manifest inputs.
Iteration 123's correctness gate caught exactly this on both domains.

## Two properties every patch here must keep

Byte length, so branch offsets do not move — which means a removal has to be
padded with a NOP, and the measurement therefore **understates** the compiler
change it stands in for. And the fuel contract: `contextFuelConsumed` must be
unchanged. A patch that alters it is measuring a different program.
