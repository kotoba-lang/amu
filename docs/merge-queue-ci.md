# Merge queue CI

The `main` merge queue validates the combined merge-group candidate with the
`selfhost-native` PR tier. Its native bootstrap, ARM and x86 qualification,
benchmark, browser-target and shared-component jobs are required checks. The
workflow runs for every PR targeting `main`, including documentation changes,
so those checks are emitted consistently. The `merge_group` event uses the same
PR tier and shard plan; pushes to `main` and scheduled runs retain their own
broader tiers.

The merge-side deletion and revert guard remains an advisory PR-only check.
It is not a queue-level required check. The queue does not turn cached artifacts
or historical receipts into native verdicts. When changing a required job name,
update the repository ruleset and confirm that both PR and merge-group events
emit the new check before enforcing it.
