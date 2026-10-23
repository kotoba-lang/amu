#!/usr/bin/env python3
"""Harness-side regime classification for the gpu-subgroup-reduce records
(JUN-58, the 2026-10-23 claim protocol, rule 1).

The protocol (docs/adr/0360-gpu-apple-subgroup-reduce.md, the regime-robust
magnitude claim protocol amendment; decision record
docs/evidence/gpu/regime-robust-protocol-20261023.txt) rule 1 says: every
measurement record publishes each run's baseline per-run median gpu-ns per
operator and the regime clusters its session observed -- the discrete clock
levels; the harness reads no GPU clock, so clusters are the observed
baseline-median levels, named by their gpu-ns ranges.

This module is that publication, mechanised. Until this file existed the
records classified manually in NOTES.md and rule 1's state was
UNIMPLEMENTED harness-side.

THE CLUSTERING RULE (named GAP-1.15):

  Per operator, take the per-run baseline median gpu-ns values, sort them
  ascending, and single-link them: the next value joins the current level
  when it is at most 1.15x the previous value, else it starts a new level.
  Levels are named by their gpu-ns ranges (lo..hi) and the runs that
  produced them. A level is ONE clock plateau as this harness can see it.

  1.15 is not a tuning knob picked to flatter any cell: it is the geometric
  midpoint of the separation window the committed records themselves
  establish between within-level drift and between-level steps:

    - within-level (manually decided): 1.075 -- the wsweep-low W = 32 :max
      cell's runs 4 and 6 (38958 and 36229 gpu-ns) are one "fast regime"
      in that record's prose (":max runs 4/6 0.958/1.017" named as
      fast-regime runs), and nothing manually placed in one level is
      further apart than that;
    - between-level (manually decided): 1.234 -- the shape-2 re-sweep
      W = 512 :min cell's run 3 (96125) is "dropped" away from the slow
      level (118646..119312) in that record's prose, and nothing manually
      placed in two levels is closer than that.

  sqrt(1.0753 * 1.2340) = 1.1519... -> 1.15. Gaps strictly between the two
  anchors were decided by NO prose in the corpus; GAP-1.15 decides them
  mechanically (merge at <= 1.15, split above) and the decision is
  visible in the published ranges. --self-test enumerates every such gap
  in the corpus and prints its verdict, so a new record that lands a gap
  in the window shows up in the output instead of hiding.

WHAT THIS MODULE DOES NOT DO (named so nothing is silently upgraded):

  - It reads no GPU clock. A "regime" here is a cluster of observed
    baseline-median levels, exactly as the protocol's rule 1 defines it.
  - Cross-operator level identity is NOT asserted. Classification is per
    operator; calling :sum's slow cluster and :min's slow cluster "the same
    clock level" is a prose inference this harness cannot verify.
  - Rule 2's sign classification (regime-invariant vs regime-scoped) is
    NOT here -- its own later slice, still UNIMPLEMENTED harness-side.
  - Pair-level classification (a run's clock can ramp mid-run; the
    op-order cell's analyze-oporder.py buckets individual pairs) is NOT
    here. This is run-level classification over baseline per-run medians,
    which is what rule 1 asks a record to publish.

CLI:

    python3 scripts/gpu_regime_classify.py <summary.md>
        print the rule-1 section for one measurement record
    python3 scripts/gpu_regime_classify.py --self-test
        unit fixtures + a regression pass over every committed summary.md
        under docs/evidence/ (pinned manual classifications must
        reproduce; cluster invariants must hold)

The measurement driver (scripts/gpu-subgroup-reduce-metal-measure.py)
imports render_section() and appends the section to every summary.md it
writes.
"""

import pathlib
import re
import sys

GAP_MAX = 1.15
ROOT = pathlib.Path(__file__).resolve().parent.parent

# The two manually-decided anchors the GAP_MAX window derives from
# (see the module docstring). Values are real committed per-run baseline
# medians, quoted so the derivation cannot silently drift: the window is
# the open interval between these two EXACT gap ratios, and GAP_MAX is its
# geometric midpoint rounded down to two decimals.
ANCHOR_WITHIN = 38958.0 / 36229.0    # wsweep-low-20261023/w32 :max runs 4 vs 6
ANCHOR_BETWEEN = 118646.0 / 96125.0  # shape2-resweep-20261023/w512 :min
                                     # run 3 vs the slow level


