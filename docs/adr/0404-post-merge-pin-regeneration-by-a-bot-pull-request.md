# ADR 0404: Derived pins are regenerated after merge by a bot pull request (JUN-818)

Status: proposed (design only). The workflow `.github/workflows/post-merge-repin.yml` ships
**disabled**; enabling it is an owner action listed under "Owner decisions".

## Problem

Derived pins (bootstrap roots, `bin/amu-linux-x86_64`, `native-product.json`, Mac CLI and
foundation-starter descriptors, `seed/cdci/*`, `seed/79` role hashes, `seed/compiler-core.json` and the
adoption receipt) are build outputs of the whole seed tree. Today each seed PR regenerates them
(`scripts/seed/repin-all-pins.py`, Mac arm64, ~8 min), then needs full PR CI (~28 min) and queue CI
(~6 min). Every merge to main makes the pins of all waiting PRs stale, so they repin and rerun, and two
pin-changing PRs always conflict in the queue. Measured 2026-11-04: 30-90 min to land one pin PR, one at
a time.

## Decision

1. PRs carry source only. PR CI keeps checking source-level correctness (compile, qualification,
   negative controls) and stops requiring pin freshness (phase B below).
2. After a merge to main, a bot job regenerates the pins on the exact merged commit and lands them as one
   bot pull request through the normal merge queue. One bot PR covers any number of source merges since
   the last pin commit (batching), so pin churn is paid once per batch rather than once per PR.

## Workflow shape (`post-merge-repin.yml`)

- Triggers: `workflow_dispatch` always; `push` to main only when repository variable
  `AMU_POST_MERGE_REPIN_ENABLED == 'true'` (default unset, so the push path is off). Paths that are pin
  outputs are ignored for the trigger, and commits whose subject starts with `repin:` by the bot are
  skipped, so a bot PR never retriggers itself.
- Runner `macos-15` (arm64), the same runner `mac-selfhost-aiueos` already uses; the Mac fixed point does
  all compilation (native only; no JVM, nbb or babashka).
- Steps, in order, each fatal:
  1. checkout the exact `github.sha` (no PR code is ever executed with the token; the token is read only
     in the last step);
  2. `repin-all-pins.py --check`; exit 0 means nothing to do (stop, no PR);
  3. `repin-all-pins.py` (write mode, fixed point);
  4. **path allowlist**: `git status` may touch only the pin file set (`PIN_FILES`, `DERIVED_FILES`, the
     `seed/79` role-hash lines, the adoption receipt named by `compiler-core.json`). Any other path or any
     non-hash line change in `seed/79` fails the job;
  5. `repin-all-pins.py --check` again on the result (the gate: regenerating is idempotent and the tree is
     a fixed point), and `test-repin-all-pins.py` (each stale pin must fail `--check`);
  6. push branch `bot/repin-<sha12>` and open a PR; enqueue it with GraphQL `enqueuePullRequest`.
- The bot PR's own CI is the normal full CI for a pin-changing PR. This is the independent verdict on the
  regenerated Linux bytes (arm64/x86_64 bootstrap and qualification run on the PR). A bot commit never
  lands without it.

## Trust boundary

A bot builds and commits bootstrap binaries. Controls:

- The bot can only open a PR; it cannot push to main or bypass the ruleset (ruleset 26342259 requires the
  queue and the required checks). No bypass actor is granted.
- The generating code is the repository's reviewed `repin-all-pins.py` at the merged commit, run from main
  (never from a PR branch).
- Output is confined by the path allowlist and verified twice (`--check`) plus by full CI on the PR.
- `sourceRevision` stays `null` (see AGENTS.md "Derived seed pins"), so no follow-up naming PR is needed.
- Rollback: revert the bot PR (it is an ordinary squash commit), or unset
  `AMU_POST_MERGE_REPIN_ENABLED` to stop the path at once. The previous pins stay valid for the previous
  source, and a stale-pin main is detected by the scheduled `--check`.
- Negative controls: `test-repin-all-pins.py` keeps proving that every stale pin fails `--check`; the
  allowlist step has its own control (`scripts/ci/test_repin_allowlist.py`, a changed non-pin path must fail).

## Phases

- A (this PR): ADR + disabled workflow + allowlist checker and tests. No behavior change on main.
- B (separate PR, after the owner enabled the bot and one bot PR landed): PR CI stops failing on stale
  pins. This must keep a mandatory pin check at merge_group time **or** rely on the bot PR plus a
  scheduled `--check` on main; the choice is an owner decision because between a source merge and the
  bot PR main has source/pin skew. Required check context names are unchanged.
- C: measure before/after and tune the queue (measure 4).

## Owner decisions / grants needed

1. Credential: a GitHub App (preferred) installed on `kotoba-lang/amu` with `contents: write`,
   `pull-requests: write`, `workflows: none`, exposed as secret `AMU_REPIN_TOKEN` (an installation token or
   fine-grained PAT). Creating it is not done by the agent.
2. Set repository variable `AMU_POST_MERGE_REPIN_ENABLED=true` to turn on the push trigger.
3. Accept the main skew window of phase B (or keep a pin check in merge_group).
4. Approve a bot-authored PR path (merge via queue, no human review required for pin-only PRs?).
