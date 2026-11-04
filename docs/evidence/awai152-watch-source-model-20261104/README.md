# Process watcher source-operation model

The pinned packager source `seed/macos-process-watch-packager.kotoba` was
checked with the adjacent test-only Python source-operation model. It parses
the watcher builder operations and stubs every syscall; it does not compile,
assemble, build or execute the proposed helper. Run from the repository root:

```text
python3 docs/evidence/awai152-watch-source-model-20261104/model.py seed/macos-process-watch-packager.kotoba
```

The model accepts one successful request/response, refuses 26 syscall and
observation failure cases and nine invalid requests, and confirms that deleting
the token-mismatch branch causes its wrong-token control to be accepted. A
short write may have emitted a partial response, which is not success. The
model assumes meanings for raw instruction literals and builder operations;
it does not check actual instruction encoding, generated branch fixups, kernel
ABI, native process behavior, race safety, code signing, trusted host framing,
boot identity, crash recovery or resource release. The model is test evidence,
not an operational tool or a qualified governor.

The adjacent `lldb-encoding-model.py` separately models the source builder's
instruction encoding and asks the installed LLDB to disassemble the modeled
words directly from memory, without writing an executable. It checks 214
mnemonics, operands and branch targets and rejects deliberate register and
branch mutations. For macOS with the Command Line Tools installed:

```text
PYTHONPATH="$(lldb -P)" /usr/bin/python3 docs/evidence/awai152-watch-source-model-20261104/lldb-encoding-model.py seed/macos-process-watch-packager.kotoba
```

This checks a Python reproduction of the encoding, not bytes emitted by Amu.
It does not execute instructions or establish syscall semantics, host identity,
process containment, crash recovery, or permission to run a workload.