def level_clusters(medians, gap_max=GAP_MAX):
    """Cluster per-run baseline median gpu-ns into clock levels.

    medians: {run_index (1-based int): baseline per-run median gpu-ns}
    Returns levels sorted fastest-first:
      [{"lo": float, "hi": float, "runs": [int, ...],
        "medians": {run: float, ...}}, ...]

    Single-linkage over the sorted values: the next value joins the
    current level iff value / previous_value <= gap_max.
    """
    if not medians:
        raise ValueError("no per-run baseline medians to classify")
    ordered = sorted(medians.items(), key=lambda kv: (kv[1], kv[0]))
    levels = []
    prev_val = None
    for run, val in ordered:
        if prev_val is None or val / prev_val > gap_max:
            levels.append({"lo": val, "hi": val, "runs": [run],
                           "medians": {run: val}})
        else:
            lv = levels[-1]
            lv["hi"] = val
            lv["runs"].append(run)
            lv["medians"][run] = val
        prev_val = val
    for lv in levels:
        lv["runs"].sort()
    return levels


def parse_summary_per_run_baseline(text):
    """Parse the per-run baseline medians out of a driver summary.md.

    Returns {operator: {run_index: median}}. Run indices are positional
    (the summary's per-run medians column lists runs in order). Raises
    ValueError on a summary with no baseline rows.
    """
    out = {}
    for line in text.splitlines():
        m = re.match(r"\| (\w+) \| baseline \| (\d+) \| ([\d.]+) \| ([\d., ]+) \|",
                     line)
        if m:
            op, _n, _med, pr = m.groups()
            vals = [float(x) for x in pr.split(",") if x.strip()]
            out[op] = {ri + 1: v for ri, v in enumerate(vals)}
    if not out:
        raise ValueError("no '| op | baseline | ...' rows with per-run "
                         "medians found in summary")
    return out


def render_section(per_op, gap_max=GAP_MAX):
    """The claim-protocol rule-1 section for a measurement record.

    per_op: {operator: {run_index: baseline per-run median gpu-ns}}
    Returns markdown (no trailing newline).
    """
    lines = []
    lines.append("## Regime classification (claim protocol rule 1)")
    lines.append("")
    lines.append("Published by scripts/gpu_regime_classify.py (GAP-1.15). "
                 "The harness reads no GPU clock: a regime here is a "
                 "cluster of the observed baseline per-run median gpu-ns "
                 "levels, named by its gpu-ns range, per operator. "
                 "Cross-operator level identity is NOT asserted. Rule 2's "
                 "sign classification is not implemented harness-side.")
    lines.append("")
    lines.append("Clustering rule GAP-1.15: per operator, the per-run "
                 "baseline medians sorted ascending, single-linkage -- the "
                 "next median joins the current level at <= 1.15x the "
                 "previous, else it starts a new level. 1.15 is the "
                 "geometric midpoint of the committed records' decided "
                 "separation window [1.075, 1.234] (within-level drift vs "
                 "between-level step; see "
                 "docs/evidence/gpu/regime-classification-20261023.txt).")
    lines.append("")
    lines.append("| operator | level | gpu-ns range | runs (baseline per-run median) |")
    lines.append("|---|---|---|---|")
    for op in sorted(per_op):
        levels = level_clusters(per_op[op], gap_max)
        n = len(levels)
        for i, lv in enumerate(levels, start=1):
            if n == 1:
                tag = f"{i} (the only observed level)"
            elif i == 1:
                tag = f"{i} (fastest observed)"
            elif i == n:
                tag = f"{i} (slowest observed)"
            else:
                tag = str(i)
            rng = (f"{lv['lo']:.0f}" if lv["lo"] == lv["hi"]
                   else f"{lv['lo']:.0f}..{lv['hi']:.0f}")
            members = ", ".join(f"{r} ({lv['medians'][r]:.0f})"
                                for r in lv["runs"])
            lines.append(f"| {op} | {tag} | {rng} | {members} |")
    return "\n".join(lines)


# ---------------------------------------------------------------- tests

