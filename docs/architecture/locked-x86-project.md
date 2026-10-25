# Typed native x86 project adapter

JUN-93's shared modules require internal reference values that the bounded
integer-only kernel image adapter cannot admit. `seed/98-x86_64-project.kotoba`
uses the adopted project's discovery/lock/namespace/schema/type/interface
implementation and the existing x86 backend/native KX64 runner. It preserves
the full47 compiler, all18 adopted core modules and every selected declaration.

Dependencies compile first. Import stubs are tail jumps to previously emitted
module entries; argument, return and hidden-context conventions are retained.
Relative code/pool references move together. Code-base-relative string literal
offsets additionally receive the module's byte base. Interface offsets are
converted from the existing AArch64 word units into x86 byte units. A bounded
prefix jumps to the root's zero-argument i64 main. Native runner/code formats
are unchanged; no host compiler, image writer or C loader is introduced.

`check-x86-project-native.py` tests multi-hop imports, per-module strings and
keyword identity, returned records/documents, eight arguments and a captured
callback. It also requires named refusal/no artifact for bad or missing locks,
unpinned mode, wrong format, unknown flags and an unreachable invalid declaration.
ARM compile-only receipts cannot stand in for the fixture's native x86 verdict42.
The canonical shared component gate separately requires native verdict0 for
text/DOM/text-edit and records every actual source hash and exact lock.

The boundary is pure native Linux execution. Capabilities, unsupported floats,
invalid external entries and unsupported operations refuse. The kernel heap/
value runtime, shared CSSOM/surface/input, Itonami dapps and persistence remain
later integration gates; none is implied by this adapter's success.
