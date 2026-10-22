# Root artifact pin and lock cleanup

Tracking: [JUN-202](https://linear.app/kotobalabs/issue/JUN-202),
[JUN-201](https://linear.app/kotobalabs/issue/JUN-201),
[JUN-200](https://linear.app/kotobalabs/issue/JUN-200), Kotoba Labs.

## Concrete source/data change

The root artifact pin in both `deps.edn` and `deps-lock.edn` now selects owning
main `b6e3ab59611e747dcc9a72c4152cb59384951190`, also selected by the
[native #205 candidate](https://github.com/kotoba-lang/kotoba-native/pull/205),
head `a7cf445c3aaad5f7e921e99453a9fe12c08f064d`. It replaces the off-main
child `ce6f82d398467ba5504c8d377b47a8ca2dc185c3`, which changes only a
C-loader identity constant. Both revisions contain the identical canonical
artifact core blob `ff7f780734f55b730505023522a3c76b11cb46d9`.
Old comments making the C loader and root pin move together are removed.

The retired `scripts/lock-classpath.cljk` invoked Node and `clojure -Spath`
to author a lock, with a KBB launcher/recommendation. Its npm alias is removed.
README and retained historical consumer diagnostics no longer prescribe that
generator or a JDK authoring exception. Missing/stale locks remain refusals
with the existing phase/expected/actual data; native lock authoring is named
as unqualified under JUN-202. Existing Node launchers and hosted namespaces
are migration inputs, not a qualified native entry or Q9 evidence.

## Incremental lock evidence

This is an explicit manifest-equivalent Git revision update of historical
lock data. A complete dependency resolver was not rerun, and the lock is not
claimed as produced by an Amu-selfhost-built writer.

Before the update, the recorded digest equalled the raw root deps bytes:
`15b535370905537301afa4479cbaa6d04dd17286474090a575683abdc1f2c959`.
The artifact dependency manifest is the identical Git blob at both revisions:
`38f649b6b4af9071d8e452ae3cc3ede55be13099`. Apart from the artifact SHA,
all root manifest data are unchanged. The complete lock retains all 85 root
entries and every alias addition: execution-v2=9, native-run=1, test=4.
Every URL, path, order and other pin is retained. Lock data changes only the
artifact SHA, root-deps digest and truthful update-provenance string.

New raw `deps.edn` SHA-256, equal to `:lock/deps-digest`:
`2690780de69ff9c86729de850f47b3f85c32b09bda8d491d140ef392176328fe`.
Lock file SHA-256:
`bd8a6c478875e3db4a72d3708a226bd362b96d9e51727c9f3b5c7b4bd00f73cd`.
The resolver provenance is
`git-manifest-equivalence/v1; native-writer-unqualified`.

Static source/data readers compared the entire old/new EDN and JSON forms,
retained alias tables, exact manifest blobs and consumer function forms. The
package data differ only by removal of the old generator alias. Consumer
function bodies are preserved apart from retirement diagnostics and their
documentation. The existing version/digest/checkout/path/alias refusal logic
is retained. No project implementation, resolver, lock materialization,
compiler, artifact/digest routine, native runtime or test was executed.
Existing suites and workflow/protection settings are untouched.

## Required native work

JUN-202 still requires a complete canonical Kotoba/native resolver and writer,
whole dependency selection and ordering, source admission, missing-input and
conflict refusals, reproducible materialization and actual native execution.
It must cover the complete graph and aliases; the update above is not a
generic lock-generation implementation or a smaller substitute for that work.
The old KBB/JDK generator is no longer a required comparison/authoring route.

Native admission, real hash provider/profile and sealed decision artifacts,
full-domain artifact canonicalization, owning-main/reviewed pin integration,
required ABI/runtime helpers and compiler g0..g3 self-reconstruction remain
open under JUN-200/201/202. The proposed root pin changes the historical
C-loader identity value; that route is retirement inventory, without native
qualification credit. This draft must not activate the profile or claim
product/CI readiness ahead of the actual replacement closure.
