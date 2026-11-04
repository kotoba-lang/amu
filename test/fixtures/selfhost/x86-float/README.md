# x86 floating SIR candidate

`seed/70-x86_64-linux.kotoba` implements the 36 existing floating SIR tags:
binary64/binary32 arithmetic/min/max, comparisons, negation/absolute/sqrt,
the six integer/width conversions. Values remain raw-bit GPR carriers, with
binary32 results sign-extended. The code uses SSE2 and no floating runtime,
host numeric conversion or C loader. Checked conversions and transcendental
heads missing from the seed frontend are not silently admitted by this work.

Each operation saves/restores MXCSR and uses nearest-even rounding with
exceptions masked and DAZ/FTZ disabled. The extra 16-byte scratch reservation
is counted against the existing 4096-byte frame limit; integer-only frames
are unchanged. MIN/MAX explicitly handle NaN and signed zero instead of
using the different MINSD/MINSS selection rule. Float-to-i64 conversion
handles NaN and positive overflow before CVTT; negative overflow saturates
to MIN. No additional NaN payload-selection promise is introduced.

Scalar ELF retains its main()->i64 public boundary and handle/capability
refusals. The context route retains raw-bit stack arguments. The kernel
object route now selects private profile 2, preserving its original integer
signatures and rejecting all floating SIR, including unreachable code.

Required native sources:

- `native/x86_float_test.kotoba`: main=511 across nine groups covering all 36
  tags, NaN/SNaN ordered comparisons, signed-zero min/max in both operand
  orders, NaN/overflow/divide-by-zero arithmetic, integer saturation,
  exact/rounded conversions, gradual underflow,
  sqrt and five-register private calls.
- `native/x86_float_stack_test.kotoba`: context-profile main=3; six-argument
  binary64/binary32 calls exercise the first stack argument and continuations.
- `seed/tests/unit/x86_float_t.kotoba`: expected 15; all 36 tags in both Linux
  profiles, all 36 refusals in the kernel profile, thirteen numeric tag gaps,
  type/profile boundaries and frame accounting. Assemble the complete
  X86_64-LINUX-MANIFEST with only 72-x86-cross-entry replaced by this unit
  fragment; it retains the original xg-default/driver helper. One compiler
  arena is reused, not allocated for each check.
- `refusals/`: scalar public floating result/parameter and handle result,
  kernel floating result/operation. All must fail before an artifact is
  published. Existing unknown-SIR, arity, capability and fuel controls remain
  required; these fixtures are not a substitute for them.

The instruction review used 36 independently hand-assembled fragments and LLVM
disassembly against [Intel SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html).
That instrument neither evaluated these Kotoba sources nor executed the
bytes. It is not emitted compiler output, a new build dependency or a native
qualification gate. Source structure, call arity, relocation-shape and manifest
checks likewise do not establish runtime behavior.

The scalar ELF gate must compare the full eight-byte stdout result, not only
the process exit status: main=511 would otherwise lose its ninth group in
the low eight exit bits. A zero-status run alone does not pass this corpus.

**Native type checking, compilation and execution have not run.** Keep this
candidate unqualified until Amu selfhost builds the complete loaderless
compiler and runtime/package/launch closure, executes all positive/refusal/
fuel/caller-MXCSR controls and the unchanged full document/formatter/Kami
component gates. Preserve source/lock/artifact and generation evidence. Do
not use a historical C-loader or hosted interpreter to produce a passing result.
