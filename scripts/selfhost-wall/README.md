# Selfhost wall harness

Measures how many sources reachable from the `nbb/*_cli.cljk` entries pass `amu check` on the
Kotoba project route (docs/selfhost-status-20260930.md). Keep this in the repo: it once lived only
in `/private/tmp` and was lost.

    scripts/selfhost-wall/make-classpath.py <amu-root> /tmp/cp.txt      # worktrees named wt-<L>-<repo>
    scripts/selfhost-wall/reach-list.py <amu-root> /tmp/cp.txt <kotoba-lang> > /tmp/list.txt
    WALL_CP=/tmp/cp.txt WALL_K=<kotoba-lang> scripts/selfhost-wall/scan.sh /tmp/list.txt /tmp/scan.tsv

Numbers from this harness are Kotoba-route checks, not bootstrap (JVM/GraalVM/nbb) measurements.