def _expect(cond, msg, stats):
    if not cond:
        raise AssertionError(msg)
    stats["passed"] += 1


def _self_test_unit(stats):
    # empty input refuses
    try:
        level_clusters({})
        raise AssertionError("empty medians must raise")
    except ValueError:
        stats["passed"] += 1

    # one value -> one level
    lv = level_clusters({1: 1000.0})
    _expect(len(lv) == 1 and lv[0]["runs"] == [1], "single value", stats)

    # tight cluster -> one level
    lv = level_clusters({1: 1000.0, 2: 1004.0, 3: 997.0})
    _expect(len(lv) == 1 and lv[0]["runs"] == [1, 2, 3], "tight cluster", stats)

    # boundary: exactly gap_max merges (<= rule)
    lv = level_clusters({1: 1000.0, 2: 1150.0})
    _expect(len(lv) == 1, "gap exactly 1.15 merges", stats)

    # boundary: just over gap_max splits
    lv = level_clusters({1: 1000.0, 2: 1150.1})
    _expect(len(lv) == 2 and lv[0]["runs"] == [1] and lv[1]["runs"] == [2],
            "gap 1.1501 splits", stats)

    # single-linkage chaining is real (documented behavior)
    lv = level_clusters({1: 100.0, 2: 114.0, 3: 130.0})
    _expect(len(lv) == 1, "chaining merges 100/114/130", stats)

    # run indices are carried through and sorted within their level
    # (sorted by value: 5->100, 9->105 merge; 2->200 starts a new level)
    lv = level_clusters({5: 100.0, 2: 200.0, 9: 105.0})
    _expect(len(lv) == 2 and lv[0]["runs"] == [5, 9] and lv[1]["runs"] == [2],
            "runs sorted, indices preserved", stats)

    # anchor fixtures (real committed numbers): shape2-resweep w512
    w512 = {
        "sum": {1: 119312.0, 2: 118833.0, 3: 61917.0, 4: 119062.0,
                5: 119062.0, 6: 119292.0},
        "max": {1: 119166.0, 2: 119208.0, 3: 72542.0, 4: 119188.0,
                5: 119438.0, 6: 119500.0},
        "min": {1: 118646.0, 2: 118896.0, 3: 96125.0, 4: 119312.0,
                5: 118875.0, 6: 119146.0},
    }
    for op, med in w512.items():
        lv = level_clusters(med)
        _expect(len(lv) == 2 and lv[0]["runs"] == [3]
                and lv[1]["runs"] == [1, 2, 4, 5, 6],
                f"w512 shape2-resweep {op}: run 3 dropped, runs 1,2,4,5,6 "
                "one slow level (the NOTES' manual classification)", stats)

    # anchor fixture: shape2 w32 :max -- the prose-named three levels
    w32max = level_clusters({1: 114084.0, 2: 113875.0, 3: 48042.0,
                             4: 37812.0, 5: 112916.0, 6: 113834.0})
    _expect([lv["runs"] for lv in w32max] == [[4], [3], [1, 2, 5, 6]],
            "w32 shape2 :max: fast ~37.5k (run 4), middle ~48k (run 3), "
            "slow ~113k (runs 1,2,5,6) -- the NOTES' manual naming", stats)

    # anchor fixture: shape2 w32 :sum -- all six runs one level
    w32sum = level_clusters({1: 113666.0, 2: 113667.0, 3: 113750.0,
                             4: 114104.0, 5: 113312.0, 6: 113792.0})
    _expect(len(w32sum) == 1 and w32sum[0]["runs"] == [1, 2, 3, 4, 5, 6],
            "w32 shape2 :sum: all six runs the slow level (the NOTES' "
            "'all six :sum runs sat at the slow level')", stats)

    # anchor fixture: wsweep-low w32 :max -- runs 4 and 6 one fast regime
    w32lo = level_clusters({1: 109479.0, 2: 107771.0, 3: 109562.0,
                            4: 38958.0, 5: 108875.0, 6: 36229.0})
    _expect(len(w32lo) == 2 and w32lo[0]["runs"] == [4, 6]
            and w32lo[1]["runs"] == [1, 2, 3, 5],
            "wsweep-low w32 :max: runs 4 and 6 one fast regime (the "
            "NOTES' ':max runs 4/6' fast-regime grouping)", stats)


