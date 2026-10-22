# Native app-data scope-absence decision

Tracking: JUN-241 / JUN-201 / JUN-202, Kotoba Labs. Source candidate only.

The native provider must answer an out-of-scope path as absent, independently
of whether an object exists there. `tools/linux_static_handlers.kotoba` now
supplies owning decision op 48 instead of leaving the native mechanism to
trap for every non-EXISTS form.

`scope-absent-answer(form)` returns one for boolean forms 3/7/8/9/10/11/12,
whose answer is `0`; zero for data forms 0/1/2/4/5/6/13/14/15, whose answer is
empty text; and minus one for an unknown form. All sixteen operations are
retained. No unknown form or authority/resource/provider failure becomes a
successful empty result.

The whole original 52-function module and operations 0..47 remain. One
private function and op 48 are added; `decide(op,a,b,c,d)` retains its five-i64
ABI. Existing decisions are neither replaced by a smaller policy nor copied
into C/host code. The native #205 mechanism records genuine C1 scope denial,
uses this operation, and returns through the real byte/cell/UTF8 result gate.
Both rename paths are resolved before opening either parent. NUL in any
complete path span refuses before normalization; file content is not a path.

The complete C1 module also receives the actual admitted root spelling length
in op 8's formerly unused fourth data argument. Root `/` now admits its
descendants without requiring a second slash after the root prefix. Zero
retains the old argument contract; malformed lengths return an invalid
decision. Its public `decide` ABI remains five i64 values; the private scope
helper gains the root-length parameter, and other C1 operations are retained.
The native mechanism must carry this updated C1 artifact as well as the
handler artifact. Its shared open-at/parent path uses all-component no-symlink
resolution flags; the final link can still be inspected without traversal.

Matching ISA-specific C1 and handler artifacts must actually be built by Amu
selfhost, sealed and admitted from this exact updated source. Old compiled
decision artifacts without op 48 remain unsupported and cause a terminal
unknown-op refusal; no fallback uses a C loader or generated C header.

Whole filesystem/provider and caller qualification remains open, as do the
complete resolver/materializer/authoring ports, raw-byte I/O/digest, required
runtime helpers/ABI, reviewed main/pins and actual compiler self-rebuild.
No project/decision/provider implementation, filesystem operation, compiler,
generator/assembler, native admission/artifact/runtime or test was executed.
No tests were added; no workflow/protection/service/production change ran.
