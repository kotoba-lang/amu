import io

path = "docs/codegen-coscientist.md"
with io.open(path, "r", encoding="utf-8") as f:
    text = f.read()

anchor = "## Standing honesty constraints"
assert anchor in text, "anchor missing"
assert text.count(anchor) == 1, "anchor not unique"

entry = (
"2026-09-09 00:15 JST (amu-rank cron, tick 315): host busy(pre-run monitor load1 104.99 / load5 76.03 / load15 66.72, up 3d 16:56, 6 users, threshold 7.5; live probe uptime 00:15: load1 116.98 / load5 93.05 / load15 74.87) - measurement refused, rank-only busy pass. git fetch clean(no new origin commits since tick-312 read; origin/main UNCHANGED at  26401d2f = Merge PR #900 'the compiler gets a ClojureScript test runner'; upstream test/infra, origin-namespace, NOT local-reconcilable; local branch spike/kbb-jvmfree-envread still diverged/behind origin, merge/reconcile left for the operator). local HEAD 44094324 = tick-314 busy+fold commit. guard-glob residue 150 untracked lines local-uncommitted (`git status --porcelain -- src bench scripts deps.edn` = 150, unchanged from tick 314; regime unchanged: append/probe scripts under docs/ + scripts/ + build-time-os sidecars + ADR 0339 untracked). Folded 2 uncommitted sibling busy-refusals landed since tick-314 commit(amu-falsify 2026-09-08 23:50 JST H-B evidence cell: host load1 159.43 / load5 123.90 / load15 89.00, up 3d 16:33,  ​6 users, threshold  ​7.5, quiet-gate refusal, no measurement, no numbers, NEXT H-C2 unchanged; amu-bench tick 2026-09-08 23:53 JST 'Standing honesty constraints' block: host load1 86.74 / load5 112.99 / load15 90.93, up 3d 16:36,  ​6 users, macOS  ​26.4 arm64, quiet-gate refusal, no bench/perfgate/hand-patch number recorded, NEXT H-C2 ceiling-check unchanged) - busy refusals, NOT a new local measured verdict(folding evidence, no status edit.). Pre-run monitor NEXT read \"H-Y1 remain open. NEXT: H-C2\" is STALE(unchanged from ticks296-311, H-C2 not rank-authority since iter-56; authoritative NEXT is the committed tick rank line below.). No new local codegen ADR since tick-314 read(0345 remains latest registered, first QUALIFIED imod lever verdicts on benjamin at quiet gate; perfgate.core/qualify for kotoba-native imod inlining NOT yet issued; ADR 0339 remains UNTRACKED/residue locally.). No new LOCAL measured verdict -> no re-rank,no status transition,no new hypothesis;; population unchanged(post-284: H-Z4 registered open(port ADR-0345 imod helper-call inlining to kotoba-native_, expected separated >=5%), H-Z3 top of codegen ladder(quiet-host A/B still blocked by guard-glob residue + repo divergence from origin_, H-C2 open ceiling-caution(static  61/61_, timed A/B unresolved_, notional  ~4.4% pending quiet host then fleet node_, H-D/H-B/H-Z1/H-Y1 open. NEXT(unchanged_, rank authority): operator merges origin/main + quiet-host A/B(H-Z3 top lever_, else H-C2 ceiling-check)on qualifying fleet node. Appended via python script file.\n"
)

## ensure trailing line is a \\n so the replace lands clean
entry += "\n"

new_text = text.replace(anchor, entry + anchor, 1)
with io.open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(new_text)

print("appended tick-315 entry, lines now:", new_text.count("\n"))