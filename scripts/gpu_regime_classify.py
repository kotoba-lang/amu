#!/usr/bin/env python3
"""Harness-side regime classification for the gpu-subgroup-reduce records
(JUN-58, the 2026-10-23 claim protocol, rules 1 and 2).

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
    clock level" is a prose inference this harness cannot verify. The
    rule-2 cell row is therefore only an admissibility roll-up over
    pooled per-run ratios -- it carries no cross-operator regime structure.
  - Rule 3's regime-matched comparison machinery is NOT here -- its own
    later slice, still UNIMPLEMENTED harness-side. (Rule 2's sign
    classification IS here as of the 2026-10-23 rule-2 slice:
    sign_classification(), and the "Sign classification (claim protocol
    rule 2)" section render_sign_section() publishes.)
  - Pair-level classification (a run's clock can ramp mid-run; the
    op-order cell's analyze-oporder.py buckets individual pairs) is NOT
    here. This is run-level classification over baseline per-run medians,
    which is what rule 1 asks a record to publish.

RULE 2 (sign classification), mechanised:

  Rule 2 of the protocol: a sign is REGIME-INVARIANT when every per-run
  ratio of every observed regime lies on the same side of 1.0 -- only
  such a sign may be a selection basis. A sign that follows the regime
  (the W = 32 straddle) is published REGIME-SCOPED and cannot choose a
  variant. This module classifies exactly that dichotomy, mechanically:

    - regime-invariant: every per-run ratio is strictly above 1.0
      ("slower", variant/baseline) or every one is strictly below
      ("faster");
    - anything else is regime-scoped. The published detail names the
      straddle's shape instead of hiding it: "by-regime" (every regime
      one-sided, regimes disagree -- sign follows the regime, the W = 32
      pattern), "within-regime" (one regime holds both sides -- the
      wsweep-low W = 32 :max cell, whose fast regime runs 4/6 are
      0.958/1.017), or "no-side" (every ratio exactly 1.0: no sign
      exists to claim). The prose of rule 2 decided only the invariant /
      scoped split; the straddle shape is this module's mechanical
      extension, published for visibility and it never upgrades
      admissibility -- a regime-scoped sign cannot choose a variant
      whatever its shape.

CLI:

    python3 scripts/gpu_regime_classify.py <summary.md>
        print the claim-protocol sections (rule 1; rule 2 when the
        record carries per-run ratios) for one measurement record
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


def parse_summary_per_run_ratios(text):
    """Parse the per-run paired ratios out of a driver summary.md.

    Returns {operator: [ratio, ...]} in run order (run indices positional,
    matching parse_summary_per_run_baseline). Raises ValueError on a
    summary with no per-run ratio rows.
    """
    out = {}
    for line in text.splitlines():
        m = re.match(r"\| (\w+) \| ([\d.]+(?:, [\d.]+)+) \| ([\d.]+) \|",
                     line)
        if m:
            op, pr, _med = m.groups()
            out[op] = [float(x) for x in pr.split(",") if x.strip()]
    if not out:
        raise ValueError("no '| op | per-run ratios | median ratio |' rows "
                         "found in summary")
    return out


def _level_tag(i, n):
    if n == 1:
        return f"{i} (the only observed level)"
    if i == 1:
        return f"{i} (fastest observed)"
    if i == n:
        return f"{i} (slowest observed)"
    return str(i)


def _level_name(i, n):
    if n == 1:
        return "the only observed level"
    if i == 1:
        return "fastest observed"
    if i == n:
        return "slowest observed"
    return "middle level"


def ratio_side(ratio):
    """Which side of 1.0 a per-run ratio (variant/baseline) sits on.

    'slower' = above 1.0 (the variant is slower than the baseline),
    'faster' = below 1.0, 'even' = exactly 1.0 (on neither side).
    """
    if ratio > 1.0:
        return "slower"
    if ratio < 1.0:
        return "faster"
    return "even"


def sign_classification(ratios, levels):
    """Claim-protocol rule 2 sign classification, mechanically.

    ratios: {run_index (1-based int): per-run paired ratio (variant/baseline)}
    levels: the rule-1 regime clusters for the SAME runs (as returned by
            level_clusters over that operator's baseline medians).

    Returns {
      "verdict": "regime-invariant" | "regime-scoped",
      "side": "slower" | "faster" | None,       (set iff regime-invariant)
      "counts": {"slower": n, "faster": n, "even": n},
      "straddle": None | "by-regime" | "within-regime" | "no-side",
      "level_sides": [{"level": i, "runs": [(run, ratio, side), ...],
                       "sides": set}, ...]      (fastest level first)
    }

    regime-invariant, exactly the protocol's words: every per-run ratio of
    every observed regime lies on the same side of 1.0. Anything else is
    regime-scoped (and cannot be a selection basis). The straddle shape is
    published but never changes the verdict:
      by-regime    -- every regime is one-sided and regimes disagree
                      (sign follows the regime; the W = 32 pattern);
      within-regime -- some single regime holds both sides
                      (the wsweep-low W = 32 :max cell, fast-regime runs
                      4/6 at 0.958/1.017);
      no-side      -- every ratio is exactly 1.0: no sign exists to claim.
    """
    if not ratios:
        raise ValueError("no per-run ratios to classify")
    lv_runs = [r for l in levels for r in l["runs"]]
    if set(lv_runs) != set(ratios):
        raise ValueError("ratio runs and regime-level runs disagree: "
                         f"ratios {sorted(ratios)}, levels {sorted(lv_runs)}")
    sides = {run: ratio_side(r) for run, r in ratios.items()}
    counts = {"slower": 0, "faster": 0, "even": 0}
    for s in sides.values():
        counts[s] += 1
    side_set = set(sides.values())
    level_sides = []
    for i, lv in enumerate(levels, start=1):
        runs = [(r, ratios[r], sides[r]) for r in lv["runs"]]
        level_sides.append({"level": i, "runs": runs,
                            "sides": {s for _, _, s in runs}})
    if side_set <= {"slower"}:
        return {"verdict": "regime-invariant", "side": "slower",
                "counts": counts, "straddle": None,
                "level_sides": level_sides}
    if side_set <= {"faster"}:
        return {"verdict": "regime-invariant", "side": "faster",
                "counts": counts, "straddle": None,
                "level_sides": level_sides}
    if side_set == {"even"}:
        straddle = "no-side"
    elif all(len(ls["sides"]) == 1 for ls in level_sides) \
            and len({next(iter(ls["sides"])) for ls in level_sides}) > 1:
        straddle = "by-regime"
    else:
        straddle = "within-regime"
    return {"verdict": "regime-scoped", "side": None,
            "counts": counts, "straddle": straddle,
            "level_sides": level_sides}


def cell_sign_classification(per_op_ratios, per_op_medians, gap_max=GAP_MAX):
    """Rule 2 at cell level: the admissibility roll-up over pooled ratios.

    per_op_ratios: {operator: {run: ratio}} (same run indices as medians)
    per_op_medians: {operator: {run: baseline median}} (for the rule-1
                    levels each sign classification is scoped to)

    The cell is regime-invariant only when EVERY operator is
    regime-invariant on the SAME side -- the "18/18 slower" shape. Because
    cross-operator level identity is NOT asserted, this roll-up carries no
    cross-operator regime structure: the straddle shape is reported per
    operator only.
    """
    per_op = {}
    for op in sorted(per_op_ratios):
        per_op[op] = sign_classification(per_op_ratios[op],
                                         level_clusters(per_op_medians[op],
                                                        gap_max))
    sides = {c["side"] for c in per_op.values()
             if c["verdict"] == "regime-invariant"}
    all_inv = all(c["verdict"] == "regime-invariant" for c in per_op.values())
    counts = {"slower": 0, "faster": 0, "even": 0}
    for c in per_op.values():
        for k in counts:
            counts[k] += c["counts"][k]
    if all_inv and len(sides) == 1:
        return {"verdict": "regime-invariant", "side": sides.pop(),
                "counts": counts, "per_op": per_op}
    return {"verdict": "regime-scoped", "side": None,
            "counts": counts, "per_op": per_op}


def _side_phrase(side, n):
    if side == "slower":
        return f"all {n} per-run ratios above 1.0 ({n}/{n} slower)"
    if side == "faster":
        return f"all {n} per-run ratios below 1.0 ({n}/{n} faster)"
    return f"all {n} per-run ratios at 1.0"


def render_sign_section(per_op, ratios, gap_max=GAP_MAX):
    """The claim-protocol rule-2 section for a measurement record.

    per_op: {operator: {run_index: baseline per-run median gpu-ns}}
    ratios: {operator: [per-run ratio, ...]} in run order
    Returns markdown (no trailing newline).
    """
    per_op_ratios = {op: {ri + 1: v for ri, v in enumerate(rs)}
                     for op, rs in ratios.items()}
    per_op_med = {op: dict(m) for op, m in per_op.items()}
    cell = cell_sign_classification(per_op_ratios, per_op_med, gap_max)
    lines = []
    lines.append("## Sign classification (claim protocol rule 2)")
    lines.append("")
    lines.append("Published by scripts/gpu_regime_classify.py from the "
                 "per-run paired ratios above and the rule-1 regime "
                 "clusters. Rule 2: a sign is REGIME-INVARIANT when every "
                 "per-run ratio of every observed regime lies on the same "
                 "side of 1.0 -- only such a sign may be a selection "
                 "basis. Any other cell is published REGIME-SCOPED and "
                 "cannot choose a variant. The harness reads no clock: a "
                 "regime is the rule-1 cluster. Cross-operator level "
                 "identity is NOT asserted, so the cell row carries only "
                 "the admissibility roll-up, no cross-operator regime "
                 "structure.")
    lines.append("")
    lines.append("| operator | verdict | side | detail |")
    lines.append("|---|---|---|---|")
    for op in sorted(cell["per_op"]):
        c = cell["per_op"][op]
        n = sum(c["counts"].values())
        if c["verdict"] == "regime-invariant":
            detail = _side_phrase(c["side"], n) + \
                "; every observed regime one-sided"
            side = c["side"]
        elif c["straddle"] == "no-side":
            detail = "every ratio is exactly 1.0 -- no sign exists to claim"
            side = "none"
        else:
            nlevels = len(c["level_sides"])
            segs = "; ".join(
                f"level {ls['level']} ({_level_name(ls['level'], nlevels)}): "
                + ", ".join(f"run {r} {v:.3f} "
                            f"{'above' if s == 'slower' else 'below' if s == 'faster' else 'at'} 1.0"
                            for r, v, s in ls["runs"])
                for ls in c["level_sides"])
            if c["straddle"] == "by-regime":
                detail = ("straddle separates by regime (every regime "
                          "one-sided, regimes disagree): " + segs)
            else:
                mixed = [str(ls["level"]) for ls in c["level_sides"]
                         if len(ls["sides"]) > 1]
                detail = (f"straddle within regime {', '.join(mixed)} "
                          f"(one regime holds both sides): " + segs)
            side = "straddles 1.0"
        lines.append(f"| {op} | {c['verdict']} | {side} | {detail} |")
    n = sum(cell["counts"].values())
    pooled = (f"{cell['counts']['slower']} above 1.0, "
              f"{cell['counts']['faster']} below 1.0"
              + (f", {cell['counts']['even']} at 1.0"
                 if cell["counts"]["even"] else ""))
    if cell["verdict"] == "regime-invariant":
        cell_line = (f"Cell (all {n} per-run ratios pooled): "
                     f"**regime-invariant**, {cell['side']} "
                     f"({n}/{n} {cell['side']}).")
    else:
        bad = sorted(op for op, c in cell["per_op"].items()
                     if c["verdict"] != "regime-invariant")
        cell_line = (f"Cell (all {n} per-run ratios pooled): "
                     f"**regime-scoped** ({pooled}) -- not a selection "
                     f"basis; non-invariant operators: "
                     f"{', '.join(bad)}.")
    lines.append("")
    lines.append(cell_line)
    return "\n".join(lines)


def render_section(per_op, gap_max=GAP_MAX, ratios=None):
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
                 "sign classification is published in its own section "
                 "below when the record's per-run ratios are provided.")
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
            tag = _level_tag(i, n)
            rng = (f"{lv['lo']:.0f}" if lv["lo"] == lv["hi"]
                   else f"{lv['lo']:.0f}..{lv['hi']:.0f}")
            members = ", ".join(f"{r} ({lv['medians'][r]:.0f})"
                                for r in lv["runs"])
            lines.append(f"| {op} | {tag} | {rng} | {members} |")
    if ratios is not None:
        lines.append("")
        lines.append(render_sign_section(per_op, ratios, gap_max))
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

    # ---- rule 2: sign classification ----

    # empty ratios refuse
    try:
        sign_classification({}, level_clusters({1: 100.0}))
        raise AssertionError("empty ratios must raise")
    except ValueError:
        stats["passed"] += 1

    # ratio runs and regime-level runs must agree
    try:
        sign_classification({1: 1.2}, level_clusters({1: 100.0, 2: 200.0}))
        raise AssertionError("run-set mismatch must raise")
    except ValueError:
        stats["passed"] += 1

    # all above 1.0 -> regime-invariant slower (the flip-set 18/18 shape)
    c = sign_classification({1: 1.2, 2: 1.3, 3: 1.1},
                            level_clusters({1: 100.0, 2: 200.0, 3: 300.0}))
    _expect(c["verdict"] == "regime-invariant" and c["side"] == "slower"
            and c["straddle"] is None,
            "all above 1.0 is regime-invariant slower", stats)

    # all below 1.0 -> regime-invariant faster (wsweep-low w32 :sum shape)
    c = sign_classification({1: 0.917, 2: 0.918, 3: 0.916},
                            level_clusters({1: 100.0, 2: 101.0, 3: 99.0}))
    _expect(c["verdict"] == "regime-invariant" and c["side"] == "faster",
            "all below 1.0 is regime-invariant faster", stats)

    # a ratio at exactly 1.0 sits on NEITHER side (rule 2: "the same side
    # of 1.0") -> invariance is blocked
    c = sign_classification({1: 1.0, 2: 1.2},
                            level_clusters({1: 100.0, 2: 100.0}))
    _expect(c["verdict"] == "regime-scoped"
            and c["straddle"] == "within-regime",
            "a ratio at 1.0 blocks invariance", stats)

    # every ratio at 1.0 -> no sign exists to claim
    c = sign_classification({1: 1.0, 2: 1.0},
                            level_clusters({1: 100.0, 2: 105.0}))
    _expect(c["verdict"] == "regime-scoped" and c["straddle"] == "no-side",
            "all ratios at 1.0 is no-side, not a sign", stats)

    # the W = 32 by-regime straddle, real committed numbers (shape2 w32
    # :max: run 4 alone in the fastest level at 1.026 above 1.0, run 3's
    # middle level and the slow level below) -- sign follows the regime
    c = sign_classification(
        {1: 0.916, 2: 0.918, 3: 0.928, 4: 1.026, 5: 0.925, 6: 0.917},
        level_clusters({1: 114084.0, 2: 113875.0, 3: 48042.0,
                        4: 37812.0, 5: 112916.0, 6: 113834.0}))
    _expect(c["verdict"] == "regime-scoped" and c["straddle"] == "by-regime",
            "shape2 w32 :max: sign separates by regime (run 4's fastest "
            "level alone above 1.0)", stats)

    # the within-regime straddle, real committed numbers (wsweep-low w32
    # :max: the fast regime's own runs 4/6 at 0.958/1.017 -- both sides
    # inside ONE regime)
    c = sign_classification(
        {1: 0.916, 2: 0.924, 3: 0.916, 4: 0.958, 5: 0.922, 6: 1.017},
        level_clusters({1: 109479.0, 2: 107771.0, 3: 109562.0,
                        4: 38958.0, 5: 108875.0, 6: 36229.0}))
    _expect(c["verdict"] == "regime-scoped"
            and c["straddle"] == "within-regime",
            "wsweep-low w32 :max: the fast regime itself straddles "
            "(runs 4/6 at 0.958/1.017) -- within-regime", stats)

    # a straddle inside the only observed regime is within-regime
    c = sign_classification({1: 0.95, 2: 1.05},
                            level_clusters({1: 100.0, 2: 101.0}))
    _expect(c["straddle"] == "within-regime",
            "straddle inside the only regime is within-regime", stats)

    # cell roll-up: every operator invariant on the same side -> the cell
    # is invariant (the "18/18 slower" shape)
    cell = cell_sign_classification(
        {"sum": {1: 1.2, 2: 1.2}, "max": {1: 1.3, 2: 1.3}},
        {"sum": {1: 100.0, 2: 101.0}, "max": {1: 100.0, 2: 105.0}})
    _expect(cell["verdict"] == "regime-invariant" and cell["side"] == "slower"
            and cell["counts"] == {"slower": 4, "faster": 0, "even": 0},
            "cell roll-up: every operator invariant on one side", stats)

    # cell roll-up: one regime-scoped operator blocks the cell
    cell = cell_sign_classification(
        {"sum": {1: 1.2, 2: 1.2}, "max": {1: 0.9, 2: 1.1}},
        {"sum": {1: 100.0, 2: 101.0}, "max": {1: 100.0, 2: 200.0}})
    _expect(cell["verdict"] == "regime-scoped",
            "cell roll-up: one regime-scoped operator blocks the cell",
            stats)

    # cell roll-up: operators invariant on OPPOSITE sides pool to a
    # straddle (the pooled ratios are not one-sided)
    cell = cell_sign_classification(
        {"sum": {1: 0.9, 2: 0.9}, "max": {1: 1.1, 2: 1.1}},
        {"sum": {1: 100.0, 2: 101.0}, "max": {1: 100.0, 2: 101.0}})
    _expect(cell["verdict"] == "regime-scoped",
            "cell roll-up: opposite invariant sides pool to a straddle",
            stats)

    # the driver's call shape: render_section with ratios carries both
    # sections and the rule-2 cell line
    out = render_section({"sum": {1: 100.0, 2: 101.0}},
                         ratios={"sum": [1.2, 1.2]})
    _expect("## Regime classification (claim protocol rule 1)" in out
            and "## Sign classification (claim protocol rule 2)" in out
            and "2/2 slower" in out,
            "render_section with ratios publishes both protocol sections",
            stats)

    # and without ratios the rule-1 section is unchanged (no rule-2 block)
    out = render_section({"sum": {1: 100.0, 2: 101.0}})
    _expect("## Sign classification" not in out
            and "published in its own section below" in out,
            "render_section without ratios stays rule-1-only", stats)


def _self_test_corpus(stats, corpus_root):
    summaries = sorted(corpus_root.rglob("summary.md"))
    parsed = []
    for s in summaries:
        text = s.read_text()
        try:
            per_op = parse_summary_per_run_baseline(text)
        except ValueError:
            continue  # a record without per-run baseline rows: not this corpus
        try:
            per_rat = parse_summary_per_run_ratios(text)
        except ValueError:
            per_rat = None  # a record without per-run ratio rows: rule 1 only
        parsed.append((s, per_op, per_rat))
    _expect(len(parsed) >= 20, f"corpus size {len(parsed)} (>= 20)",
            stats)

    gaps_in_window = []
    for s, per_op, _per_rat in parsed:
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
    for s, per_op, _per_rat in parsed:
        rel = str(s.relative_to(corpus_root)).replace("/summary.md", "")
        if rel in want:
            for op, expect in want[rel].items():
                got = [l["runs"] for l in level_clusters(per_op[op])]
                _expect(got == expect,
                        f"{rel}:{op}: pinned manual classification "
                        f"{expect}, got {got}", stats)

    # ---- rule 2 over the corpus: sign classification ----
    sign_cells = 0
    tally = {"regime-invariant slower": 0, "regime-invariant faster": 0,
             "by-regime": 0, "within-regime": 0, "no-side": 0}
    # pinned sign classifications over the parsed corpus (not fixtures).
    # Provenance of each pin:
    #   wsweep-low w32 :max -- that record's own prose ":max runs 4/6
    #     0.958/1.017" names the fast-regime runs and both sides live in
    #     that one regime (within-regime);
    #   shape2 w32 :max/:min -- accelerator_variants' prose "fast-level
    #     :max 1.026 and :min 1.021-1.026 against slow-level ~0.92": the
    #     sign follows the regime (by-regime);
    #   shape2-resweep w512 all ops -- the re-sweep's "reproduces in sign
    #     strictly" cells, 18/18 slower (regime-invariant);
    #   wsweep-low w32 :sum/:min -- mechanically from the committed
    #     summary numbers; NO prose decided wsweep-low :min's three-level
    #     split (GAP-1.15's verdict), so the pin says only what the
    #     numbers say.
    pinned_sign = {
        "gpu-subgroup-reduce-m1max-wsweep-low-20261023/w32": {
            "sum": ("regime-invariant", "faster", None),
            "max": ("regime-scoped", None, "within-regime"),
            "min": ("regime-scoped", None, "by-regime"),
        },
        "gpu-subgroup-reduce-m1max-shape2-20261023/w32": {
            "sum": ("regime-invariant", "faster", None),
            "max": ("regime-scoped", None, "by-regime"),
            "min": ("regime-scoped", None, "by-regime"),
        },
        "gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w512": {
            "sum": ("regime-invariant", "slower", None),
            "max": ("regime-invariant", "slower", None),
            "min": ("regime-invariant", "slower", None),
        },
    }
    for s, per_op, per_rat in parsed:
        if not per_rat:
            continue
        rel = str(s.relative_to(corpus_root)).replace("/summary.md", "")
        for op, rs in sorted(per_rat.items()):
            _expect(op in per_op,
                    f"{rel}:{op}: ratio rows have baseline rows", stats)
            ratios = {ri + 1: v for ri, v in enumerate(rs)}
            _expect(set(ratios) == set(per_op[op]),
                    f"{rel}:{op}: ratio runs == baseline-median runs", stats)
            c = sign_classification(ratios, level_clusters(per_op[op]))
            sign_cells += 1
            # independent recomputation of rule 2's condition, not
            # reusing the classifier's own verdict
            sides = {ratio_side(r) for r in ratios.values()}
            want_inv = sides <= {"slower"} or sides <= {"faster"}
            _expect((c["verdict"] == "regime-invariant") == want_inv,
                    f"{rel}:{op}: verdict matches an independent "
                    f"recomputation of rule 2's condition", stats)
            if c["verdict"] == "regime-invariant":
                tally[f"regime-invariant {c['side']}"] += 1
            else:
                tally[c["straddle"]] += 1
                if c["straddle"] == "by-regime":
                    _expect(all(len(ls["sides"]) == 1
                                for ls in c["level_sides"]),
                            f"{rel}:{op}: by-regime means every regime "
                            f"one-sided", stats)
                elif c["straddle"] == "within-regime":
                    _expect(any(len(ls["sides"]) > 1
                                for ls in c["level_sides"]),
                            f"{rel}:{op}: within-regime means one regime "
                            f"holds both sides", stats)
        if rel in pinned_sign:
            for op, expect in pinned_sign[rel].items():
                ratios = {ri + 1: v for ri, v in enumerate(per_rat[op])}
                c = sign_classification(ratios, level_clusters(per_op[op]))
                _expect((c["verdict"], c["side"], c["straddle"]) == expect,
                        f"{rel}:{op}: pinned sign classification {expect}, "
                        f"got {(c['verdict'], c['side'], c['straddle'])}",
                        stats)

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
    print(f"rule 2 sign classification: {sign_cells} operator-cells over "
          f"the corpus -- {tally['regime-invariant slower']} "
          f"regime-invariant slower, {tally['regime-invariant faster']} "
          f"regime-invariant faster, {tally['by-regime']} regime-scoped "
          f"by-regime, {tally['within-regime']} regime-scoped "
          f"within-regime, {tally['no-side']} no-side")


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
    text = pathlib.Path(args[0]).read_text()
    per_op = parse_summary_per_run_baseline(text)
    try:
        ratios = parse_summary_per_run_ratios(text)
    except ValueError:
        ratios = None
    print(render_section(per_op, ratios=ratios))


if __name__ == "__main__":
    main()
