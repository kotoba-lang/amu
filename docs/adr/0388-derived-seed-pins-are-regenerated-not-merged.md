# ADR-0388 -- derived seed pins are regenerated, never merged by hand (JUN-631)

- Status: **stage 1 implemented** (null `sourceRevision`, `scripts/seed/repin-derived-pins.py`); stage 2 accepted, not implemented.
- Date: 2026-10-30
- Owner decision: 2026-10-30, "そういう状態が発生するのがそもそも問題" (the conflict state itself is the problem); apply with priority.
- Tracking: JUN-631. Found while merging amu#1699 (AWAI-118).

## Context

A seed change commits, next to its source, every artifact derived from it: the Mac and Linux root compilers,
`bin/amu-linux-x86_64`, the public Mac CLI, `native-product.json`, `seed/bootstrap/*.json` and the foundation-starter
descriptors. Each digest depends on the whole source tree, so:

- **any two seed PRs conflict** in those files, whatever sources they touch. Neither side of the conflict is right: the
  correct value is a build of the merged tree. amu#1699 hit this twice, after #1706 and #1708.
- **`sourceRevision` forced a follow-up PR per merge.** The writer clears it when the image changes, the audit refused a
  null value, and a commit cannot name itself. So each seed PR needed a second PR naming the first one's squash commit
  (#1708 is one), which conflicts again with the next seed PR.

## Decision

### Stage 1 (this change)

1. **`sourceRevision: null` means "the descriptor's own commit".** `audit-descriptor-source-revision.py` then audits the
   sources at the descriptor commit itself, and reports `sourceRevisionImplicit: true`. A stale descriptor (sources moved,
   pins not rebuilt) is still a `MISMATCH`. A non-null value is still checked as before. No follow-up PR is needed.
2. **Pin conflicts are resolved by regeneration only.** `scripts/seed/repin-derived-pins.py [--take-pins-from REF]`
   restores every pin file from REF (main's side after `git merge`), then rebuilds all of them on the merged source with
   the two-phase writer, rebuilds and repins the public CLI, and re-runs the public and `--check` gates. A conflict in a
   non-pin file stops it. Never pick either side of a pin conflict by hand, and never rebase a seed PR to resolve one.

### Stage 2 (accepted target, separate change)

Seed PRs carry source only; derived pins are produced from the PR's own source in CI and committed to `main` after merge.

- PR jobs consume compilers derived in the same run (`selfhost-native.yml` already derives them in `bootstrap-arm64` /
  `derive-x86_64`) instead of the checked-in pins. `check-native-identities.py` is split: pin-vs-pin consistency runs on
  PRs, pin-vs-source binding runs on `main`/repin only.
- A `main` repin job on macos-15 (`contents: write`) runs `repin-derived-pins.py` after each seed merge and pushes the
  result. This needs a bot identity allowed to push to `main` (repository setting, owner action).
- `seed/cdci/policy.json` / `seed/cdci/controller.kotoba` gate digests and the hard-coded module counts are derived too and
  join the same job.

## Consequences

- Stage 1 removes the follow-up PR and makes the conflict resolution one deterministic command; seed PRs still conflict
  with each other until stage 2.
- A null `sourceRevision` binds the tree that contains it, which is exactly what the audit checks; it is still not compiler
  build provenance or release qualification.