def _self_test_corpus(stats, corpus_root):
    summaries = sorted(corpus_root.rglob("summary.md"))
    parsed = []
    for s in summaries:
        text = s.read_text()
        try:
            parsed.append((s, parse_summary_per_run_baseline(text)))
        except ValueError:
            continue  # a record without per-run baseline rows: not this corpus
    _expect(len(parsed) >= 20, f"corpus size {len(parsed)} (>= 20)",
            stats)

    gaps_in_window = []
    for s, per_op in parsed:
        for op, med in sorted(per_op.items()):
            runs = set(med)
            _expect(runs == set(range(1, len(med) + 1)),
                    f"{s}:{op}: runs are exactly 1..{len(med)}", stats)
            lv = level_clusters(med)
            _expect(sorted(r for l in lv for r in l["runs"]) == sorted(med),
                    f"{s}:{op}: every run classified exactly once", stats)
            ordered = sorted(med.values())
            for a, b in zip(ordered, ordered[1:]):
                gap = b / a
                if ANCHOR_WITHIN < gap < ANCHOR_BETWEEN:
                    gaps_in_window.append((str(s.relative_to(corpus_root)),
                                           op, a, b, gap))
            # invariant: within-level gaps <= GAP_MAX, between-level > GAP_MAX
            for l in lv:
                vals = sorted(l["medians"].values())
                for a, b in zip(vals, vals[1:]):
                    _expect(b / a <= GAP_MAX,
                            f"{s}:{op}: within-level gap {b / a:.3f} <= "
                            f"{GAP_MAX}", stats)
            for l1, l2 in zip(lv, lv[1:]):
                _expect(l2["lo"] / l1["hi"] > GAP_MAX,
                        f"{s}:{op}: between-level gap "
                        f"{l2['lo'] / l1['hi']:.3f} > {GAP_MAX}", stats)

    # the pinned manual classifications, over the parsed corpus (not
    # fixtures): they must reproduce from the committed summary.md text
    want = {
        "gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w512": {
            "sum": [[3], [1, 2, 4, 5, 6]],
            "max": [[3], [1, 2, 4, 5, 6]],
            "min": [[3], [1, 2, 4, 5, 6]],
        },
        "gpu-subgroup-reduce-m1max-shape2-20261023/w32": {
            "max": [[4], [3], [1, 2, 5, 6]],
        },
    }
    for s, per_op in parsed:
        rel = str(s.relative_to(corpus_root)).replace("/summary.md", "")
        if rel in want:
            for op, expect in want[rel].items():
                got = [l["runs"] for l in level_clusters(per_op[op])]
                _expect(got == expect,
                        f"{rel}:{op}: pinned manual classification "
                        f"{expect}, got {got}", stats)

    print(f"corpus: {len(parsed)} committed summaries classified under "
          f"GAP-1.15")
    print(f"gaps strictly between the two decided anchors "
          f"({ANCHOR_WITHIN:.4f} within-level, {ANCHOR_BETWEEN:.4f} "
          f"between-level) -- decided by GAP-1.15 alone, named not hidden:")
    for rel, op, a, b, gap in gaps_in_window:
        verdict = "merge" if gap <= GAP_MAX else "split"
        print(f"  {rel} {op}: {a:.0f} -> {b:.0f}  gap {gap:.3f}  -> {verdict}")
    if not gaps_in_window:
        print("  (none)")


def main():
    args = sys.argv[1:]
    if args == ["--self-test"]:
        stats = {"passed": 0}
        _self_test_unit(stats)
        print(f"unit fixtures: {stats['passed']} assertions passed")
        _self_test_corpus(stats, ROOT / "docs" / "evidence")
        print(f"TOTAL: {stats['passed']} assertions passed, 0 failed")
        return
    if len(args) != 1:
        doc = __doc__ or ""
        sys.stderr.write(doc.split("CLI:")[1] if "CLI:" in doc else doc)
        sys.exit(2)
    per_op = parse_summary_per_run_baseline(pathlib.Path(args[0]).read_text())
    print(render_section(per_op))


if __name__ == "__main__":
    main()
