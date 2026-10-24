# Canonical source admission

Tracking: [JUN-235](https://linear.app/kotobalabs/issue/JUN-235),
[JUN-241](https://linear.app/kotobalabs/issue/JUN-241), Kotoba Labs.

The shared source admission boundary now recognizes only `.kotoba`. This
removes the older permanent CLJK syntax-sugar/CLJC compatibility contract
from the actual classifier and its diagnostic data, extending the native
project cleanup in [Amu #1437](https://github.com/kotoba-lang/amu/pull/1437).

## Complete public contract

All four public names, argument counts and typed result descriptors remain:

| Function | Result / current decision |
| --- | --- |
| `source-kind(path)` | `Option<Keyword>`; only `.kotoba` yields `:kotoba` |
| `source-kind-present?(path)` | true only for canonical source |
| `admit!(path)` | `Result<String,Document>`; `.kotoba` accepted, other extensions refused in `:usage` |
| `admit-native-artifact!(value,path)` | `Result<Document,Document>`; source paths refuse in `:decode`, compiled artifact shape checks retained |

Removing old positive classifications must not turn a legacy source filename
into a valid artifact input. `.cljk`, `.cljc`, `.cljs` and `.clj` remain
recognized privately for refusal by artifact admission, with
`:source-kind :retired-source`. They are never public source kinds and never
accepted by `admit!`. Canonical `.kotoba` source keeps its existing
source-as-artifact refusal. Other paths still require a map with both actual
`:exports` and `:code` keys; present/missing key diagnostics remain. This
boundary does not replace the later real artifact/seal verifier.

The existing historical host adapter mirrors the same retirement policy;
it no longer advertises `.cljk` or `.cljc` as accepted source. That adapter is
still migration inventory, not a required native implementation or permission
to keep Node/JVM as a compiler host.

## Native closure and diagnostic data

The complete `source_path_core.kotoba` implementation now uses direct Kotoba
string byte-length/subsequence/equality operations. It no longer imports
`kotoba.lang.text` or requires the historical language compatibility root just
to recognize a suffix. It has no namespace dependencies or host imports.
Short/empty paths are bounded before substring extraction.

All typed diagnostic `document-map` keys are now explicit document keywords,
matching the document API's types. The existing message/data structure,
usage/decode phases, expected artifact description and missing/present key
payloads remain. This corrects typed construction rather than dropping errors
to admit the module. No native type-admission result is claimed.

## Evidence and remaining integration

Evidence is source-form/API/arity/reference and source/Git digest inspection
only. No compiler/implementation, native admission/build/artifact/runtime or
tests were executed or added. Previous Definition CID/Seed measurements in
historical checkpoints do not qualify this changed source revision.

All native compiler images, callers, module locks and source pins must select
the reviewed revision together. The full Node launcher/host callers, native
input writer/replay, upstream/ABI/helper behavior, Definition CIDs and whole
self-rebuild remain open under JUN-199/200/201/202/241. The already-retired
CLJK comparison and C-loader/KBB-first conditions are not restored as gates.
