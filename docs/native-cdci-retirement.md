# Retire Amu's remaining legacy workflow registrations

Tracking: [AWAI-66](https://linear.app/kotobalabs/issue/AWAI-66), Kotoba Labs.
Codex thread: 01a15eb9-ef0b-73f3-a095-1a1af90d3a21.

The owner's final CDCI roles are Amu selfhost and Kotoba native. Both gates
and their controller must be Amu-produced loaderless x86_64-linux-static ELF,
with no CLJK/CLJC/CLJS, NBB/KBB, Clojure, JVM/Java/GraalVM, Node or C
compiler/loader/runtime in the build and execution closure. Python/shell
orchestration and historical hosted comparisons do not qualify that native
controller. The old fleet-ci-gates / kotoba-authoring labels are not additional
final gates. Full compiler/project/runtime behavior and the complete corpus
remain required; a smaller passing slice is not completion.

## Removed registrations and their dependent checker

| Workflow | Declared jobs | Obsolete execution dependency |
| --- | ---: | --- |
| test.yml | 11 | Node/NBB compiler and provider suites, Python seed/custody orchestration and C-loader verification |
| browser-matrix.yml | 2 | Node/Playwright/npm browser and Safari harnesses |
| fuzz.yml | 1 | Node/NBB libFuzzer/C orchestration, scheduled weekly or manually dispatched |
| seed-x86_64-linux.yml | 4 | Node-installed/Python-driven seed preparation, cross-build and C-loader execution |

These counts are declared jobs, not expanded matrix executions. All four
workflow registrations (532 lines) are deleted. This removes their future
push/PR, weekly and manual dispatch paths. It does not cancel an already
running job or stop a live service.

The 84-line Node/KBB workflow checker and its npm entry are also deleted.
That checker required the old workflow files, pinned Node 24.12.0, NBB
prefetch/tests and a historical shell regression command to exist. Keeping
it would recreate obsolete migration blockers after deleting the workflows.
Its action-pin and supply-chain concerns remain obligations of the native
replacement, without retaining a Node/KBB executable or a blanket rule that
silently excludes required component behavior.

Canonical compiler/provider/source components, tests, fuzz seeds, historical
build/corpus drivers and evidence files are unchanged by this cleanup, except
for hosted helper/provenance comments that claimed the removed checker
enforced them or that a partial host swap removed the whole runtime. No test
is added or run. Complete pre-retirement workflow/checker paths,
Git blobs, job names and schedule are recorded in
[the machine retirement record](native-cdci-retirement.edn), from main
`ff6b4743c3729430048184d98b43c3829da4bb62`. Historical execution receipts keep
their original compiler/runtime provenance. They do not prove the native
replacement, and ephemeral Actions artifacts are not assumed available.

## Temporary required-context hold

A fresh read before this cleanup showed only `merge-guard` (GitHub App
15368, strict=false) as a required status on main, admin enforcement enabled,
force pushes/deletions disabled, zero required reviewers, and no applied
branch rules. None of the four deleted workflows supplies that required
context. Keep the merge-guard workflow/script and all protection settings
unchanged. Its retirement remains separately held in
[Amu #1439](https://github.com/kotoba-lang/amu/pull/1439), pending the exact
human approval requested there. This is a temporary exception to finish,
not a third accepted native gate or a new hosted comparison requirement.

Removing old jobs reduces legacy automated coverage while the native
replacement is still unavailable. No unconditional success, skipped-test
pass, hosted fallback or synthetic native qualification flag is installed.

## Open native acceptance

The actual native compiler and full command/project/resolver/materializer/
packaging closure, exact source/lock/Definition CID and sealed decision
artifacts, remaining ABI/runtime/byte capabilities/raw-file/hash/I/O, complete
positive/refusal/resource/corpus execution and Amu-produced self-rebuild
remain open. Build, admit and qualify the controller and the two real native
gate artifacts before registering them. Record compiler generations,
artifact digests, forbidden-process evidence, authority/resource behavior
and the actual fixed point. Current source drafts and historical subset
receipts do not satisfy those requirements.

This cleanup establishes absence of the four legacy workflow registrations
and their checker. It does not establish that all legacy source has been
retired, that the remaining merge-guard hold is resolved, or that CDCI is
qualified. Product/static-hosting/browser consent and production-cutover
rules remain separate and unchanged.
