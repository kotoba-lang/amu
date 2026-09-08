import io

path = "docs/codegen-coscientist.md"
with io.open(path, "r", encoding="utf-8") as f:
    text = f.read()

anchor = "## Standing honesty constraints"
assert anchor in text, "anchor missing"
assert text.count(anchor) == 1, "anchor not unique"

entry = (
"2026-09-08 23:52 JST (amu-rank cron, tick 314): host busy(pre-run monitor load1 136.38 / load5 124.68 / load15 92.59, up 3d 16:35, 6 users, threshold 7.5; live probe uptime 23:52: load1 104.44 / load5 118.29 / load15 92.09) - measurement refused, rank-only busy pass. git fetch clean(no new origin commits since tick-312 read; origin/main UNCHANGED at 26401d2f = Merge PR #900 'the compiler gets a ClojureScript test runner'; upstream test/infra, origin-namespace, NOT local-reconcilable; local branch spike/kbb-jvmfree-envread still diverged/behind origin, merge/reconcile left for the operator). local HEAD 6fc47fa6 = tick-313 busy+fold commit. guard-glob residue 149 -> 150 untracked lines local-uncommitted (`git status --porcelain -- src bench scripts deps.edn` = 150, regime unchanged: append/probe scripts under docs/ + scripts/ + build-time-os sidecars + ADR 0339 untracked). Folded 1 uncommitted sibling busy-refusal landed since tick-313 commit(amu-bench 2026-09-08 23:33 JST H-C2 evidence cell: host load1 92.53 / load5 62.73 / load15 55.69, up 3d 16:15, 6 users, threshold 7.5, quiet-gate refusal, no measurement, no numbers, NEXT remains H-C2) - a busy refusal, NOT a new local measured verdict(folding evidence, no status edit). Pre-run monitor NEXT read \"H-Y1 remain open. NEXT: H-C2\" is STALE(unchanged from ticks 296-311; H-C2 has not been rank-authority NEXT since iter-56); authoritative NEXT is the committed tick's rank line below. No new local codegen ADR since tick-313 read(0345 remains latest registered, first QUALIFIED imod lever verdicts on benjamin at quiet gate; perfgate.core/qualify for kotoba-native imod inlining NOT yet issued; ADR 0339 remains UNTRACKED/residue locally). No new LOCAL measured verdict -> no re-rank, no status transition, no new hypothesis;; population unchanged(post-284: H-Z4 registered open(port ADR-0345 imod helper-call inlining to kotoba-native, expected separated >=5%), H-Z3 top of codegen ladder(quiet-host A/B still blocked by guard-glob residue + repo divergence from origin), H-C2 open ceiling-caution(static 61/61, timed A/B unresolved, notional ~4.4% pending quiet host then fleet node), H-D/H-B/H-Z1/H-Y1 open). NEXT (unchanged, rank authority): operator lands/commits local residue + merges/syncs local branch onto advanced origin/main (incl. PR #819 fleet scripts quiet-host.cljs + remote-bench.cljs), then quiet-host A/B (H-Z3 top lever, else H-C2 ceiling-check) on idlest qualifying fleet node.\n"
)

new_text = text.replace(anchor, entry + anchor, 1)
with io.open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(new_text)

print("appended tick-314 entry, lines now:", new_text.count("\n"))