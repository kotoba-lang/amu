#!/usr/bin/env node
// merge-guard: report when a PR's merge into the base branch would destroy
// main-side work. Written after the 2026-10-20 incident (amu#1339): a bot
// resolved conflicts with --theirs, "recovered" with `git revert -m 1` of its
// own main merges, and the next merge deleted 408 main-side files (128,777
// lines). See JUN-263.
//
// ADVISORY BY DEFAULT (owner decision, 2026-10-21): refactoring flows rewrite
// and delete large trees and merge main repeatedly, and a blocking gate gets in
// their way. The default mode prints findings and always exits 0; nothing here
// stops a merge. Set MERGE_GUARD_MODE=fail to make the findings block instead.
//
// Three findings:
//
// 1. Merge-side deletion. Every file the merge result deletes relative to the
//    base should also be deleted by the PR's own non-merge commits. A deletion
//    that only appears in the merge result is merge-resolution damage, not
//    intent. (Rename/delete interactions in large refactors can trip this
//    legitimately — one reason it reports instead of blocks.)
//
// 2. Revert-of-main-merge. A non-merge commit whose tree restores the pre-merge
//    state of a merge that brought main into a diverged branch
//    (`git revert -m 1` of such a merge) records the inverse of main's work as
//    the branch's own change. Detected structurally, not by commit message (the
//    incident's reverts carried hand-written subjects): commit C is flagged
//    when a main-merge R before it has parents [A, B] with B on the base
//    history and A off it, and every path R touched holds A's blob at C.
//    Reverting a merged *PR* (a merge whose both parents are on the base
//    history) is the normal revert-PR route and is never flagged.
//
// 3. Mass deletion. More than MERGE_GUARD_MAX_DELETED_LINES (500) deleted
//    lines in the merge result. Informational only in warn mode; in fail mode
//    intentional large deletions set MERGE_GUARD_ALLOW_MASS_DELETION=true.
//
// Usage: MERGE_GUARD_BASE=<sha> MERGE_GUARD_HEAD=<sha> node scripts/merge-guard.mjs
// (In CI the workflow passes the pull request's base and head SHAs.)

import { execFileSync } from "node:child_process";

const BASE = process.env.MERGE_GUARD_BASE;
const HEAD = process.env.MERGE_GUARD_HEAD;
const MODE = (process.env.MERGE_GUARD_MODE ?? "warn") === "fail" ? "fail" : "warn";
const MAX_DELETED_LINES = Number(process.env.MERGE_GUARD_MAX_DELETED_LINES ?? "500");
const ALLOW_MASS_DELETION = (process.env.MERGE_GUARD_ALLOW_MASS_DELETION ?? "false") === "true";

if (!BASE || !HEAD) {
  console.error("merge-guard: MERGE_GUARD_BASE and MERGE_GUARD_HEAD are required");
  process.exit(2);
}

function git(args) {
  return execFileSync("git", args, {
    encoding: "utf8",
    maxBuffer: 256 * 1024 * 1024,
    stdio: ["ignore", "pipe", "ignore"],
  }).trim();
}

function gitLines(args) {
  const out = git(args);
  return out === "" ? [] : out.split("\n");
}

