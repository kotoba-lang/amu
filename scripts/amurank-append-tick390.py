import io
p = 'docs/codegen-coscientist.md'
s = io.open(p, encoding='utf-8').read()
entry = "\n2026-09-13 11:0x JST (amu-rank cron, tick 390): rank-only host-busy pass; load1 21.25 / 5m 18.38 / 15m 15.04 at 11:06 (uptime 8d, 6 users), far above the 7.5 gate — measurement refused. git fetch/review: origin/main 18ef21dd unchanged since tick 385; local HEAD b4dca066 (tick 389). Sibling in-flight edits (M docs/codegen-cosientist.md, M docs/codegen-coscientist.md, M docs/jit-cosientist.md, D scripts/quiet-host.cljk, untracked probe scripts) untouched; newest sibling entries are amu-bench busy-refusal ticks (2026-09-13 10:07, load1 13.08/34.17, no numbers) — no new measured evidence against any open hypothesis; no new ADR (0346 remains newest on disk). No re-rank, no status transition, no new hypothesis — no measured numbers exist. Population unchanged: H-Z3 quiet-host hand-patch A/B first (only measured above-bar effect, needs sustained idle>=9/10 or a qualifying fleet node), fallback H-C2; H-D, H-B, H-Y1, H-Z1 open. NEXT: H-Z3 quiet-host hand-patch A/B, fallback H-C2.\n"
tail_at = s.rfind('\n2026-09-13 05:0x JST (amu-rank cron, tick 389)')
assert tail_at > 0, 'tick 389 entry not found'
# insert after end of tick 389 paragraph
end = s.find('\n\n', tail_at)
if end == -1:
    end = len(s)
s2 = s[:end] + entry + s[end:]
io.open(p, 'w', encoding='utf-8').write(s2)
print('appended tick 390')
