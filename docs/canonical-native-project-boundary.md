# Canonical Kotoba native project boundary

Tracking: [JUN-235](https://linear.app/kotobalabs/issue/JUN-235),
[JUN-202](https://linear.app/kotobalabs/issue/JUN-202), Kotoba Labs.

This source candidate implements the owner's retirement of permanent CLJK
syntax sugar in the native project entry. It extends the existing typed-map
interface draft [Amu #1437](https://github.com/kotoba-lang/amu/pull/1437).
Current main was merged into that clean branch without rewriting its prior
commit or touching shared WIP. The earlier closed typed-map implementation
and all its positive/refusal source branches remain.

## Retired product routes

- Path discovery and entry validation accept `.kotoba` only. They no longer
  probe `.cljk`/`.cljc`, choose a legacy extension or lower a discovered file.
  Multiple canonical candidates still refuse as ambiguous; a missing module
  still fails. An explicitly supplied legacy entry also refuses with a lock.
- Native CLI commands remain `check`, `check-entry` and `modules`, with
  locked or explicitly `--unpinned` graph selection. `compare-hir` and its
  three private comparison functions are removed. No old comparison pass is
  substituted for actual native qualification.
- Native frontend public `analyze-cljk-source`, `lint-cljk-source` and
  `validate-cljk-expression-source` are removed. Canonical type/expression
  validation, analysis, project analysis and lint remain. The frontend and
  project linker no longer import `syntax-sugar` or select a lowering arm.
- `make-source-formatted` and the `:surface` field are removed from all four
  owning/consumer schema declarations. Every source constructor/selector and
  the linked public call arities are updated together.

## Current public source APIs

| Boundary | Canonical arguments |
| --- | --- |
| `native-project/make-source` | namespace, source text |
| `native-frontend/analyze-project-source` | source text, dependency packet |
| `native-project-linker/link-project-source` | source text, dependency packet |
| `native-project-linker/link-project-forms` | parsed forms, source text, dependency packet |

These are intentional source API/record-layout changes. New compiler images,
module locks, dependency packets and callers must select the same reviewed
source revision. An old artifact with the former boolean/layout is not a
compatible caller merely because export names agree. Definition CIDs and
actual ABI behavior remain unmeasured.

Canonical packet bytes keep their existing framing: `0`, newline,
namespace-byte-length, newline, source-byte-length, newline, namespace bytes,
then source bytes. Marker `1` and every other nonzero marker now refuse;
they are never relabelled canonical. Empty dependency packets retain their
empty-list meaning. All existing packet/module/edge/source-size limits and
truncation/length checks remain.

## Preserved component behavior

The complete five-function reserved-name guard is extracted unchanged into
`source_names.kotoba`. Executable reserved names still refuse; quote data and
case test literals retain their exact previous handling. There is no always
false guard, reduced traversal or lowering dependency hidden in that module.

The locked resolver retains lock schema/root/module/CID validation, exact
source digest verification, namespace matching, dependency order, missing
block/pin/cycle and budget failures, with no path fallback. Its complete
function form changes only the old constant-false frame argument and the
directory check described below. Root/alias/path rules and ambiguity checks remain. Native project
import alias/refer/private/export/schema/collision/type/resource checks and
closed typed-map interfaces remain; interface stubs are still analysis data,
not executable module links.

The block-store check previously reused the file `EXISTS` predicate for a
directory. Its historical host adapter accepts regular files only; the native
candidate checks whether open succeeds, so that predicate did not establish
directory kind consistently across providers. The resolver now requests
`STAT`, parses all four fields through the existing canonical decimal-text
module and requires the directory-kind field to be 1. Lock files and CID
blocks retain their existing file predicate. Missing/non-directory stores
refuse explicitly. This removes the resolver's reliance on ambiguous existence
semantics; no runtime rejection or recovery was reproduced in this work.

The historical paired fixtures and their cases are preserved. Their README
instructions now describe canonical entry and historical comparison evidence;
no test implementation or fixture source was added, deleted or executed.

## Remaining whole-closure work

This is draft source, not owning-main landing, native source/type admission,
Definition CID equivalence, executable project linking or a self-rebuild.
The selected `kotoba.sema`/reader/value/type owners, remaining compiler/seed
entrypoints, source/lock integration, generic native writer/replay and required
runtime/ABI helpers still require full canonical integration/qualification.
No claim is made that every remaining legacy reference in the repository or
all compiler dependencies is removed by this boundary cleanup.

Native packaging and hash/cwd routes are separate prepared candidates in
[native #205](https://github.com/kotoba-lang/kotoba-native/pull/205),
[Amu #1440](https://github.com/kotoba-lang/amu/pull/1440) and
[profile #805](https://github.com/kotoba-lang/kotoba-lang/pull/805). Their
provider availability and exact source/lock selection remain unqualified.
Required order remains owning components/native mechanisms, reviewed
source/lock integration, native compiler generations, whole self-rebuild,
then the two actual Kotoba/Amu selfhost CDCI gates and native controller.

Evidence here is source-form/export/import/record/arity/reference/digest and
Git metadata inspection only. No project implementation, compiler, build,
generator, native admission/artifact/runtime or tests were executed. No
workflow/protection, live service or production route changed.

The structural inventory reads nine sources, 203 functions, 20 internal import
calls and 186 record uses. It reports no delimiter/export/import/own-call/
record-field/constructor findings. The complete reserved-name guard's five
function forms match their source exactly. The locked resolver form matches
after normalizing only the retired false frame argument, explicit directory
predicate and its diagnostic. These source comparisons do not establish
native admission, Definition CIDs or execution behavior.