function isAncestor(ancestor, descendant) {
  try {
    execFileSync("git", ["merge-base", "--is-ancestor", ancestor, descendant], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

const findings = [];
const warnings = [];

// --- Range shape ------------------------------------------------------------
const mergeBase = git(["merge-base", BASE, HEAD]);
if (isAncestor(HEAD, BASE)) {
  console.log(`merge-guard: ${HEAD} is already contained in ${BASE}; nothing to merge`);
  process.exit(0);
}

// --- Merge result ----------------------------------------------------------
// git merge-tree --write-tree prints the merged tree OID on the first line and
// exits 0 on a clean merge; on conflicts it still prints a tree OID but exits
// 1 and appends conflict information.
let mergeTree;
let mergeConflicts = [];
try {
  const out = git(["merge-tree", "--write-tree", BASE, HEAD]);
  mergeTree = out.split("\n")[0];
  mergeConflicts = out.split("\n").slice(1).filter((l) => l.trim() !== "");
} catch (error) {
  const out = String(error.stdout ?? "");
  mergeTree = out.split("\n")[0];
  mergeConflicts = out.split("\n").slice(1).filter((l) => l.trim() !== "");
  if (!/^[0-9a-f]{40}$/.test(mergeTree ?? "")) {
    findings.push(`merge-tree could not compute a merge result for ${BASE}..${HEAD}: ${out.slice(0, 500)}`);
  } else {
    // A conflicted PR cannot merge anyway; GitHub reports it as dirty. This is
    // a note, not a finding.
    warnings.push(
      `the PR conflicts with the base branch; the deletion checks below cover ` +
        `the merge-tree result only (${mergeConflicts.slice(0, 10).join(" | ")})`,
    );
  }
}

if (mergeTree && /^[0-9a-f]{40}$/.test(mergeTree)) {
  // --- Finding 1: merge-side deletions should be the PR's own deletions ----
  const mergeDeleted = new Set(
    gitLines(["diff", "--diff-filter=D", "--name-only", BASE, mergeTree]),
  );
  const ownDeleted = new Set(
    gitLines(["log", "--no-merges", "--diff-filter=D", "--name-only", "--format=", `${BASE}..${HEAD}`]),
  );
  const undeleted = [...mergeDeleted].filter((f) => !ownDeleted.has(f)).sort();
  if (undeleted.length > 0) {
    findings.push(
      `the merge deletes ${undeleted.length} file(s) that the PR's own non-merge commits never deleted ` +
        `(merge-resolution damage): ${undeleted.slice(0, 20).join(", ")}${undeleted.length > 20 ? ", …" : ""}`,
    );
  }

  // --- Finding 2: revert of a main merge ---------------------------------
  // Merges in the PR's line that brought the base history into a diverged
  // branch: parents [A, B], B on the base history, A off it.
  const mainMerges = [];
  for (const sha of gitLines(["rev-list", "--merges", `${BASE}..${HEAD}`])) {
    const parts = git(["rev-list", "--parents", "-n", "1", sha]).split(" ");
    const [A, B] = parts.slice(1);
    if (parts.length === 3 && B && isAncestor(B, BASE) && !isAncestor(A, BASE)) {
      mainMerges.push({ sha, A, B, paths: gitLines(["diff", "--name-only", A, sha]) });
    }
  }
  for (const c of gitLines(["rev-list", "--no-merges", `${BASE}..${HEAD}`])) {
    const parents = git(["rev-list", "--parents", "-n", "1", c]).split(" ").slice(1);
    if (parents.length !== 1) continue;
    for (const { sha, A, paths } of mainMerges) {
      // Only a commit after the merge can invert it.
      if (paths.length === 0 || !isAncestor(sha, c)) continue;
      // Every path the main merge touched must hold A's blob at c for this to
      // be an inversion of that merge.
      let inverted = true;
      for (const path of paths) {
        let blobAtA;
        let blobAtC;
        try {
          blobAtA = git(["rev-parse", `${A}:${path}`]);
        } catch {
          blobAtA = "(absent)";
        }
        try {
          blobAtC = git(["rev-parse", `${c}:${path}`]);
        } catch {
          blobAtC = "(absent)";
        }
        if (blobAtA !== blobAtC) {
          inverted = false;
          break;
        }
      }
      if (inverted) {
        findings.push(
          `commit ${c.slice(0, 12)} restores the pre-merge state of main-merge ${sha.slice(0, 12)} ` +
            `on all ${paths.length} path(s) it touched: a revert -m 1 of a main merge records the inverse ` +
            `of main's work as this branch's own change. Recover with git reset to a new branch from the ` +
            `pre-merge tip, or redo the merge with a faithful port.`,
        );
        break;
      }
    }
    const body = git(["log", "-1", "--format=%B", c]);
    if (/revert -m 1/i.test(body)) {
      warnings.push(
        `commit ${c.slice(0, 12)} explains a "revert -m 1" in its body; if it inverts a main merge ` +
          `partially, the structural check above can miss it — review by hand`,
      );
    }
  }

  // --- Finding 3: mass deletion ------------------------------------------
  let deletedLines = 0;
  for (const line of gitLines(["diff", "--numstat", BASE, mergeTree])) {
    const [add, del] = line.split("\t");
    if (del !== "-") deletedLines += Number(del);
  }
  if (deletedLines > MAX_DELETED_LINES) {
    const message =
      `the merge result deletes ${deletedLines} lines against the base (informational limit ` +
      `${MAX_DELETED_LINES}). Large refactors do this on purpose; in fail mode set ` +
      `MERGE_GUARD_ALLOW_MASS_DELETION=true in .github/workflows/merge-guard.yml to acknowledge.`;
    if (ALLOW_MASS_DELETION) warnings.push(`${message} (acknowledged)`);
    else findings.push(message);
  }

  console.log(
    `merge-guard: base ${BASE.slice(0, 12)} head ${HEAD.slice(0, 12)} ` +
      `merge-base ${mergeBase.slice(0, 12)} merge-tree ${mergeTree.slice(0, 12)} ` +
      `deleted-files=${mergeDeleted.size} own-deleted-files=${ownDeleted.size} ` +
      `deleted-lines=${deletedLines} main-merges=${mainMerges.length} mode=${MODE}`,
  );
}

for (const w of warnings) console.log(`merge-guard note: ${w}`);
for (const f of findings) console.log(`merge-guard: ${MODE === "fail" ? "FAIL" : "WOULD-FAIL"}: ${f}`);
if (findings.length > 0 && MODE === "fail") process.exit(1);
console.log(
  findings.length > 0
    ? `merge-guard: ${findings.length} finding(s) reported, not blocking (MERGE_GUARD_MODE=warn)`
    : "merge-guard: clean",
);
