#!/usr/bin/env python3
"""Harness-side regime classification for the gpu-subgroup-reduce records
(JUN-58, the 2026-10-23 claim protocol, rules 1, 2 and 3).

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
  - Clock identity is never asserted (this module reads no clock).
    Cross-operator level identity at RUN level is a mechanical
    publication fact (cross_operator_level_identity /
    render_identity_section): per record, the operators' rule-1 run
    partitions are tested for agreement, and where they agree a
    record's prose may name one level across operators; where they
    diverge, the divergent run pairs are named and the per-operator
    level names stay operator-scoped. Pair-level cross-operator
    identity is its own mechanical publication fact at pair
    granularity (cross_operator_pair_level_identity /
    render_pair_identity_section, published inside the --pairs output
    when the record carries at least two operators): the same
    partition-agreement test over the shared (run, pair) key set, with
    keys completed by some operators only NAMED and excluded, never
    silently dropped. The rule-2 cell row is still only an
    admissibility roll-up over pooled per-run ratios -- it carries no
    cross-operator regime structure regardless of the identity verdicts
    (rule 4: an identity verdict changes no rule-2 verdict, no rule-3
    phrase, no selection answer).
  - Rule 1/2 themselves are RUN-level (per-run baseline medians, per-run
    ratios), which is what rule 1 asks a record to publish. Pair-level
    classification (a run's clock can ramp mid-run) is its own section
    (parse_run_log_pairs / pair_level_classification /
    render_pair_level_section, CLI --pairs): the SAME GAP-1.15 rule at
    pair granularity, plus the rule-2 machine applied to pairs as a
    published ANALOGUE only -- no rule-2 verdict is amended by it.

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

RULE 3 (the regime-matched comparison), mechanised:

  Rule 3 of the protocol: a magnitude comparison across sessions or
  cells is drawn within matched regime strata; when the regime mixes
  differ the claim names the split ("magnitude splits by clock regime")
  and attributes the deviation to session mixing -- it is never
  published as a failure to reproduce. The reproduction vocabulary is
  exactly three phrases: "reproduces in sign strictly" (all per-run
  ratios hold the historical sign), "magnitude reproduces within
  <delta>" (matched regime mixes), "magnitude splits by clock regime"
  (mixed). This module compares two measurement records mechanically
  (regime_matched_comparison / cell_regime_matched_comparison, published
  by render_rule3_section):

  - the SIGN phrase is rule 2's, for reproduction: "reproduces in sign
    strictly" exactly when the historical cell is regime-invariant on
    some side and every per-run ratio of the new cell holds that same
    side. A regime-scoped historical cell has no single historical sign
    to hold, so the phrase cannot be claimed (named in the output).
  - the MAGNITUDE phrase is keyed on the regime mix of the paired
    median's DRAW (the prose's "the medians' regime mixes differ"). The
    draw is the middle run(s) of the (ratio, run) sort; TIES are named,
    not resolved -- every run tying a middle ratio is a candidate draw,
    so a tie cannot silently pick the pure stratum. The mixes are
    matched exactly when both draws lie within one rule-1 level each and
    those two levels match under rule 1's OWN single-linkage test at
    GAP-1.15 (some member median of one within 1.15x of some member
    median of the other). Matched -> "magnitude reproduces within
    <delta>" where <delta> is the observed deviation of the published
    paired medians (quoted from the summary's own median column, so the
    phrase digits match the committed prose). Mixed -> "magnitude splits
    by clock regime".
  - the comparison is ALSO drawn within every matched stratum pair
    (per-stratum ratio medians and their delta) -- the record's
    regime-matched magnitude datum. The cell-median delta and the
    within-stratum delta publish side by side, so a session-mixing
    artifact cannot masquerade as a reproduction failure (or a
    reproduction).

  Two boundary cases the prose did not decide are decided mechanically
  and published (the GAP-1.15 ethos applied to comparisons): the tie
  rule for draws (above), and the cross-cell stratum-matching rule
  (rule 1's own single-linkage test -- "matched" is gpu-ns compatibility
  under the same constant that defines a level within a session; the
  harness reads no clock and asserts no cross-session clock identity, so
  the corpus prose's cross-session slow/fast naming is the assumption
  this replaces with a visible test). Where the machine's verdict
  diverges from a record's manual prose, the divergence is printed and
  pinned in --self-test, not bent away.

CROSS-OPERATOR LEVEL IDENTITY (the run partition across operators):

  Rule 1 classifies per operator, which leaves the cross-operator
  question open: is a run's regime operator-independent? This module
  answers it mechanically (cross_operator_level_identity, published by
  render_identity_section in the single-record output when the record
  has at least two operators):

  - the test is PARTITION AGREEMENT: for every run pair, every operator
    must agree on whether the two runs sit in the same rule-1 level
    (GAP-1.15, applied per operator). Agreement on every pair =
    "identity holds" -- a record's prose may then name one level across
    operators. Any divergent pair = "identity refuted" -- the pairs are
    NAMED with every operator's relation, and the per-operator level
    names stay operator-scoped (one operator's fastest level is not
    another's).
  - where the partitions disagree, the disagreement's SHAPE is
    published too: partition refinement between every operator pair
    (equal partitions / one refines the other / cross-cutting).
  - this is a publication fact about one record's regime structure.
    Rule 4 stands: it changes no rule-2 verdict, no rule-3 phrase, no
    selection answer, no :measured? flag, no workgroup row. Clock
    identity is never asserted (the harness reads no clock).

PAIR-LEVEL CROSS-OPERATOR IDENTITY (the pair partition across
operators):

  The pair-level section classifies per operator; the cross-operator
  question at pair granularity is answered by the SAME test at pair
  granularity (cross_operator_pair_level_identity, published by
  render_pair_identity_section inside the --pairs output when the
  record carries at least two operators):

  - partition agreement over the shared (run, pair) key set: for every
    key pair, every operator must agree on whether the two pairs sit in
    the same rule-1 pair level (GAP-1.15, per operator). Agreement
    everywhere = "identity holds"; any divergent key pair = "identity
    refuted", the per-operator level names stay operator-scoped.
  - one contract decision this granularity forces: operator key sets
    may disagree (a pair can lose an arm in one operator's block), and
    incompleteness is data -- the keys missing from some operator are
    NAMED and excluded, never silently dropped; refusal happens only
    below two operators or two shared keys. Divergent key pairs are
    published by CLASS (every divergent pair in exactly one class,
    counts sum to the verdict's total), because a 6 x 20 record has
    7140 key pairs and one row per pair hides the shape behind bulk.
  - rule 4 again: the verdict changes no rule-2 verdict, no rule-3
    phrase, no selection answer, no :measured? flag, no workgroup row.
    The same (run, pair) index is not one wall-clock moment across
    operators (each operator's pairs run in its own block of the op
    order), so this is agreement of pair partitions over a shared key
    index set, not clock identity.

WGSL WALL-CLOCK CHANNEL (rule 1, metric-named):

  The 2026-10-25 claim-protocol WGSL channel adoption (ADR-0360, "the
  claim-protocol WGSL channel" amendment; record
  docs/evidence/gpu/claim-protocol-wgsl-channel-20261025.txt) carries
  rule 1 with the baseline metric NAMED BY THE CHANNEL: the WGSL
  channel's only clock is host wall-clock submit->completion
  (performance.now) -- the measured adapter refuses GPU-core timestamps.
  The clustering mechanism is THIS module's, unchanged and
  metric-parametric (GAP-1.15 over per-run medians); only the
  publication names the metric (parse_wgsl_measure_log /
  render_wgsl_rule1_section, CLI --wgsl-log).

  RUN UNIT on this channel (the adoption's parenthetical, "per cell-arm
  run"): one run is one cell-arm sampling block -- (n, W, operator,
  metric) -- whose per-run median is that block's median over its
  paired rounds of the arm's host submit->completion time (the
  measure-log's own `time` line). The MSL channel's run is a fresh
  process; this channel's is the paired sampling block. single and
  batch32 are TWO metrics of this channel (one dispatch per submit vs
  amortized over 32 dispatches in one command buffer); each clusters
  only its own runs -- never mixed.

  RULE 2'S UNIT on this channel (PUBLISHED, this module's
  render_wgsl_sign_section): the per-run ratio is the block's
  paired-median ratio (median over the block's rounds of
  subgroup/baseline -- the measure-log's `pair` line), and a WGSL sign
  claim is channel-scoped (it never flips an MSL cell and never answers
  a workgroup row). The publication is REGIME-MATCHED SIGN PER LEVEL
  over the record's pair lines, per metric (single and batch32 never
  mix), the MSL channel's sign_classification machine unchanged -- rule
  1's GAP-1.15 clusters of the same runs' baseline medians are the
  regimes. The rule-1 section itself still renders no sign verdict;
  rule 2 publishes in its own section beside it (the two sections are
  what --wgsl-log prints, with a rule-2 status token between them; a
  record with no `pair` lines carries no sign to classify and the token
  says so).

  DELIBERATE BOUNDARY: the classifier is never run over the committed
  2026-10-25 pre-adoption measure-log's VALUES in this module's tests
  -- that record stays OUT of the claim protocol (it predates the
  adoption) and the named UNMEASURED question (do the WGSL host-clock
  baselines cluster into more than one regime level at all?) is
  answered only by a fresh claim-protocol run. The corpus self-test
  checks that log's STRUCTURE only and pins that it still carries no
  regime section.

CLI:

    python3 scripts/gpu_regime_classify.py <summary.md>
        print the claim-protocol sections (rule 1; the cross-operator
        level identity section when the record has at least two
        operators; rule 2 when the record carries per-run ratios) for
        one measurement record
    python3 scripts/gpu_regime_classify.py --compare <historical.md> <new.md>
        print the claim-protocol rule-3 section: the regime-matched
        comparison of two measurement records (first = the historical
        cell the claim is drawn against)
    python3 scripts/gpu_regime_classify.py --pairs <run-log.txt>
        print the pair-level regime classification (rule 1's GAP-1.15
        rule at pair granularity, plus the rule-2 machine as an
        ANALOGUE) from the driver's raw run log, followed by the
        pair-level cross-operator identity section when the log
        carries at least two operators
    python3 scripts/gpu_regime_classify.py --wgsl-log <measure-log.txt|->
        print the claim-protocol publication for a WGSL wall-clock
        measurement record: the metric-named rule-1 section, the rule-2
        status token, and the rule-2 sign section (regime-matched sign
        per level over the record's `pair` lines) -- or a named rule-2
        absence when the record carries no paired ratios (read the
        measure-log from a path or from stdin with '-')
    python3 scripts/gpu_regime_classify.py --self-test
        unit fixtures + a regression pass over every committed summary.md
        under docs/evidence/ (pinned manual classifications must
        reproduce; cluster invariants must hold; rule-3 pins reproduce
        the closing-cell prose where it decided, and the machine's
        divergence is pinned where it decides alone; pair-level pins
        over the op-order cell's committed run-log, machine vs the
        manual instrument's buckets)

The measurement driver (scripts/gpu-subgroup-reduce-metal-measure.py)
imports render_section() and appends the section to every summary.md it
writes.
"""

import pathlib
import re
import statistics
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
                 "regime is the rule-1 cluster. The cell row carries only "
                 "the admissibility roll-up, no cross-operator regime "
                 "structure -- cross-operator level identity (its own "
                 "section) is a publication fact about the regime "
                 "structure and never re-scopes a rule-2 verdict.")
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
                 "Cross-operator level identity is tested mechanically "
                 "and published in its own section below when the record "
                 "has at least two operators. Rule 2's "
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
    if len(per_op) >= 2:
        lines.append("")
        lines.append(render_identity_section(per_op, gap_max))
    if ratios is not None:
        lines.append("")
        lines.append(render_sign_section(per_op, ratios, gap_max))
    return "\n".join(lines)


# ------------------------------------------------------- rule 3 machinery

def parse_summary_published_medians(text):
    """Parse the published paired median ratios out of a driver summary.md.

    Returns {operator: median}. The summary's own median column IS the
    record's published paired statistic (median of the per-run ratios);
    the rule-3 delta phrases quote it so a phrase like "within 0.002"
    matches the committed prose digit for digit. Raises ValueError on a
    summary with no per-run ratio rows.
    """
    out = {}
    for line in text.splitlines():
        m = re.match(r"\| (\w+) \| ([\d.]+(?:, [\d.]+)+) \| ([\d.]+) \|",
                     line)
        if m:
            op, _pr, med = m.groups()
            out[op] = float(med)
    if not out:
        raise ValueError("no '| op | per-run ratios | median ratio |' rows "
                         "found in summary")
    return out


def median_draw(ratios):
    """The regime mix of a paired median: which runs draw it.

    ratios: {run_index (1-based int): per-run paired ratio}
    The paired median of n ratios is the mean of the two middle values
    under (ratio, run) sort order (the single middle value when n is
    odd). TIES are named, not resolved: every run whose ratio equals a
    middle-position ratio is a candidate draw, so a tie cannot silently
    pick the pure stratum. Returns {
      "mid_runs": [run, ...],     (the (ratio, run)-sort middle runs)
      "mid_ratios": [float, ...], (sorted)
      "candidates": [run, ...],   (every run tying a middle ratio)
    }
    """
    if not ratios:
        raise ValueError("no per-run ratios to draw the median from")
    ordered = sorted(ratios.items(), key=lambda kv: (kv[1], kv[0]))
    n = len(ordered)
    if n % 2 == 0:
        mid = [ordered[n // 2 - 1], ordered[n // 2]]
    else:
        mid = [ordered[n // 2]]
    mid_ratios = sorted({v for _, v in mid})
    mid_set = set(mid_ratios)
    candidates = sorted(r for r, v in ratios.items() if v in mid_set)
    return {"mid_runs": [r for r, _ in mid], "mid_ratios": mid_ratios,
            "candidates": candidates}


def draw_levels(draw, levels):
    """Which rule-1 levels the candidate draw runs sit in.

    Returns [(level_index_1_based, [runs, ...]), ...] fastest level
    first. The draw is PURE exactly when this has one entry.
    """
    run_level = {}
    for i, lv in enumerate(levels, start=1):
        for r in lv["runs"]:
            run_level[r] = i
    out = {}
    for r in draw["candidates"]:
        out.setdefault(run_level[r], []).append(r)
    return sorted((i, sorted(rs)) for i, rs in out.items())


def strata_matched(lv_a, lv_b, gap_max=GAP_MAX):
    """Rule-3 stratum matching across two cells, by rule 1's own rule.

    Two regime levels from different sessions are MATCHED when the
    GAP-1.15 single-linkage test would merge them: some member median of
    one is within gap_max of some member median of the other. The
    harness reads no clock, so "matched" is gpu-ns compatibility under
    the SAME constant that defines a level within a session -- not
    verified clock identity across sessions.
    """
    for va in lv_a["medians"].values():
        for vb in lv_b["medians"].values():
            if max(va, vb) / min(va, vb) <= gap_max:
                return True
    return False


def _stratum_ratio_median(ratios, level):
    vals = sorted(ratios[r] for r in level["runs"])
    n = len(vals)
    return (vals[n // 2] if n % 2
            else 0.5 * (vals[n // 2 - 1] + vals[n // 2]))


def regime_matched_comparison(hist_meds, hist_rats, hist_pub,
                              new_meds, new_rats, new_pub,
                              gap_max=GAP_MAX):
    """Claim-protocol rule 3, mechanically, for ONE operator's two cells.

    hist_*: the historical cell (per-run baseline medians {run: float},
            per-run ratios {run: float}, published paired median float);
    new_*: the reproduction cell, same shape (same run indices within a
           cell; run indices need not correspond across cells).
    Returns {
      "sign_ok": bool, "sign_phrase": str,
      "matched": bool, "magnitude_phrase": str, "delta": float,
      "draw": {"hist": ..., "new": ...},   (median_draw + draw_levels)
      "levels": {"hist": [...], "new": [...]},
      "matched_strata": [(i, j, med_h, med_n, dlt, runs_h, runs_n), ...],
      "unmatched": {"hist": [i, ...], "new": [j, ...]},
    }

    The magnitude phrase is exactly one of the protocol's two magnitude
    vocabulary phrases; the sign phrase is the vocabulary's sign phrase
    or a named non-phrase (the vocabulary names reproductions only).
    """
    lv_h = level_clusters(hist_meds, gap_max)
    lv_n = level_clusters(new_meds, gap_max)
    draw_h = median_draw(hist_rats)
    draw_n = median_draw(new_rats)
    dl_h = draw_levels(draw_h, lv_h)
    dl_n = draw_levels(draw_n, lv_n)
    pure_h, pure_n = len(dl_h) == 1, len(dl_n) == 1
    matched = (pure_h and pure_n
               and strata_matched(lv_h[dl_h[0][0] - 1],
                                  lv_n[dl_n[0][0] - 1], gap_max))
    delta = abs(new_pub - hist_pub)
    # rule 2 supplies the historical sign the phrase must hold
    c_h = sign_classification(hist_rats, lv_h)
    if c_h["verdict"] == "regime-invariant" and all(
            ratio_side(r) == c_h["side"] for r in new_rats.values()):
        sign_ok = True
        sign_phrase = ("reproduces in sign strictly (all "
                       f"{len(new_rats)} per-run ratios hold the "
                       f"historical sign: {c_h['side']})")
    else:
        sign_ok = False
        if c_h["verdict"] != "regime-invariant":
            sign_phrase = ("no single historical sign to hold (the "
                           f"historical cell is regime-scoped, "
                           f"{c_h['straddle']})")
        else:
            sides = {ratio_side(r) for r in new_rats.values()}
            sign_phrase = (f"sign does not reproduce strictly (new-cell "
                           f"per-run ratio sides: "
                           f"{', '.join(sorted(sides))}; historical sign: "
                           f"{c_h['side']})")
    magnitude_phrase = ("magnitude reproduces within "
                        f"{delta:.3f}") if matched \
        else "magnitude splits by clock regime"
    # the within-stratum datum: every matched stratum pair
    matched_strata = []
    used_h, used_n = set(), set()
    for i, lvh in enumerate(lv_h, start=1):
        for j, lvn in enumerate(lv_n, start=1):
            if strata_matched(lvh, lvn, gap_max):
                mh = _stratum_ratio_median(hist_rats, lvh)
                mn = _stratum_ratio_median(new_rats, lvn)
                matched_strata.append((i, j, mh, mn, abs(mn - mh),
                                       lvh["runs"], lvn["runs"]))
                used_h.add(i)
                used_n.add(j)
    unmatched = {"hist": [i for i in range(1, len(lv_h) + 1)
                          if i not in used_h],
                 "new": [j for j in range(1, len(lv_n) + 1)
                         if j not in used_n]}
    return {"sign_ok": sign_ok, "sign_phrase": sign_phrase,
            "matched": matched, "magnitude_phrase": magnitude_phrase,
            "delta": delta,
            "draw": {"hist": {**draw_h, "levels": dl_h, "pure": pure_h},
                     "new": {**draw_n, "levels": dl_n, "pure": pure_n}},
            "levels": {"hist": lv_h, "new": lv_n},
            "matched_strata": matched_strata, "unmatched": unmatched}


def load_comparison_cell(text, label):
    """Build the cell shape regime_matched_comparison consumes, from one
    summary.md. Returns {"label", "medians", "ratios", "published"} with
    per-operator dicts (ratios keyed by run index).
    """
    med = parse_summary_per_run_baseline(text)
    rats = {op: {ri + 1: v for ri, v in enumerate(rs)}
            for op, rs in parse_summary_per_run_ratios(text).items()}
    pub = parse_summary_published_medians(text)
    return {"label": label, "medians": med, "ratios": rats,
            "published": pub}


def cell_regime_matched_comparison(hist, new, gap_max=GAP_MAX):
    """Rule 3 for a whole cell pair: every shared operator, plus the
    cell roll-up (a cell reproduces its magnitude only when EVERY
    operator's comparison is regime-matched).
    """
    ops = sorted(set(hist["ratios"]) & set(new["ratios"]))
    if not ops:
        raise ValueError("the two cells share no operator")
    per_op = {}
    for op in ops:
        per_op[op] = regime_matched_comparison(
            hist["medians"][op], hist["ratios"][op], hist["published"][op],
            new["medians"][op], new["ratios"][op], new["published"][op],
            gap_max)
    sign_ok = all(c["sign_ok"] for c in per_op.values())
    matched = all(c["matched"] for c in per_op.values())
    delta = max(c["delta"] for c in per_op.values())
    split_ops = [op for op in ops if not per_op[op]["matched"]]
    if matched:
        cell_magnitude = f"magnitude reproduces within {delta:.3f}"
    else:
        cell_magnitude = ("magnitude splits by clock regime (mixed: "
                          f"{', '.join(split_ops)})")
    return {"per_op": per_op, "ops": ops, "sign_ok": sign_ok,
            "matched": matched, "delta": delta, "split_ops": split_ops,
            "cell_magnitude": cell_magnitude}


def render_rule3_section(hist, new, gap_max=GAP_MAX, via=None):
    """The claim-protocol rule-3 section for a comparison of two
    measurement records. hist/new: load_comparison_cell() shapes.
    via: the publication path to name in the section header (default the
    --compare CLI; the measurement driver's auto-wiring passes its own
    name so a section never claims a publication path it did not take).
    Returns markdown (no trailing newline).
    """
    cell = cell_regime_matched_comparison(hist, new, gap_max)

    def _draw_desc(d):
        if d["pure"]:
            i, rs = d["levels"][0]
            return (f"pure (level {i}, runs "
                    + ", ".join(str(r) for r in rs) + ")")
        return ("mixed (" + "; ".join(
            f"level {i}: runs " + ", ".join(str(r) for r in rs)
            for i, rs in d["levels"]) + ")")

    lines = []
    lines.append("## Regime-matched comparison (claim protocol rule 3)")
    lines.append("")
    lines.append(f"Published by {via or 'scripts/gpu_regime_classify.py --compare'}: "
                 f"**{hist['label']}** (historical) against "
                 f"**{new['label']}**. Rule 3: a magnitude comparison "
                 f"across sessions or cells is drawn within matched "
                 f"regime strata; when the regime mixes differ the claim "
                 f"names the split (\"magnitude splits by clock regime\") "
                 f"and attributes the deviation to session mixing -- "
                 f"never \"failed to reproduce\". The reproduction "
                 f"vocabulary is exactly three phrases. Strata match "
                 f"across cells under rule 1's own single-linkage test at "
                 f"GAP-1.15 (the harness reads no clock: matched = "
                 f"gpu-ns-compatible, not verified clock identity). The "
                 f"magnitude phrase's delta is the observed deviation of "
                 f"the published paired medians.")
    lines.append("")
    lines.append("| operator | sign phrase | magnitude phrase | median draw "
                 "(historical / new) |")
    lines.append("|---|---|---|---|")
    for op in cell["ops"]:
        c = cell["per_op"][op]
        lines.append(f"| {op} | {c['sign_phrase']} | "
                     f"{c['magnitude_phrase']} | "
                     f"{_draw_desc(c['draw']['hist'])} / "
                     f"{_draw_desc(c['draw']['new'])} |")
    lines.append("")
    lines.append(f"Cell: sign -- "
                 f"{'reproduces in sign strictly (every operator)' if cell['sign_ok'] else 'does NOT reproduce strictly (see per-operator detail)'}; "
                 f"magnitude -- {cell['cell_magnitude']}.")
    lines.append("")
    lines.append("Within-stratum comparison (the regime-matched datum; "
                 "per matched stratum pair, the per-run ratio medians of "
                 "the member runs):")
    lines.append("")
    lines.append("| operator | strata (hist / new) | runs (hist / new) | "
                 "median ratio (hist / new) | delta |")
    lines.append("|---|---|---|---|---|")
    for op in cell["ops"]:
        c = cell["per_op"][op]
        for (i, j, mh, mn, dlt, rh, rn) in c["matched_strata"]:
            lines.append(
                f"| {op} | {i} / {j} | "
                f"{', '.join(str(r) for r in rh)} / "
                f"{', '.join(str(r) for r in rn)} | "
                f"{mh:.3f} / {mn:.3f} | {dlt:.3f} |")
        if c["unmatched"]["hist"] or c["unmatched"]["new"]:
            lines.append(
                f"| {op} | unmatched levels | hist: "
                f"{', '.join(str(i) for i in c['unmatched']['hist']) or '-'}; "
                f"new: "
                f"{', '.join(str(j) for j in c['unmatched']['new']) or '-'} | "
                f"- | - |")
    return "\n".join(lines)


def append_comparison_section(hist_text, hist_label, new_text, new_label,
                              gap_max=GAP_MAX, via=None):
    """The driver auto-wiring primitive (claim protocol rule 3).

    Returns new_text with the rule-3 section appended as the record's
    final section, drawn from exactly the text that will be published:
    the single-record sections are never rewritten and the appended
    section is byte-identical to what `--compare <hist> <new>` prints
    for the same pair (modulo the `via` header). The single-record
    parsers are round-trip safe through the appended text (the rule-3
    tables match none of their row shapes) -- the self-test asserts it.
    """
    section = render_rule3_section(
        load_comparison_cell(hist_text, hist_label),
        load_comparison_cell(new_text, new_label),
        gap_max, via=via)
    return new_text.rstrip("\n") + "\n\n" + section + "\n"


# ----------------------------------------------- pair-level machinery

def parse_run_log_pairs(text):
    """Parse the raw pair samples out of a measurement driver run-log.txt.

    Returns (pairs, incomplete):
      pairs:      {(run, op, pair): {"baseline": float, "variant": float,
                                     "order": str}} -- both arms seen;
      incomplete: same shape, one arm missing. Incomplete pairs are
                  NAMED by this function and never silently dropped: a
                  ramping clock that loses an arm is data about the run,
                  not noise to be deleted.

    Run indices come from the '===== fresh-process run N =====' headers
    (1-based, as the driver writes them); pair indices are the log's own.
    """
    pairs = {}
    run = 0
    for line in text.splitlines():
        m = re.match(r"===== fresh-process run (\d+) =====", line)
        if m:
            run = int(m.group(1))
            continue
        m = re.match(r"sample op=(\w+) pair=(\d+) order=(\S) arm=(\w+) "
                     r"gpu_ns=([\d.]+)", line)
        if m:
            op, p, order, arm, gpu = m.groups()
            key = (run, op, int(p))
            rec = pairs.setdefault(key, {"order": order})
            if arm in rec:
                raise ValueError(f"duplicate arm {arm!r} for pair {key}")
            rec[arm] = float(gpu)
    complete, incomplete = {}, {}
    for key, rec in sorted(pairs.items()):
        if "baseline" in rec and "variant" in rec:
            complete[key] = rec
        else:
            incomplete[key] = rec
    return complete, incomplete


def pair_level_classification(pairs, gap_max=GAP_MAX):
    """Pair-level regime classification: rule 1's rule at pair granularity.

    pairs: {key: {"baseline": float, "variant": float}} with key an opaque
           sortable (run, op, pair) tuple -- complete pairs only.
    Returns {op: {"levels": [level, ...],        (fastest first; each
                  "ratios": {key: variant/baseline},
                  "sign": sign_classification() over the pairs}}

    The clustering rule is rule 1's OWN rule, unchanged: GAP-1.15
    single-linkage, applied to the individual pairs' baseline gpu-ns per
    operator instead of to per-run baseline medians. This is the named
    gap (a run's clock can ramp mid-run: the op-order cell's within-run
    ramping needs per-pair levels). NOT rule 2: rule 2's verdicts stay
    run-level over per-run ratios; the "sign" field here is the rule-2
    machine applied at pair granularity, published as an ANALOGUE only --
    it never replaces or amends a rule-2 verdict, and it cannot choose a
    variant. Cross-operator level identity (run level and pair level) is
    NOT asserted here -- both are their own sections
    (cross_operator_level_identity / cross_operator_pair_level_identity).
    """
    if not pairs:
        raise ValueError("no complete pairs to classify")
    by_op = {}
    for (run, op, p), rec in pairs.items():
        by_op.setdefault(op, {})[(run, p)] = rec
    out = {}
    for op in sorted(by_op):
        recs = by_op[op]
        baselines = {k: r["baseline"] for k, r in recs.items()}
        ratios = {k: r["variant"] / r["baseline"] for k, r in recs.items()}
        levels = level_clusters(baselines, gap_max)
        out[op] = {"levels": levels, "ratios": ratios,
                   "sign": sign_classification(ratios, levels)}
    return out


def render_pair_level_section(pairs, incomplete=None, gap_max=GAP_MAX,
                              via=None):
    """The pair-level classification section for a measurement record.

    pairs: complete pairs as returned by parse_run_log_pairs
    incomplete: the parser's named incomplete pairs (published, not hidden)
    Returns markdown (no trailing newline).
    """
    if incomplete is None:
        incomplete = {}
    cls = pair_level_classification(pairs, gap_max)
    lines = []
    lines.append("## Pair-level regime classification (rule 1's rule at "
                 "pair granularity)")
    lines.append("")
    lines.append("Published by " + (via or "scripts/gpu_regime_classify.py "
                                    "--pairs") + ": A run's clock can ramp "
                 "mid-run, so run-level classification is blind to "
                 "within-run regime changes: this section classifies the "
                 "individual pairs instead. The clustering rule is rule 1's "
                 "OWN rule, unchanged -- GAP-1.15 single-linkage -- applied "
                 "to the pairs' baseline gpu-ns per operator (pair "
                 "granularity instead of per-run medians). The harness "
                 "reads no GPU clock; a level is one observed baseline "
                 "plateau. Pair-level cross-operator identity is its "
                 "own section below when the record carries at least "
                 "two operators (run-level cross-operator identity is "
                 "its own section in the record's rule-1 block).")
    lines.append("")
    lines.append("What this section is NOT: it is not rule 2. Rule 2's "
                 "verdicts stay run-level over per-run ratios; the sides "
                 "column is the rule-2 machine applied at pair granularity, "
                 "published as an ANALOGUE for the regime question only -- "
                 "it never amends a rule-2 verdict and cannot choose a "
                 "variant. No `:measured?` flag, workgroup row, flip gate "
                 "or selection answer moves.")
    lines.append("")
    lines.append("| operator | level | pairs | baseline gpu-ns range | "
                 "median pair ratio | sides |")
    lines.append("|---|---|---|---|---|---|")
    for op in sorted(cls):
        lvls = cls[op]["levels"]
        n = len(lvls)
        for i, lv in enumerate(lvls, start=1):
            tag = _level_tag(i, n)
            rng = (f"{lv['lo']:.0f}" if lv["lo"] == lv["hi"]
                   else f"{lv['lo']:.0f}..{lv['hi']:.0f}")
            ratios = [cls[op]["ratios"][k] for k in lv["runs"]]
            med = statistics.median(ratios)
            sides = {ratio_side(r) for r in ratios}
            side_txt = (f"{sum(1 for r in ratios if r > 1.0)}/"
                        f"{len(ratios)} slower")
            if "faster" in sides:
                side_txt += (f", {sum(1 for r in ratios if r < 1.0)}/"
                             f"{len(ratios)} faster")
            if "even" in sides:
                side_txt += (f", {sum(1 for r in ratios if r == 1.0)}/"
                             f"{len(ratios)} at 1.0")
            lines.append(f"| {op} | {tag} | {len(ratios)} | {rng} | "
                         f"{med:.3f} | {side_txt} |")
    lines.append("")
    for op in sorted(cls):
        c = cls[op]["sign"]
        n = sum(c["counts"].values())
        if c["verdict"] == "regime-invariant":
            verdict = (f"pair-level analogue for {op}: regime-invariant, "
                       f"{c['side']} ({n}/{n} {c['side']})")
        else:
            verdict = (f"pair-level analogue for {op}: regime-scoped "
                       f"({c['counts']['slower']} slower, "
                       f"{c['counts']['faster']} faster"
                       + (f", {c['counts']['even']} at 1.0"
                          if c["counts"]["even"] else "")
                       + f"; straddle {c['straddle']})")
        lines.append(verdict + ".")
    if incomplete:
        keys = ", ".join(f"run {r} {op} pair {p}"
                         for (r, op, p) in sorted(incomplete))
        lines.append("")
        lines.append(f"Incomplete pairs, named and excluded "
                     f"({len(incomplete)}): {keys}.")
    per_op = {}
    for (r, op, p), rec in pairs.items():
        per_op.setdefault(op, {})[(r, p)] = rec["baseline"]
    if len(per_op) >= 2:
        lines.append("")
        lines.append(render_pair_identity_section(
            per_op, gap_max,
            via=(via or "scripts/gpu_regime_classify.py --pairs")))
    return "\n".join(lines)


# ------------------------------- cross-operator identity machinery

def cross_operator_level_identity(per_op, gap_max=GAP_MAX):
    """Cross-operator level identity, mechanically: do the operators'
    rule-1 run partitions agree?

    per_op: {operator: {run_index: baseline per-run median gpu-ns}} for
            at least two operators over the SAME run set.

    Rule 1 classifies per operator, which leaves the cross-operator
    question open: is a run's regime operator-independent? The
    mechanical test is PARTITION AGREEMENT -- for every run pair, every
    operator must agree on whether the two runs sit in the same rule-1
    level (GAP-1.15 applied per operator). Returns {
      "verdict": "identity-holds" | "identity-refuted",
      "ops": [op, ...], "runs": [run, ...],
      "levels": {op: [level, ...]},        (rule 1's own clusters)
      "partitions": {op: {run: level_index}},  (1-based, fastest 1)
      "divergent": [(a, b, {op: "same-level" | "split-level"}), ...],
      "refinements": [(fine, coarse), ...]  (fine's partition refines
        coarse's, equality included -- both directions = equal)
    }

    This is a publication fact about one record's regime structure. It
    NEVER changes a rule-2 verdict, a rule-3 phrase, a selection answer,
    a :measured? flag or a workgroup row (rule 4). Where identity
    refutes, the per-operator level names stay operator-scoped -- one
    operator's fastest level is not another's. The harness reads no GPU
    clock: identity is agreement of the run partitions, not verified
    clock identity, and pair-level cross-operator identity is not
    tested here.
    """
    if len(per_op) < 2:
        raise ValueError("cross-operator level identity needs at least "
                         "two operators")
    ops = sorted(per_op)
    run_sets = {op: set(med) for op, med in per_op.items()}
    if len({frozenset(s) for s in run_sets.values()}) != 1:
        raise ValueError("operators disagree on the run set: "
                         + "; ".join(f"{op} {sorted(s)}"
                                     for op, s in sorted(run_sets.items())))
    runs = sorted(run_sets[ops[0]])
    if len(runs) < 2:
        raise ValueError("cross-operator level identity needs at least "
                         "two runs")
    levels = {op: level_clusters(per_op[op], gap_max) for op in ops}
    partitions = {}
    for op in ops:
        partitions[op] = {}
        for i, lv in enumerate(levels[op], start=1):
            for r in lv["runs"]:
                partitions[op][r] = i

    def same(op, a, b):
        return partitions[op][a] == partitions[op][b]

    divergent = []
    for ia, a in enumerate(runs):
        for b in runs[ia + 1:]:
            rels = {}
            for op in ops:
                rels[op] = "same-level" if same(op, a, b) else "split-level"
            if len(set(rels.values())) > 1:
                divergent.append((a, b, rels))
    refinements = []
    for fine in ops:
        for coarse in ops:
            if fine == coarse:
                continue
            if all(not same(fine, a, b) or same(coarse, a, b)
                   for ia, a in enumerate(runs) for b in runs[ia + 1:]):
                refinements.append((fine, coarse))
    return {"verdict": ("identity-holds" if not divergent
                        else "identity-refuted"),
            "ops": ops, "runs": runs, "levels": levels,
            "partitions": partitions, "divergent": divergent,
            "refinements": refinements}


def render_identity_section(per_op, gap_max=GAP_MAX, via=None):
    """The cross-operator level identity section for one measurement
    record. per_op: {operator: {run_index: baseline per-run median}}.
    Returns markdown (no trailing newline).
    """
    ident = cross_operator_level_identity(per_op, gap_max)
    ops = ident["ops"]
    npairs = len(ident["runs"]) * (len(ident["runs"]) - 1) // 2
    lines = []
    lines.append("## Cross-operator level identity (the rule-1 partition "
                 "across operators)")
    lines.append("")
    lines.append("Published by " + (via or "scripts/gpu_regime_classify.py")
                 + ": rule 1 classifies per operator; this section tests "
                 "mechanically whether those classifications describe ONE "
                 "regime structure. The test is partition agreement -- for "
                 "every run pair, every operator must agree on whether the "
                 "two runs sit in the same rule-1 level (GAP-1.15, applied "
                 "per operator). The harness reads no GPU clock and asserts "
                 "no clock identity: identity here is agreement of the run "
                 "partitions, nothing more.")
    lines.append("")
    if ident["verdict"] == "identity-holds":
        lines.append(f"Verdict: **identity holds** -- the rule-1 run "
                     f"partition is identical across "
                     f"{', '.join(ops)} (all {npairs} run pairs agree). "
                     f"Where it holds, a record's prose may name one "
                     f"level across these operators.")
    else:
        lines.append(f"Verdict: **identity refuted** -- "
                     f"{len(ident['divergent'])} of {npairs} run pairs "
                     f"diverge across {', '.join(ops)} (named below). "
                     f"Per-operator level names stay operator-scoped: "
                     f"one operator's fastest level is not another's.")
    lines.append("")
    refin = set(ident["refinements"])
    rel_lines = []
    for i, o1 in enumerate(ops):
        for o2 in ops[i + 1:]:
            if (o1, o2) in refin and (o2, o1) in refin:
                rel_lines.append(f"{o1} and {o2}: equal partitions")
            elif (o1, o2) in refin:
                rel_lines.append(f"{o1}'s partition refines {o2}'s "
                                 f"({o2} pools what {o1} splits)")
            elif (o2, o1) in refin:
                rel_lines.append(f"{o2}'s partition refines {o1}'s "
                                 f"({o1} pools what {o2} splits)")
            else:
                rel_lines.append(f"{o1} and {o2} cross-cut (neither "
                                 f"partition refines the other)")
    lines.append("Partition relations (the disagreement's shape where "
                 "the partitions disagree): " + "; ".join(rel_lines) + ".")
    if ident["divergent"]:
        lines.append("")
        lines.append(f"Divergent run pairs ({len(ident['divergent'])} of "
                     f"{npairs}):")
        lines.append("")
        lines.append("| run pair | " + " | ".join(ops) + " |")
        lines.append(("|---" * (len(ops) + 1)) + "|")
        for a, b, rels in ident["divergent"]:
            lines.append(f"| {a} vs {b} | "
                         + " | ".join(rels[op] for op in ops) + " |")
    lines.append("")
    lines.append("What this section does NOT do (rule 4, unchanged): it "
                 "changes no rule-2 verdict, no rule-3 phrase, no "
                 "selection answer, no `:measured?` flag, no workgroup "
                 "row. Pair-level cross-operator identity is its own "
                 "test at pair granularity (the pair-level section "
                 "publishes it); nothing in this run-level section "
                 "licenses or refutes a pair-level naming.")
    return "\n".join(lines)


# ----------------------- pair-level cross-operator identity machinery

def cross_operator_pair_level_identity(per_op, gap_max=GAP_MAX):
    """Pair-level cross-operator identity: the pair partition across
    operators, tested exactly as the run partition is.

    per_op: {operator: {(run, pair): baseline gpu-ns}} -- each
    operator's complete pair baselines, the same maps
    pair_level_classification clusters (so the levels compared here ARE
    the pair-level section's levels). Returns {
      "verdict": "identity-holds" | "identity-refuted",
      "ops": [op, ...], "keys": [(run, pair), ...]  (the shared ground
        set, sorted),
      "excluded": {(run, pair): [op, ...]}  (key completed by SOME
        operators only; NAMED here, never silently dropped),
      "levels": {op: [level, ...]},        (rule 1's own pair clusters)
      "partitions": {op: {key: level_index}},  (1-based, fastest 1)
      "divergent": [(a, b, {op: "same-level" | "split-level"}), ...],
      "refinements": [(fine, coarse), ...]  (fine's partition refines
        coarse's, equality included -- both directions = equal)
    }

    The mechanical test is the run-level one, unchanged: PARTITION
    AGREEMENT over the shared (run, pair) key set -- for every key pair,
    every operator must agree on whether the two pairs sit in the same
    rule-1 pair level (GAP-1.15, applied per operator to that
    operator's own pairs). Agreement on every key pair -> "identity
    holds" (one record's prose may then name one pair level across
    operators); any divergent key pair -> "identity refuted" (the pairs
    named with every operator's relation, the per-operator level names
    stay operator-scoped).

    One contract decision this granularity forces (the run-level
    contract cannot be copied verbatim): operators' key sets may
    DISAGREE (a pair can lose an arm in one operator's block and not
    another's), and the parser's rule stands -- incompleteness is data,
    not noise to be deleted. So a key-set mismatch does NOT refuse here:
    the keys missing from some operator are NAMED in "excluded" and the
    agreement test runs on the shared ground set only. Refusal happens
    only below two operators or below two shared keys.

    This is a publication fact about one record's regime structure (rule
    4, unchanged): it never changes a rule-2 verdict, a rule-3 phrase,
    a selection answer, a :measured? flag or a workgroup row. The
    harness reads no GPU clock and asserts no clock identity -- and the
    same (run, pair) index is not one wall-clock moment across
    operators (each operator's pairs run in its own block of the
    driver's op order), so identity here is agreement of the pair
    partitions over the shared key index set, nothing more. Clock
    identity remains unasserted.
    """
    if len(per_op) < 2:
        raise ValueError("pair-level cross-operator identity needs at "
                         "least two operators")
    ops = sorted(per_op)
    key_sets = {op: set(m) for op, m in per_op.items()}
    shared = set.intersection(*key_sets.values())
    if len(shared) < 2:
        raise ValueError("pair-level cross-operator identity needs at "
                         "least two shared pair keys, got "
                         f"{len(shared)}")
    excluded = {}
    for k in sorted(set.union(*key_sets.values()) - shared):
        excluded[k] = [op for op in ops if k in key_sets[op]]
    keys = sorted(shared)
    levels = {op: level_clusters(per_op[op], gap_max) for op in ops}
    partitions = {}
    for op in ops:
        partitions[op] = {}
        for i, lv in enumerate(levels[op], start=1):
            for k in lv["runs"]:
                partitions[op][k] = i

    def same(op, a, b):
        return partitions[op][a] == partitions[op][b]

    divergent = []
    for ia, a in enumerate(keys):
        for b in keys[ia + 1:]:
            rels = {}
            for op in ops:
                rels[op] = "same-level" if same(op, a, b) else "split-level"
            if len(set(rels.values())) > 1:
                divergent.append((a, b, rels))
    refinements = []
    for fine in ops:
        for coarse in ops:
            if fine == coarse:
                continue
            if all(not same(fine, a, b) or same(coarse, a, b)
                   for ia, a in enumerate(keys) for b in keys[ia + 1:]):
                refinements.append((fine, coarse))
    return {"verdict": ("identity-holds" if not divergent
                        else "identity-refuted"),
            "ops": ops, "keys": keys, "excluded": excluded,
            "levels": levels, "partitions": partitions,
            "divergent": divergent, "refinements": refinements}


def render_pair_identity_section(per_op, gap_max=GAP_MAX, via=None):
    """The pair-level cross-operator identity section for one
    measurement record. per_op: {operator: {(run, pair): baseline}}.
    Returns markdown (no trailing newline).

    The divergent key pairs are published by CLASS, not one row per
    pair: a 6-run x 20-pair record has 7140 key pairs, and a table with
    thousands of rows hides the disagreement's shape behind its own
    bulk. Every divergent key pair belongs to exactly one class (its
    operators' relation tuple) and each class publishes its count and
    named example key pairs -- the counts sum to the verdict's total,
    asserted in --self-test, so nothing is silently dropped.
    """
    ident = cross_operator_pair_level_identity(per_op, gap_max)
    ops = ident["ops"]
    keys = ident["keys"]
    npairs = len(keys) * (len(keys) - 1) // 2

    def _key(k):
        return f"run {k[0]} pair {k[1]}"

    lines = []
    lines.append("## Pair-level cross-operator identity (the pair "
                 "partition across operators)")
    lines.append("")
    lines.append("Published by " + (via or "scripts/gpu_regime_classify.py "
                                    "--pairs") + ": the pair-level "
                 "section classifies per operator; this section tests "
                 "mechanically whether those pair classifications "
                 "describe ONE regime structure. The test is the "
                 "run-level identity test at pair granularity, "
                 "unchanged -- partition agreement over the shared "
                 "(run, pair) key set: for every key pair, every "
                 "operator must agree on whether the two pairs sit in "
                 "the same rule-1 pair level (GAP-1.15, applied per "
                 "operator). The harness reads no GPU clock and asserts "
                 "no clock identity; the same (run, pair) index is not "
                 "one wall-clock moment across operators (each "
                 "operator's pairs run in its own block of the driver's "
                 "op order), so identity here is agreement of the pair "
                 "partitions over the shared key index set, nothing "
                 "more.")
    lines.append("")
    if ident["verdict"] == "identity-holds":
        lines.append(f"Verdict: **identity holds** -- the pair-level "
                     f"partition is identical across {', '.join(ops)} "
                     f"(all {npairs} key pairs agree). Where it holds, "
                     f"a record's prose may name one pair level across "
                     f"these operators.")
    else:
        lines.append(f"Verdict: **identity refuted** -- "
                     f"{len(ident['divergent'])} of {npairs} key pairs "
                     f"diverge across {', '.join(ops)} (their classes "
                     f"below). Per-operator pair level names stay "
                     f"operator-scoped: one operator's fastest pair "
                     f"level is not another's.")
    lines.append("")
    refin = set(ident["refinements"])
    rel_lines = []
    for i, o1 in enumerate(ops):
        for o2 in ops[i + 1:]:
            if (o1, o2) in refin and (o2, o1) in refin:
                rel_lines.append(f"{o1} and {o2}: equal partitions")
            elif (o1, o2) in refin:
                rel_lines.append(f"{o1}'s partition refines {o2}'s "
                                 f"({o2} pools what {o1} splits)")
            elif (o2, o1) in refin:
                rel_lines.append(f"{o2}'s partition refines {o1}'s "
                                 f"({o1} pools what {o2} splits)")
            else:
                rel_lines.append(f"{o1} and {o2} cross-cut (neither "
                                 f"partition refines the other)")
    lines.append("Partition relations (the disagreement's shape where "
                 "the partitions disagree): " + "; ".join(rel_lines) + ".")
    if ident["divergent"]:
        classes = {}
        for a, b, rels in ident["divergent"]:
            sig = tuple(rels[op] for op in ops)
            classes.setdefault(sig, []).append((a, b))
        lines.append("")
        lines.append(f"Divergent key pairs ({len(ident['divergent'])} of "
                     f"{npairs}), by class (every divergent key pair is "
                     f"in exactly one class; the counts sum to "
                     f"{len(ident['divergent'])}):")
        lines.append("")
        lines.append("| " + " | ".join(ops) + " | key pairs | examples |")
        lines.append(("|---" * (len(ops) + 2)) + "|")
        for sig, members in sorted(classes.items(),
                                   key=lambda kv: (-len(kv[1]), kv[0])):
            examples = "; ".join(f"{_key(a)} vs {_key(b)}"
                                 for a, b in members[:3])
            if len(members) > 3:
                examples += f"; +{len(members) - 3} more"
            lines.append("| " + " | ".join(sig) + f" | {len(members)} | "
                         + examples + " |")
    if ident["excluded"]:
        lines.append("")
        lines.append("Excluded keys, named and not compared "
                     f"({len(ident['excluded'])}; completed by some "
                     "operators only, never silently dropped): "
                     + "; ".join(
                         f"{_key(k)} ({', '.join(ops_have)})"
                         for k, ops_have in sorted(
                             ident["excluded"].items())) + ".")
    lines.append("")
    lines.append("What this section does NOT do (rule 4, unchanged): it "
                 "changes no rule-2 verdict (pair-level and run-level), "
                 "no rule-3 phrase, no selection answer, no "
                 "`:measured?` flag, no workgroup row. Clock identity "
                 "is never asserted (the harness reads no clock).")
    return "\n".join(lines)


# ------------------------------------------- WGSL wall-clock channel (rule 1)
# The claim-protocol WGSL channel adoption (2026-10-25, ADR-0360) carries
# rule 1 with the baseline metric NAMED BY THE CHANNEL: host wall-clock
# submit->completion, milliseconds. The clustering mechanism is this
# module's own (GAP-1.15, metric-parametric); only the publication names
# the metric. See the module docstring for the run unit ("per cell-arm
# run") and the deliberate boundary on the pre-adoption log.

WGSL_METRICS = ("single", "batch32")

WGSL_METRIC_TEXT = {
    "single": ("host wall-clock submit->completion, milliseconds (one "
               "dispatch per queue submit; the performance.now bracket "
               "submit -> onSubmittedWorkDone)"),
    "batch32": ("host wall-clock submit->completion per dispatch, "
                "milliseconds (32 dispatches of the same kernel in one "
                "command buffer; the submit bracket divided by 32)"),
}

WGSL_TIME_RE = re.compile(
    r"^time n=(\d+) w=(\d+) op=(\w+) arm=(\w+) "
    r"single_median_ms=([\d.]+) single_rounds=(\d+) "
    r"batch32_median_ms=([\d.]+) batch32_rounds=(\d+)\s*$")

WGSL_PAIR_RE = re.compile(
    r"^pair n=(\d+) w=(\d+) op=(\w+) "
    r"single_paired_ratio=([\d.]+) batch32_paired_ratio=([\d.]+) "
    r"rounds=(\d+)/(\d+)\s*$")


def parse_wgsl_measure_log(text):
    """Parse the per-run medians out of a WGSL measure-log.

    Returns {metric: {op: {(n, w): {"baseline": float or None,
                                    "subgroup": float or None}}}}
    where metric is 'single' or 'batch32' and (n, w) is the run identity
    of the adoption's \"per cell-arm run\" (one cell-arm sampling block;
    its per-run median is the block's `time` line). Raises ValueError on
    a log with no `time` lines and on a duplicate (metric, op, run, arm)
    -- a duplicated block is a measurement error, not a merge candidate.
    """
    out = {m: {} for m in WGSL_METRICS}
    seen = set()
    n_time = 0
    for line in text.splitlines():
        m = WGSL_TIME_RE.match(line)
        if not m:
            continue
        n, w, op, arm, sm, _sr, bm, _br = m.groups()
        n_time += 1
        run = (int(n), int(w))
        for metric, val in (("single", sm), ("batch32", bm)):
            key = (metric, op, run, arm)
            if key in seen:
                raise ValueError(f"duplicate time line for {key}")
            seen.add(key)
            rec = out[metric].setdefault(op, {}).setdefault(
                run, {"baseline": None, "subgroup": None})
            rec[arm] = float(val)
    if n_time == 0:
        raise ValueError("no 'time n=... w=... op=... arm=...' lines found "
                         "in the WGSL measure log")
    return out


def parse_wgsl_measure_pairs(text):
    """Parse the per-run paired-median ratios out of a WGSL measure-log.

    Rule 2's unit on this channel (the `pair` line). Returns
    {metric: {op: {(n, w): paired-median ratio (subgroup/baseline)}}}
    -- one ratio per (n, W, op) block per metric. Raises ValueError on
    a log with no `pair` lines and on a duplicate (metric, op, run)
    -- a duplicated block is a measurement error, not a merge candidate.
    """
    out = {m: {} for m in WGSL_METRICS}
    seen = set()
    n_pair = 0
    for line in text.splitlines():
        m = WGSL_PAIR_RE.match(line)
        if not m:
            continue
        n, w, op, sr, br = m.group(1, 2, 3, 4, 5)
        n_pair += 1
        run = (int(n), int(w))
        for metric, val in (("single", sr), ("batch32", br)):
            key = (metric, op, run)
            if key in seen:
                raise ValueError(f"duplicate pair line for {key}")
            seen.add(key)
            out[metric].setdefault(op, {})[run] = float(val)
    if n_pair == 0:
        raise ValueError("no 'pair n=... w=... op=...' lines found in "
                         "the WGSL measure log -- rule 2's unit on this "
                         "channel is the block's paired-median ratio")
    return out


def _wgsl_fmt(v):
    return f"{v:.4f}"


def render_wgsl_rule1_section(parsed, gap_max=GAP_MAX):
    """The claim-protocol rule-1 section for a WGSL wall-clock record.

    parsed: parse_wgsl_measure_log's return. Returns markdown (no
    trailing newline). Rule 1 ONLY -- nothing here renders a sign
    verdict (rule 2's sign classification publishes in its own section
    beside this one, render_wgsl_sign_section), and no :measured? flag
    or workgroup row is in scope of this publication (rule 4,
    unchanged).
    """
    lines = []
    lines.append("## Regime classification (claim protocol rule 1, "
                 "WGSL wall-clock channel)")
    lines.append("")
    lines.append("Published by scripts/gpu_regime_classify.py (GAP-1.15), "
                 "invoked by the WGSL measurement harness. This channel's "
                 "baseline metric is NAMED BY THE CHANNEL (the 2026-10-25 "
                 "claim-protocol WGSL adoption, ADR-0360): host wall-clock "
                 "submit->completion in milliseconds -- the harness reads "
                 "no GPU clock. A regime here is a cluster of the observed "
                 "baseline per-run median levels in that metric, named by "
                 "its host-ms range, per operator.")
    lines.append("")
    lines.append("Run unit on this channel (the adoption's \"per cell-arm "
                 "run\"): one run is one cell-arm sampling block -- "
                 "(n, W, operator, metric) -- whose per-run median is the "
                 "block's median over its paired rounds of host "
                 "submit->completion (the measure-log's own `time` line). "
                 "The MSL channel's run is a fresh process; this "
                 "channel's is the paired sampling block. single and "
                 "batch32 are TWO metrics of the channel (one dispatch "
                 "per submit vs amortized over 32 dispatches in one "
                 "command buffer); each clusters only its own runs -- "
                 "never mixed.")
    lines.append("")
    lines.append("Clustering rule GAP-1.15: per operator, the per-run "
                 "baseline medians sorted ascending, single-linkage -- the "
                 "next median joins the current level at <= 1.15x the "
                 "previous, else it starts a new level. The rule is "
                 "metric-parametric as written (its 1.15 window derives "
                 "from the MSL corpus's decided separation and carries "
                 "unchanged); only the publication names the metric. "
                 "Rule 2's sign classification is published in its own "
                 "section beside this one (regime-matched sign per "
                 "level over this record's `pair` lines) -- this rule-1 "
                 "section itself renders no sign verdict -- and rule 4 "
                 "is unchanged: this publication moves no "
                 "`:measured?` flag and no workgroup row.")
    for metric in WGSL_METRICS:
        per_op = parsed.get(metric) or {}
        if not per_op:
            continue
        lines.append("")
        lines.append(f"### metric: {metric} -- {WGSL_METRIC_TEXT[metric]}")
        lines.append("")
        lines.append("Per-run baseline medians (rule 1's first publication; "
                     "baseline = the :reduce WGSL arm):")
        lines.append("")
        lines.append("| operator | run (n, W) | baseline per-run median "
                     "(host ms) |")
        lines.append("|---|---|---|")
        missing = []
        for op in sorted(per_op):
            for run in sorted(per_op[op]):
                rec = per_op[op][run]
                if rec["baseline"] is None:
                    missing.append((op, run))
                    continue
                lines.append(f"| {op} | n={run[0]} W={run[1]} | "
                             f"{_wgsl_fmt(rec['baseline'])} |")
        lines.append("")
        lines.append("Regime clusters:")
        lines.append("")
        lines.append("| operator | level | host-ms range | runs (baseline "
                     "per-run median) |")
        lines.append("|---|---|---|---|")
        for op in sorted(per_op):
            med = {run: rec["baseline"] for run, rec in per_op[op].items()
                   if rec["baseline"] is not None}
            if not med:
                raise ValueError(f"operator {op} has no baseline run median "
                                 f"in metric {metric} -- nothing to cluster")
            levels = level_clusters(med, gap_max)
            n = len(levels)
            for i, lv in enumerate(levels, start=1):
                tag = _level_tag(i, n)
                rng = (_wgsl_fmt(lv["lo"]) if lv["lo"] == lv["hi"]
                       else f"{_wgsl_fmt(lv['lo'])}..{_wgsl_fmt(lv['hi'])}")
                members = ", ".join(
                    f"n={r[0]} W={r[1]} ({_wgsl_fmt(lv['medians'][r])})"
                    for r in lv["runs"])
                lines.append(f"| {op} | {tag} | {rng} | {members} |")
        if missing:
            lines.append("")
            lines.append("Named and excluded (a block with no baseline arm "
                         "sample -- incomplete blocks are data, never "
                         "silently dropped): "
                         + "; ".join(f"{op} n={run[0]} W={run[1]}"
                                     for op, run in missing) + ".")
    return "\n".join(lines)


def _wgsl_run_label(run):
    return f"n={run[0]} W={run[1]}"


def _wgsl_level_sign_phrase(sides, runs):
    """The per-level sign phrase: one-sided / mixed / all-at-1.0, counts."""
    n = len(runs)
    counts = {"slower": 0, "faster": 0, "even": 0}
    for _r, _v, s in runs:
        counts[s] += 1
    if sides == {"faster"}:
        return f"one-sided faster ({n}/{n} below 1.0)"
    if sides == {"slower"}:
        return f"one-sided slower ({n}/{n} above 1.0)"
    if sides == {"even"}:
        return f"all at 1.0 ({n}/{n})"
    parts = []
    if counts["slower"]:
        parts.append(f"{counts['slower']} above 1.0")
    if counts["faster"]:
        parts.append(f"{counts['faster']} below 1.0")
    if counts["even"]:
        parts.append(f"{counts['even']} at 1.0")
    return "mixed sides (" + ", ".join(parts) + ")"


def render_wgsl_sign_section(parsed, pairs, gap_max=GAP_MAX):
    """The claim-protocol rule-2 section for a WGSL wall-clock record.

    parsed: parse_wgsl_measure_log's return -- the rule-1 side; its
            GAP-1.15 clusters of the per-run baseline medians are the
            observed regimes of this record.
    pairs: parse_wgsl_measure_pairs's return -- rule 2's unit on this
           channel, the block's paired-median subgroup/baseline ratio
           (the `pair` line).

    Publishes REGIME-MATCHED SIGN PER LEVEL over the record's pair
    lines: per metric (single and batch32 NEVER mix), per operator, the
    MSL channel's sign_classification machine unchanged -- a sign is
    regime-invariant when every per-run ratio of every observed regime
    lies on the same side of 1.0; only such a sign may be a selection
    basis -- plus the per-metric cell roll-up (every operator
    regime-invariant on the SAME side). Sign claims are CHANNEL-SCOPED
    (the 2026-10-25 adoption carries rule 2 in full): a WGSL-channel
    sign never flips an MSL cell and never answers a workgroup row.
    Rule 4 is unchanged -- this publication moves no :measured? flag
    and no workgroup row. Runs the rule-1 levels cannot place (a pair
    line with no baseline per-run median) and rule-1 runs with no pair
    line (rule 2 has no unit for them) are NAMED and excluded, never
    silently dropped.
    """
    lines = []
    lines.append("## Sign classification (claim protocol rule 2, "
                 "WGSL wall-clock channel)")
    lines.append("")
    lines.append("Published by scripts/gpu_regime_classify.py from the "
                 "record's own `pair` lines (rule 2's unit on this "
                 "channel: the per-run ratio is the block's "
                 "paired-median ratio, median over the block's rounds "
                 "of subgroup/baseline) and the rule-1 regime clusters "
                 "of the same runs' baseline per-run medians "
                 "(GAP-1.15, host-ms). Rule 2: a sign is "
                 "regime-invariant when every per-run ratio of every "
                 "observed regime lies on the same side of 1.0 -- only "
                 "such a sign may be a selection basis; any other sign "
                 "is regime-scoped and cannot choose a variant. The "
                 "sign machine is the MSL channel's, unchanged and "
                 "metric-parametric; single and batch32 are TWO metrics "
                 "of this channel and classify separately, never "
                 "mixed.")
    lines.append("")
    lines.append("Sign claims on this channel are CHANNEL-SCOPED "
                 "(rule 2 carries in full, the 2026-10-25 adoption): a "
                 "WGSL-channel sign never flips an MSL cell and never "
                 "answers a workgroup row. Rule 4 is unchanged -- this "
                 "publication moves no `:measured?` flag and no "
                 "workgroup row.")
    for metric in WGSL_METRICS:
        per_op_pairs = pairs.get(metric) or {}
        per_op_parsed = parsed.get(metric) or {}
        if not per_op_pairs and not per_op_parsed:
            continue
        lines.append("")
        lines.append(f"### metric: {metric} -- {WGSL_METRIC_TEXT[metric]}")
        named_unplaceable = []
        named_unpaired = []
        op_cls = {}
        op_med = {}
        for op in sorted(set(per_op_pairs) | set(per_op_parsed)):
            ratios_all = per_op_pairs.get(op) or {}
            med_all = {run: rec["baseline"]
                       for run, rec in (per_op_parsed.get(op) or {}).items()
                       if rec["baseline"] is not None}
            ratios = {r: v for r, v in ratios_all.items() if r in med_all}
            for r in sorted(set(ratios_all) - set(ratios)):
                named_unplaceable.append(
                    f"{_wgsl_run_label(r)} ({op})")
            for r in sorted(set(med_all) - set(ratios)):
                named_unpaired.append(f"{_wgsl_run_label(r)} ({op})")
            if not ratios:
                continue
            med = {r: med_all[r] for r in ratios}
            op_med[op] = med
            op_cls[op] = sign_classification(ratios,
                                             level_clusters(med, gap_max))
            op_cls[op]["ratios"] = ratios
        if not op_cls:
            lines.append("")
            lines.append("No classifiable pair ratios in this metric.")
        else:
            lines.append("")
            lines.append("Regime-matched sign per level (rule 1's "
                         "levels of this metric; the sign of the pair "
                         "ratios within each level):")
            lines.append("")
            lines.append("| operator | level | runs (paired ratio) | "
                         "level sign |")
            lines.append("|---|---|---|---|")
            for op in sorted(op_cls):
                cls = op_cls[op]
                nlevels = len(cls["level_sides"])
                for ls in cls["level_sides"]:
                    tag = _level_tag(ls["level"], nlevels)
                    runs = ", ".join(
                        f"{_wgsl_run_label(r)} ({v:.3f})"
                        for r, v, _s in ls["runs"])
                    phrase = _wgsl_level_sign_phrase(ls["sides"], ls["runs"])
                    lines.append(f"| {op} | {tag} | {runs} | {phrase} |")
            lines.append("")
            lines.append("| operator | verdict | side | detail |")
            lines.append("|---|---|---|---|")
            for op in sorted(op_cls):
                c = op_cls[op]
                n = sum(c["counts"].values())
                if c["verdict"] == "regime-invariant":
                    detail = (_side_phrase(c["side"], n)
                              + "; every observed regime one-sided")
                    side = c["side"]
                elif c["straddle"] == "no-side":
                    detail = ("every ratio is exactly 1.0 -- no sign "
                              "exists to claim")
                    side = "none"
                else:
                    nlevels = len(c["level_sides"])
                    segs = "; ".join(
                        f"level {ls['level']} "
                        f"({_level_name(ls['level'], nlevels)}): "
                        + ", ".join(
                            f"{_wgsl_run_label(r)} {v:.3f} "
                            f"{'above' if s == 'slower' else 'below' if s == 'faster' else 'at'} 1.0"
                            for r, v, s in ls["runs"])
                        for ls in c["level_sides"])
                    if c["straddle"] == "by-regime":
                        detail = ("straddle separates by regime (every "
                                  "regime one-sided, regimes disagree): "
                                  + segs)
                    else:
                        mixed = [str(ls["level"]) for ls in c["level_sides"]
                                 if len(ls["sides"]) > 1]
                        detail = (f"straddle within regime "
                                  f"{', '.join(mixed)} (one regime "
                                  f"holds both sides): " + segs)
                    side = "straddles 1.0"
                lines.append(f"| {op} | {c['verdict']} | {side} | "
                             f"{detail} |")
            cell = cell_sign_classification(
                {op: cls["ratios"] for op, cls in op_cls.items()},
                op_med, gap_max)
            n = sum(cell["counts"].values())
            pooled = (f"{cell['counts']['slower']} above 1.0, "
                      f"{cell['counts']['faster']} below 1.0"
                      + (f", {cell['counts']['even']} at 1.0"
                         if cell["counts"]["even"] else ""))
            if cell["verdict"] == "regime-invariant":
                cell_line = (f"Cell (metric {metric}, all {n} paired "
                             f"ratios pooled): **regime-invariant**, "
                             f"{cell['side']} ({n}/{n} {cell['side']}).")
            else:
                bad = sorted(op for op, c in cell["per_op"].items()
                             if c["verdict"] != "regime-invariant")
                cell_line = (f"Cell (metric {metric}, all {n} paired "
                             f"ratios pooled): **regime-scoped** "
                             f"({pooled}) -- not a selection basis; "
                             f"non-invariant operators: "
                             f"{', '.join(bad)}.")
            lines.append("")
            lines.append(cell_line)
        if named_unplaceable or named_unpaired:
            lines.append("")
            segs = []
            if named_unplaceable:
                segs.append("named and excluded (a pair line the "
                            "rule-1 levels cannot place -- no baseline "
                            "per-run median, so no regime): "
                            + "; ".join(named_unplaceable))
            if named_unpaired:
                segs.append("named and excluded (a rule-1 run with no "
                            "pair line -- rule 2 has no unit for it): "
                            + "; ".join(named_unpaired))
            lines.append("Incomplete data, named not dropped: "
                         + "; ".join(segs) + ".")
    return "\n".join(lines)


def render_wgsl_claim_protocol(text):
    """The full claim-protocol publication for a WGSL measure log.

    The metric-named rule-1 section, the rule-2 status token, and the
    rule-2 sign section (render_wgsl_sign_section) -- or a named
    rule-2 absence when the record carries no `pair` lines (a record
    without paired ratios carries no sign to classify). A duplicated
    block is a measurement error and propagates as ValueError.
    """
    parsed = parse_wgsl_measure_log(text)
    out = [render_wgsl_rule1_section(parsed)]
    if not any(WGSL_PAIR_RE.match(l) for l in text.splitlines()):
        out.append("claim-protocol-rule2: NOT PUBLISHED -- no `pair` "
                   "lines in this record (rule 2's unit on this "
                   "channel is the block's paired-median ratio) -- a "
                   "record without paired ratios carries no sign to "
                   "classify")
        return "\n\n".join(out)
    out.append("claim-protocol-rule2: PUBLISHED (regime-matched sign "
               "per level below; sign claims channel-scoped -- a "
               "WGSL-channel sign never flips an MSL cell and never "
               "answers a workgroup row; rule 4 unchanged: no "
               ":measured? flag and no workgroup row moves)")
    out.append(render_wgsl_sign_section(
        parsed, parse_wgsl_measure_pairs(text)))
    return "\n\n".join(out)


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


def _self_test_rule3_unit(stats):
    # ---- rule 3: median draw, stratum matching, comparison phrases ----

    # empty ratios refuse
    try:
        median_draw({})
        raise AssertionError("empty ratios must raise")
    except ValueError:
        stats["passed"] += 1

    # even n: the two middle positions under (ratio, run) sort
    # (sorted: run 2 = 1.1, run 1 = 1.2, run 4 = 1.3, run 3 = 1.4)
    d = median_draw({1: 1.2, 2: 1.1, 3: 1.4, 4: 1.3})
    _expect(d["mid_runs"] == [1, 4] and d["candidates"] == [1, 4],
            "even draw: middle two under (ratio, run)", stats)

    # odd n: the single middle (sorted: run 2 = 1.1, run 1 = 1.2,
    # run 3 = 1.3 -> the middle is run 1)
    d = median_draw({1: 1.2, 2: 1.1, 3: 1.3})
    _expect(d["mid_runs"] == [1] and d["candidates"] == [1],
            "odd draw: the single middle", stats)

    # ties are NAMED, not resolved: a tie cannot pick the pure stratum
    d = median_draw({1: 1.192, 2: 1.178, 3: 1.192, 4: 1.192,
                     5: 1.196, 6: 1.194})
    _expect(d["mid_ratios"] == [1.192] and d["candidates"] == [1, 3, 4],
            "tie draw: every run tying a middle ratio is a candidate",
            stats)

    # draw_levels: pure and mixed
    lv = level_clusters({1: 100.0, 2: 100.0, 3: 300.0, 4: 301.0})
    dl = draw_levels({"candidates": [1, 2]}, lv)
    _expect(dl == [(1, [1, 2])], "pure draw", stats)
    dl = draw_levels({"candidates": [1, 3]}, lv)
    _expect(dl == [(1, [1]), (2, [3])], "mixed draw", stats)

    # strata_matched: rule 1's own single-linkage test across cells
    a = {"medians": {1: 100.0}}
    b = {"medians": {1: 115.0}}
    _expect(strata_matched(a, b), "exactly 1.15x across cells matches",
            stats)
    b = {"medians": {1: 115.01}}
    _expect(not strata_matched(a, b), "1.1501x across cells does not "
            "match", stats)

    # comparison: both draws pure and matched -> the delta phrase, with
    # the observed deviation digit for digit
    c = regime_matched_comparison(
        {1: 100.0, 2: 101.0, 3: 100.5, 4: 100.7},
        {1: 1.200, 2: 1.201, 3: 1.200, 4: 1.199}, 1.200,
        {1: 100.2, 2: 100.9, 3: 101.1, 4: 100.4},
        {1: 1.202, 2: 1.203, 3: 1.201, 4: 1.202}, 1.202)
    _expect(c["matched"] and c["magnitude_phrase"]
            == "magnitude reproduces within 0.002"
            and c["sign_ok"] and c["sign_phrase"].startswith(
                "reproduces in sign strictly"),
            "matched mixes -> 'magnitude reproduces within <delta>' "
            "(delta from the published medians: 0.002)", stats)

    # comparison: mixed historical draw -> the split phrase, never
    # "failed to reproduce"
    c = regime_matched_comparison(
        {1: 37.0, 2: 37.1, 3: 37.2, 4: 119.0, 5: 119.4, 6: 119.3},
        {1: 1.182, 2: 1.179, 3: 1.178, 4: 1.192, 5: 1.194, 6: 1.194},
        1.187,
        {1: 118.6, 2: 118.9, 3: 96.1, 4: 119.3, 5: 118.9, 6: 119.1},
        {1: 1.197, 2: 1.201, 3: 1.187, 4: 1.196, 5: 1.200, 6: 1.197},
        1.197)
    _expect(not c["matched"] and c["magnitude_phrase"]
            == "magnitude splits by clock regime"
            and "failed to reproduce" not in c["magnitude_phrase"],
            "mixed draw -> 'magnitude splits by clock regime'", stats)

    # comparison: both draws pure but the strata do not match (fast vs
    # slow across sessions) -> still the split phrase
    c = regime_matched_comparison(
        {1: 37.0, 2: 37.1},
        {1: 0.9, 2: 0.91}, 0.905,
        {1: 119.0, 2: 119.1},
        {1: 1.2, 2: 1.21}, 1.205)
    _expect(not c["matched"] and c["magnitude_phrase"]
            == "magnitude splits by clock regime",
            "pure draws in UNmatched strata -> split phrase", stats)

    # sign phrase refusal: a regime-scoped historical cell has no single
    # historical sign to hold
    c = regime_matched_comparison(
        {1: 37.0, 2: 119.0},
        {1: 0.95, 2: 1.05}, 1.0,
        {1: 37.1, 2: 119.1},
        {1: 1.02, 2: 1.03}, 1.025)
    _expect(not c["sign_ok"] and "no single historical sign" in
            c["sign_phrase"],
            "regime-scoped historical cell refuses the sign phrase", stats)

    # sign phrase refusal: the new cell does not hold the historical sign
    c = regime_matched_comparison(
        {1: 100.0, 2: 101.0},
        {1: 1.2, 2: 1.21}, 1.205,
        {1: 100.1, 2: 100.2},
        {1: 1.2, 2: 0.99}, 1.095)
    _expect(not c["sign_ok"] and "does not reproduce strictly" in
            c["sign_phrase"],
            "a new-cell ratio off the historical side refuses the sign "
            "phrase", stats)

    # the tie robustness shape (the historical :max w512 draw): three
    # runs tie the middle ratio across THREE strata -> mixed, whatever
    # order the tie resolves in
    c = regime_matched_comparison(
        {1: 49042.0, 2: 37625.0, 3: 119396.0, 4: 96438.0,
         5: 119312.0, 6: 119250.0},
        {1: 1.192, 2: 1.178, 3: 1.192, 4: 1.192, 5: 1.196, 6: 1.194},
        1.192,
        {1: 119166.0, 2: 119208.0, 3: 72542.0, 4: 119188.0,
         5: 119438.0, 6: 119500.0},
        {1: 1.197, 2: 1.197, 3: 1.186, 4: 1.194, 5: 1.195, 6: 1.191},
        1.195)
    _expect(not c["draw"]["hist"]["pure"]
            and len(c["draw"]["hist"]["levels"]) == 3
            and not c["matched"]
            and c["magnitude_phrase"] == "magnitude splits by clock regime",
            "the three-way 1.192 tie draws across three strata -> mixed, "
            "no tie resolution picks a pure stratum", stats)

    # cell roll-up: one split operator splits the cell
    hist = {"label": "h",
            "medians": {"sum": {1: 100.0, 2: 101.0},
                        "max": {1: 37.0, 2: 119.0}},
            "ratios": {"sum": {1: 1.2, 2: 1.21},
                       "max": {1: 1.182, 2: 1.192}},
            "published": {"sum": 1.205, "max": 1.187}}
    new = {"label": "n",
           "medians": {"sum": {1: 100.1, 2: 100.9},
                       "max": {1: 118.6, 2: 119.1}},
           "ratios": {"sum": {1: 1.202, 2: 1.203},
                      "max": {1: 1.197, 2: 1.201}},
           "published": {"sum": 1.2025, "max": 1.199}}
    cell = cell_regime_matched_comparison(hist, new)
    _expect(not cell["matched"] and cell["split_ops"] == ["max"]
            and cell["sign_ok"]
            and "splits by clock regime (mixed: max)" in
            cell["cell_magnitude"],
            "cell roll-up: one mixed operator splits the cell", stats)

    # the renderer's call shape
    out = render_rule3_section(hist, new)
    _expect("## Regime-matched comparison (claim protocol rule 3)" in out
            and "magnitude splits by clock regime" in out
            and "Within-stratum comparison" in out,
            "render_rule3_section publishes the rule-3 section", stats)


def _self_test_rule3_corpus(stats, corpus_root):
    """Rule 3 over the committed corpus: the closing cell's pins (prose
    decided sum and min; the machine decides max alone and the
    divergence is published), plus the full ten-pair re-sweep
    enumeration (printed, GAP-1.15 ethos: nothing hides).
    """
    def _load(rel):
        return load_comparison_cell(
            (corpus_root / rel / "summary.md").read_text(), rel)

    # ---- pins: the shape-2 w512 closing cell (the protocol's own
    # motivating case). Provenance of each pin:
    #   sum -- the closing NOTES: "Sum reproduces within 0.002 (1.202 vs
    #     1.200)": prose-decided matched, the machine reproduces it;
    #   min -- the closing NOTES: ":min lands +0.010 above ... the min
    #     median straddles the regime boundary"; the protocol record:
    #     "the medians' regime mixes differ": prose-decided split, the
    #     machine reproduces it;
    #   max -- the closing NOTES published "max within 0.003" as
    #     reproducing, by deviation size. Rule 3 AS DECIDED keys the
    #     phrase on the regime mix, not the deviation size, and this
    #     cell's historical :max median draw ties at 1.192 across THREE
    #     strata (runs 1/3/4) -- mixed by the tie rule whatever the tie
    #     resolution. The machine therefore says "magnitude splits by
    #     clock regime" where the manual prose said "within 0.003": the
    #     FIRST visible consequence of the protocol's own decision, and
    #     it is pinned here as the machine deciding alone, not bent back
    #     to the prose. The divergence is printed, never hidden.
    hist = _load("gpu-subgroup-reduce-m1max-shape2-band-20261023/w512")
    new = _load("gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w512")
    cell = cell_regime_matched_comparison(hist, new)
    pins = {
        "sum": (True, True, "magnitude reproduces within 0.002"),
        "max": (True, False, "magnitude splits by clock regime"),
        "min": (True, False, "magnitude splits by clock regime"),
    }
    for op, (sign_ok, matched, phrase) in pins.items():
        c = cell["per_op"][op]
        _expect(c["sign_ok"] == sign_ok and c["matched"] == matched
                and c["magnitude_phrase"] == phrase,
                f"closing cell {op}: pin (sign_ok={sign_ok}, "
                f"matched={matched}, {phrase!r}), got "
                f"(sign_ok={c['sign_ok']}, matched={c['matched']}, "
                f"{c['magnitude_phrase']!r})", stats)

    # the regime-matched datum at the closing cell: the min comparison
    # drawn WITHIN the matched slow stratum is 1.194 vs 1.197 = 0.003 --
    # the 0.010 cell-median deviation is session mixing, and rule 3
    # publishes both numbers side by side
    cmin = cell["per_op"]["min"]
    slow_pairs = [t for t in cmin["matched_strata"]
                  if t[5] == [4, 5, 6]]
    _expect(len(slow_pairs) == 1
            and round(slow_pairs[0][2], 3) == 1.194
            and round(slow_pairs[0][3], 3) == 1.197
            and round(slow_pairs[0][4], 3) == 0.003,
            "closing cell min: within-stratum (slow) comparison is "
            "1.194 vs 1.197 = 0.003 against the cell-median 0.010",
            stats)

    # ---- enumeration over the ten re-sweep pairs (published, not
    # asserted): every flip-set cell's historical-vs-re-sweep rule-3
    # verdicts
    print("rule 3 over the ten re-sweep pairs (historical -> re-sweep; "
          "printed, GAP-1.15 ethos):")
    # the ten re-sweep pairs, with the historical cell each re-sweep
    # actually re-swept (named in each re-sweep NOTES):
    #   shape-1: wsweep-low holds w64/w128, wsweep holds w256/w512/w1024;
    #   shape-2: shape2 holds the w256 anchor, the band holds the rest.
    pair_dirs = []
    for w, h in (("w64", "gpu-subgroup-reduce-m1max-wsweep-low-20261023"),
                 ("w128", "gpu-subgroup-reduce-m1max-wsweep-low-20261023"),
                 ("w256", "gpu-subgroup-reduce-m1max-wsweep-20261023"),
                 ("w512", "gpu-subgroup-reduce-m1max-wsweep-20261023"),
                 ("w1024", "gpu-subgroup-reduce-m1max-wsweep-20261023")):
        pair_dirs.append((f"{h}/{w}",
                          f"gpu-subgroup-reduce-m1max-resweep-20261023/{w}"))
    for w, h in (("w64", "gpu-subgroup-reduce-m1max-shape2-band-20261023"),
                 ("w128", "gpu-subgroup-reduce-m1max-shape2-band-20261023"),
                 ("w256", "gpu-subgroup-reduce-m1max-shape2-20261023"),
                 ("w512", "gpu-subgroup-reduce-m1max-shape2-band-20261023"),
                 ("w1024", "gpu-subgroup-reduce-m1max-shape2-band-20261023")):
        pair_dirs.append(
            (f"{h}/{w}",
             f"gpu-subgroup-reduce-m1max-shape2-resweep-20261023/{w}"))
    seen = 0
    for hrel, nrel in pair_dirs:
        hp = corpus_root / hrel / "summary.md"
        np_ = corpus_root / nrel / "summary.md"
        if not hp.exists() or not np_.exists():
            continue
        seen += 1
        c = cell_regime_matched_comparison(_load(hrel), _load(nrel))
        for op in c["ops"]:
            co = c["per_op"][op]
            print(f"  {nrel} {op}: sign "
                  f"{'reproduces strictly' if co['sign_ok'] else 'DOES NOT'}"
                  f"; {co['magnitude_phrase']} (cell-median delta "
                  f"{co['delta']:.3f}); draw hist "
                  f"{'pure' if co['draw']['hist']['pure'] else 'MIXED'}/"
                  f"new {'pure' if co['draw']['new']['pure'] else 'MIXED'}"
                  + ("; within-stratum "
                     + ", ".join(f"{t[2]:.3f}/{t[3]:.3f} d{t[4]:.3f}"
                                 for t in co["matched_strata"])
                     if co["matched_strata"] else ""))
    _expect(seen == 10, f"ten re-sweep pairs enumerated ({seen})", stats)


def _self_test_rule3_autowire(stats, corpus_root):
    """Driver auto-wiring of --compare: append_comparison_section() over
    the real corpus pair, pinned against the --compare machinery's own
    output and against the single-record parsers' round trip.
    """
    hist_path = (corpus_root
                 / "gpu-subgroup-reduce-m1max-shape2-band-20261023/w512")
    new_rel = "gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w512"
    hist_text = (hist_path / "summary.md").read_text()
    new_text = (corpus_root / new_rel / "summary.md").read_text()

    # the default header phrase is pinned unchanged: the --compare CLI's
    # published records must not drift
    section_default = render_rule3_section(
        load_comparison_cell(hist_text, "H"), load_comparison_cell(new_text, "N"))
    _expect(section_default.splitlines()[2].startswith(
                "Published by scripts/gpu_regime_classify.py --compare: "),
            "default via keeps the --compare CLI header phrase", stats)
    section_via = render_rule3_section(
        load_comparison_cell(hist_text, "H"), load_comparison_cell(new_text, "N"),
        via="driver-auto-wire-test")
    _expect("Published by driver-auto-wire-test: " in section_via,
            "via names the publication path that actually published", stats)

    # the append is additive: the single-record text stands byte-identical
    # as a prefix and the appended section equals --compare's output
    out = append_comparison_section(hist_text, "H", new_text, "N",
                                    via="driver-auto-wire-test")
    _expect(out.startswith(new_text.rstrip("\n") + "\n\n"),
            "auto-wire appends, never rewrites the single-record sections",
            stats)
    _expect(out.endswith(section_via + "\n"),
            "the appended section equals the --compare machinery's output",
            stats)

    # the single-record parsers round-trip through the appended text (the
    # rule-3 tables match none of their row shapes)
    for fn in (parse_summary_per_run_baseline, parse_summary_per_run_ratios,
               parse_summary_published_medians):
        _expect(fn(out) == fn(new_text),
                f"{fn.__name__} round-trips through the appended summary",
                stats)

    # a rule-1/2 section parsed from the appended record still classifies
    # the same runs (the record stays usable as the NEXT comparison's
    # historical side)
    rt = load_comparison_cell(out, "round-trip")
    fresh = load_comparison_cell(new_text, "fresh")
    _expect(rt["medians"] == fresh["medians"] and rt["ratios"] == fresh["ratios"]
            and rt["published"] == fresh["published"],
            "an appended record stays loadable as a comparison cell", stats)


def _self_test_pair_level_unit(stats):
    # -- parse_run_log_pairs: complete / incomplete / duplicate arm
    log = ("===== fresh-process run 1 =====\n"
           "device=X\n"
           "sample op=sum pair=0 order=A arm=baseline gpu_ns=1000.0 host_ns=2000\n"
           "sample op=sum pair=0 order=A arm=variant gpu_ns=900.0 host_ns=1900\n"
           "sample op=sum pair=1 order=B arm=variant gpu_ns=1150.0 host_ns=2100\n"
           "===== fresh-process run 2 =====\n"
           "sample op=sum pair=0 order=B arm=variant gpu_ns=1010.0 host_ns=2010\n"
           "sample op=sum pair=0 order=B arm=baseline gpu_ns=1111.0 host_ns=2111\n")
    complete, incomplete = parse_run_log_pairs(log)
    _expect(set(complete) == {(1, "sum", 0), (2, "sum", 0)},
            "complete pairs keyed (run, op, pair)", stats)
    _expect(set(incomplete) == {(1, "sum", 1)},
            "incomplete pairs are NAMED, not dropped", stats)
    _expect(complete[(1, "sum", 0)]["order"] == "A"
            and complete[(1, "sum", 0)]["baseline"] == 1000.0
            and complete[(1, "sum", 0)]["variant"] == 900.0,
            "arms and order parsed", stats)
    try:
        parse_run_log_pairs(
            "===== fresh-process run 1 =====\n"
            "sample op=sum pair=0 order=A arm=baseline gpu_ns=1.0 host_ns=1\n"
            "sample op=sum pair=0 order=A arm=baseline gpu_ns=2.0 host_ns=2\n")
        raise AssertionError("duplicate arm must raise")
    except ValueError:
        stats["passed"] += 1

    # -- pair_level_classification refuses an empty pair set
    try:
        pair_level_classification({})
        raise AssertionError("empty pairs must raise")
    except ValueError:
        stats["passed"] += 1

    # -- clustering at pair granularity is rule 1's rule: GAP-1.15 boundary
    mk = lambda k, b, v: {k: {"baseline": b, "variant": v}}
    pairs = {}
    pairs.update(mk((1, "sum", 0), 1000.0, 900.0))
    pairs.update(mk((1, "sum", 1), 1150.0, 1035.0))     # 1.150 -> merges
    cls = pair_level_classification(pairs)
    _expect(len(cls["sum"]["levels"]) == 1,
            "pair baselines at exactly 1.15x merge (<= rule)", stats)
    pairs = {}
    pairs.update(mk((1, "sum", 0), 1000.0, 900.0))
    pairs.update(mk((1, "sum", 1), 1150.1, 1035.0))     # 1.1501 -> splits
    cls = pair_level_classification(pairs)
    _expect(len(cls["sum"]["levels"]) == 2
            and cls["sum"]["levels"][1]["runs"] == [(1, 1)],
            "pair baselines just over 1.15x split", stats)
    _expect(cls["sum"]["ratios"][(1, 0)] == 0.9,
            "pair ratio is variant/baseline", stats)

    # -- the rule-2 machine at pair granularity, as an analogue
    pairs = {}
    pairs.update(mk((1, "sum", 0), 1000.0, 900.0))
    pairs.update(mk((1, "sum", 1), 1005.0, 950.0))
    cls = pair_level_classification(pairs)
    _expect(cls["sum"]["sign"]["verdict"] == "regime-invariant"
            and cls["sum"]["sign"]["side"] == "faster",
            "all-faster pairs: regime-invariant faster", stats)
    pairs.update(mk((1, "sum", 2), 1010.0, 1010.0 * 1.02))
    cls = pair_level_classification(pairs)
    _expect(cls["sum"]["sign"]["verdict"] == "regime-scoped"
            and cls["sum"]["sign"]["straddle"] == "within-regime",
            "both sides inside one pair level: within-regime straddle",
            stats)
    pairs = {}
    pairs.update(mk((1, "sum", 0), 1000.0, 900.0))      # fast level, faster
    pairs.update(mk((1, "sum", 1), 1300.0, 1300.0 * 1.02))  # slow, slower
    cls = pair_level_classification(pairs)
    _expect(cls["sum"]["sign"]["verdict"] == "regime-scoped"
            and cls["sum"]["sign"]["straddle"] == "by-regime",
            "each pair level one-sided, levels disagree: by-regime",
            stats)

    # -- rendering: the section never claims rule 2, names incomplete pairs
    sec = render_pair_level_section(
        {(1, "sum", 0): {"baseline": 1000.0, "variant": 900.0, "order": "A"}},
        {(1, "sum", 1): {"variant": 1150.0, "order": "B"}})
    _expect("it is not rule 2" in sec and "ANALOGUE" in sec,
            "the section names what it is not", stats)
    _expect("Incomplete pairs, named and excluded (1): run 1 sum pair 1"
            in sec, "incomplete pairs are published", stats)
    sec_via = render_pair_level_section(
        {(1, "sum", 0): {"baseline": 1000.0, "variant": 900.0, "order": "A"}},
        via="pair-level-test")
    _expect(sec_via.splitlines()[2].startswith("Published by pair-level-test: "),
            "via names the publication path that actually published", stats)


def _self_test_pair_level_corpus(stats, corpus_root):
    """Pair-level pins over the op-order cell's committed run-log: the
    machine's level structure, and its relation to the manual
    instrument's committed buckets (analyze-oporder.txt) -- where they
    agree and where the machine decides alone. Divergence is pinned, not
    bent away."""
    cell = corpus_root / "gpu-subgroup-reduce-m1max-oporder-20261023"
    pairs, incomplete = parse_run_log_pairs(
        (cell / "w32-sum-last" / "run-log.txt").read_text())
    _expect(len(pairs) == 360 and not incomplete,
            "op-order corpus: 360 complete pairs (6 runs x 3 ops x 20), "
            "0 incomplete", stats)
    cls = pair_level_classification(pairs)

    # the machine's level structure, pinned over the real corpus
    # (lo, hi, pairs, median pair ratio at 3dp) per level, fastest first
    pinned = {
        "max": [(35708, 36250, 7, 1.029), (88125, 88917, 5, 0.919),
                (107625, 111125, 104, 0.917), (128000, 128000, 1, 0.784),
                (204250, 204250, 1, 0.491), (293625, 330375, 2, 0.321)],
        "min": [(35708, 37167, 20, 1.018), (45708, 46125, 5, 0.960),
                (58500, 59875, 9, 1.009), (107208, 111167, 85, 0.920),
                (327417, 327417, 1, 0.306)],
        "sum": [(35583, 36958, 24, 1.018), (45375, 59417, 34, 0.934),
                (68625, 68625, 1, 0.836), (88417, 89625, 5, 0.906),
                (107458, 110708, 54, 0.920), (173708, 173708, 1, 0.295),
                (225250, 225250, 1, 0.444)],
    }
    for op, rows in pinned.items():
        levels = cls[op]["levels"]
        _expect(len(levels) == len(rows),
                f"{op}: machine level count pinned ({len(rows)})", stats)
        for lv, (lo, hi, cnt, med) in zip(levels, rows):
            _expect(lv["lo"] == lo and lv["hi"] == hi,
                    f"{op}: level range {lo}..{hi} pinned", stats)
            _expect(len(lv["runs"]) == cnt,
                    f"{op}: level {lo}..{hi} pair count {cnt} pinned",
                    stats)
            got = statistics.median([cls[op]["ratios"][k]
                                     for k in lv["runs"]])
            _expect(round(got, 3) == med,
                    f"{op}: level {lo}..{hi} median {med} pinned", stats)

    # the rule-2 analogue at pair granularity, pinned (and explicitly NOT
    # a rule-2 verdict: all three ops are regime-scoped at pair level
    # because single pairs spike both ways, which the per-level medians
    # carry regardless)
    sign_pins = {"max": ((7, 113, 0), "within-regime"),
                 "min": ((22, 97, 1), "within-regime"),
                 "sum": ((20, 99, 1), "within-regime")}
    for op, (counts, straddle) in sign_pins.items():
        c = cls[op]["sign"]
        _expect(c["verdict"] == "regime-scoped" and c["straddle"] == straddle,
                f"{op}: pair-level analogue verdict/straddle pinned", stats)
        _expect((c["counts"]["slower"], c["counts"]["faster"],
                 c["counts"]["even"]) == counts,
                f"{op}: pair-level analogue side counts pinned {counts}",
                stats)

    # the manual instrument's committed buckets, parsed from its own
    # committed output -- the two instruments must agree on the pair
    # population and the median wherever the manual bucket is defined
    manual = {}
    for line in (cell / "analyze-oporder.txt").read_text().splitlines():
        m = re.match(r"\| (\w+) \| (\w+) \| (\d+) \| ([\d.]+)\.\.([\d.]+) "
                     r"\| ([\d.]+) \|", line)
        if m:
            op, bucket, cnt, _lo, _hi, med = m.groups()
            manual[(op, bucket)] = (int(cnt), float(med))
    _expect(len(manual) == 8, "manual instrument: 8 bucket rows parsed "
            "(3 ops x 3 buckets minus max/middle empty)", stats)

    def in_bucket(bucket, b):
        return ((b > 80000) if bucket == "slow"
                else (40000 < b <= 80000) if bucket == "middle"
                else (0 < b <= 40000))

    for (op, bucket), (cnt, med) in sorted(manual.items()):
        sel = [(k, r) for k, r in pairs.items()
               if k[1] == op and in_bucket(bucket, r["baseline"])]
        _expect(len(sel) == cnt,
                f"{op}/{bucket}: machine pair population == manual count "
                f"({cnt})", stats)
        got = statistics.median([cls[op]["ratios"][(k[0], k[2])]
                                 for k, _ in sel]) if sel else None
        _expect(got is not None and round(got, 3) == med,
                f"{op}/{bucket}: machine median == the manual instrument's "
                f"committed median ({med})", stats)
        lv_in = [l for l in cls[op]["levels"]
                 if all(in_bucket(bucket, l["medians"][k]) for k in l["runs"])]
        if bucket == "fast" and sel:
            _expect(len(lv_in) == 1,
                    f"{op}/fast: one machine level (the manual fast bucket "
                    f"is a machine plateau)", stats)
        if bucket in ("slow", "middle") and sel:
            _expect(len(lv_in) >= 2,
                    f"{op}/{bucket}: the manual bucket POOLS what the "
                    f"machine splits ({len(lv_in)} levels) -- divergence "
                    f"pinned, not bent away", stats)


def _self_test_identity_unit(stats):
    # ---- cross-operator level identity: partition agreement ----

    # fewer than two operators refuses (there is no cross-operator
    # question)
    try:
        cross_operator_level_identity({"sum": {1: 100.0}})
        raise AssertionError("one operator must raise")
    except ValueError:
        stats["passed"] += 1

    # fewer than two runs refuses
    try:
        cross_operator_level_identity({"sum": {1: 100.0},
                                       "max": {1: 101.0}})
        raise AssertionError("one run must raise")
    except ValueError:
        stats["passed"] += 1

    # operators must cover the same run set
    try:
        cross_operator_level_identity(
            {"sum": {1: 100.0, 2: 101.0}, "max": {1: 100.0}})
        raise AssertionError("run-set mismatch must raise")
    except ValueError:
        stats["passed"] += 1

    # identical partitions -> identity holds (partitions equal refine
    # each other in both directions)
    ident = cross_operator_level_identity(
        {"sum": {1: 100.0, 2: 101.0, 3: 300.0, 4: 305.0},
         "max": {1: 100.5, 2: 101.5, 3: 301.0, 4: 306.0}})
    _expect(ident["verdict"] == "identity-holds" and not ident["divergent"],
            "identical partitions: identity holds", stats)
    _expect(("sum", "max") in ident["refinements"]
            and ("max", "sum") in ident["refinements"],
            "equal partitions refine each other in both directions", stats)

    # one operator splits a pair the others pool -> identity refuted,
    # the divergent pairs NAMED with every operator's relation
    ident = cross_operator_level_identity(
        {"sum": {1: 100.0, 2: 101.0, 3: 102.0},
         "max": {1: 100.0, 2: 101.0, 3: 300.0}})
    _expect(ident["verdict"] == "identity-refuted"
            and ident["divergent"] == [(1, 3, {"sum": "same-level",
                                               "max": "split-level"}),
                                       (2, 3, {"sum": "same-level",
                                               "max": "split-level"})],
            "the divergent pairs are named with each operator's relation",
            stats)

    # the GAP-1.15 boundary decides identity exactly as it decides a
    # level: 100 -> 115 merges in both operators (holds); one operator
    # at 115.01 splits (refuted)
    ident = cross_operator_level_identity(
        {"sum": {1: 100.0, 2: 115.0}, "max": {1: 101.0, 2: 116.0}})
    _expect(ident["verdict"] == "identity-holds",
            "exactly 1.15x merges in both operators: identity holds",
            stats)
    ident = cross_operator_level_identity(
        {"sum": {1: 100.0, 2: 115.0}, "max": {1: 101.0, 2: 116.17}})
    _expect(ident["verdict"] == "identity-refuted",
            "one operator just over 1.15x splits: identity refuted", stats)

    # refinement shapes: strict refinement
    ident = cross_operator_level_identity(
        {"sum": {1: 100.0, 2: 101.0, 3: 102.0},
         "max": {1: 100.0, 2: 101.0, 3: 300.0}})
    _expect(("max", "sum") in ident["refinements"]
            and ("sum", "max") not in ident["refinements"],
            "strict refinement: max's partition refines sum's", stats)

    # refinement shapes: cross-cutting (neither refines) -- sum pools
    # {1,2} where max splits them, max pools {2,3} where sum splits them
    ident = cross_operator_level_identity(
        {"sum": {1: 100.0, 2: 101.0, 3: 300.0, 4: 301.0},
         "max": {1: 100.0, 2: 200.0, 3: 201.0, 4: 302.0}})
    _expect(("sum", "max") not in ident["refinements"]
            and ("max", "sum") not in ident["refinements"]
            and len(ident["divergent"]) == 3,
            "cross-cutting partitions refine in neither direction (3 "
            "divergent pairs)", stats)

    # rendering: the refuted section names the pairs, the refinement
    # shape, and carries the rule-4 disclaimer
    sec = render_identity_section(
        {"sum": {1: 100.0, 2: 101.0, 3: 102.0},
         "max": {1: 100.0, 2: 101.0, 3: 300.0}})
    _expect("identity refuted" in sec and "1 vs 3" in sec
            and "same-level" in sec and "split-level" in sec,
            "the refuted section names the divergent pairs", stats)
    _expect("changes no rule-2 verdict" in sec and "rule 4" in sec,
            "the section carries the rule-4 disclaimer", stats)
    _expect("max's partition refines sum's" in sec,
            "the refinement shape is published", stats)

    # rendering: the holds section licenses cross-operator naming
    sec_ok = render_identity_section(
        {"sum": {1: 100.0, 2: 101.0}, "max": {1: 100.5, 2: 101.5}})
    _expect("identity holds" in sec_ok
            and "may name one level across these operators" in sec_ok,
            "the holds section licenses cross-operator naming", stats)

    # via names the publication path that actually published
    sec_via = render_identity_section(
        {"sum": {1: 100.0, 2: 101.0}, "max": {1: 100.5, 2: 101.5}},
        via="identity-test")
    _expect(sec_via.splitlines()[2].startswith("Published by identity-test: "),
            "via names the publication path that actually published", stats)

    # render_section publishes the identity section for >= 2 operators
    # and stays rule-1-only for one
    out = render_section({"sum": {1: 100.0, 2: 101.0},
                          "max": {1: 100.5, 2: 300.0}})
    _expect("## Cross-operator level identity" in out
            and "identity refuted" in out,
            "render_section carries the identity section for two "
            "operators", stats)
    out1 = render_section({"sum": {1: 100.0, 2: 101.0}})
    _expect("## Cross-operator level identity" not in out1,
            "render_section omits the identity section for one operator",
            stats)

    # the single-record parsers round-trip through a record carrying
    # the identity section (its tables match none of their row shapes) --
    # the record stays loadable as a comparison cell
    rows = ("| sum | baseline | 2 | 250.0 | 100.0, 400.0 |\n"
            "| max | baseline | 2 | 255.0 | 105.0, 405.0 |\n"
            "| sum | 1.200, 1.186 | 1.193 |\n"
            "| max | 1.195, 1.183 | 1.189 |\n")
    body = rows + render_section(
        {"sum": {1: 100.0, 2: 400.0}, "max": {1: 105.0, 2: 405.0}},
        ratios={"sum": [1.200, 1.186], "max": [1.195, 1.183]})
    _expect(parse_summary_per_run_baseline(body)
            == {"sum": {1: 100.0, 2: 400.0}, "max": {1: 105.0, 2: 405.0}},
            "baseline rows round-trip through a record carrying the "
            "identity section", stats)
    _expect(parse_summary_per_run_ratios(body)
            == {"sum": [1.200, 1.186], "max": [1.195, 1.183]},
            "ratio rows round-trip through a record carrying the "
            "identity section", stats)


def _self_test_identity_corpus(stats, corpus_root):
    """Cross-operator level identity over the committed corpus: every
    record with at least two operators gets its verdict (printed, the
    GAP-1.15 ethos), the structural claim is asserted over every
    refuted record, and the machine's verdicts are pinned per named
    record -- including next to the record prose they license or
    refute. No prose decided these partitions' cross-operator relation;
    the pins are the machine's own verdicts over committed numbers and
    must not drift silently. Nothing is re-measured here: every number
    is parsed from committed summary.md text.
    """
    records = []
    for s in sorted(corpus_root.rglob("summary.md")):
        try:
            per_op = parse_summary_per_run_baseline(s.read_text())
        except ValueError:
            continue
        if len(per_op) < 2:
            continue
        rel = str(s.relative_to(corpus_root)).replace("/summary.md", "")
        records.append((rel, per_op))
    # a floor, not an exact pin: the corpus grows with every new record
    _expect(len(records) >= 28,
            f"multi-operator corpus floor 28 ({len(records)})", stats)
    holds, refuted = [], []
    strict_edge_records = 0
    multi_level_holds = 0
    for rel, per_op in records:
        _expect(len({frozenset(m) for m in per_op.values()}) == 1,
                f"{rel}: operators share one run set", stats)
        ident = cross_operator_level_identity(per_op)
        if ident["verdict"] == "identity-holds":
            holds.append(rel)
            if any(len(lvs) > 1 for lvs in ident["levels"].values()):
                multi_level_holds += 1
        else:
            refuted.append(rel)
            refin = set(ident["refinements"])
            if any((o1, o2) in refin and (o2, o1) not in refin
                   for o1 in ident["ops"] for o2 in ident["ops"]
                   if o1 != o2):
                strict_edge_records += 1
    # floors over the 2026-10-23 corpus; the exact tallies are printed
    # and quoted by docs/evidence/gpu/cross-operator-level-identity-
    # 20261023.txt
    _expect(len(holds) >= 9 and len(refuted) >= 19,
            f"corpus tally floors: >= 9 holds / >= 19 refuted (got "
            f"{len(holds)}/{len(refuted)})", stats)
    def _ident(rel):
        return cross_operator_level_identity(
            parse_summary_per_run_baseline(
                (corpus_root / rel / "summary.md").read_text()))

    # THE 2026-10-25 DECISION (docs/evidence/gpu/cross-cutting-only-
    # decision-20261025.txt; ADR-0360 Amendment 2026-10-25):
    # cross-cutting-only is a LEGAL refuted shape -- identity refutes on
    # partition disagreement alone (any divergent run pair), and the
    # refinement relation is the disagreement's published SHAPE (equal /
    # one refines the other / cross-cutting), never a legality
    # condition. The 2026-10-23 structural claim ("every refuted record
    # has a strict refinement edge", asserted over every refuted
    # record) is SUPERSEDED: its dated 19/19 tally stands as history,
    # and the corpus's first counterexample surfaced exactly as that
    # pin's comment prescribed ("would fail this pin and surface
    # instead of hiding"). What the pin asserts afterwards, in the
    # :sum-refines-:max set pin's own idiom: the refuted records with
    # NO strict refinement edge are EXACTLY the named set below. A
    # future crossing-only record fails this pin on purpose and must
    # enter the set with its own story -- the surfacing mechanism is
    # preserved where it matters (crossing-only is legal but never
    # silent), not dropped.
    #
    # the 2026-10-25 cross-day W = 32 replica -- the corpus's FIRST
    # crossing-only refutation, and (every pair cross-cutting) its
    # first CROSS-CUTTING-ONLY one: 5 of 15 run pairs diverge, no
    # refinement edge in either direction. Levels (GAP-1.15,
    # fastest-first): max [[5], [1, 2], [4], [3, 6]], min [[5, 6],
    # [4], [1, 2], [3]], sum [[1], [2, 4], [3, 5, 6]]. Its story is
    # its own record's (crossday-20261025/w32 NOTES: the instrument's
    # first calendar-stamped session; sign reproduces strictly against
    # the 2026-10-23 flip basis). Pinned per named record, as every
    # machine verdict over committed numbers is.
    #
    # the 2026-10-25 cross-day shape-2 W = 32 replica
    # (crossday-20261025/w32-shape2) -- the corpus's SECOND crossing-only
    # refutation, surfaced by this pin failing on purpose exactly as the
    # idiom prescribes: 10 of 15 run pairs diverge and NO one-way
    # refinement edge exists -- but its shape DIFFERS from the first
    # one's: max and min are EQUAL partitions (each refines the other,
    # neither strictly), and both cross-cut sum. So it is crossing-only
    # without being cross-cutting-only (the first record's every-pair-
    # cross-cutting shape). Levels (GAP-1.15, fastest-first): max
    # [[5, 6], [4], [3], [1, 2]], min [[5, 6], [4], [3], [1, 2]], sum
    # [[1], [2, 3, 4, 5, 6]]. Its story is its own record's
    # (crossday-20261025/w32-shape2 NOTES: sign reproduces strictly
    # against the 2026-10-24 shape-2 flip basis, 18/18). Pinned per
    # named record, as every machine verdict over committed numbers is.
    #
    # the 2026-10-25 cross-day shape-2 W = 128 replica
    # (crossday-20261025/w128-shape2) -- the corpus's THIRD crossing-only
    # refutation, surfaced by this pin failing on purpose exactly as the
    # idiom prescribes: 4 of 15 run pairs diverge and NO one-way
    # refinement edge exists. Its shape returns to the FIRST record's
    # cross-cutting-only one (every operator pair cross-cutting,
    # refinements empty) -- the corpus's SECOND cross-cutting-only
    # record -- at a four-level regime mix at every operator, and the
    # fewest divergent run pairs of the three named records (4 of 15).
    # Levels (GAP-1.15, fastest-first): max [[6], [4, 5], [3], [1, 2]],
    # min [[5, 6], [4], [3], [1, 2]], sum [[5], [3], [6], [1, 2, 4]].
    # Its story is its own record's (crossday-20261025/w128-shape2
    # NOTES: sign reproduces strictly against the 2026-10-24 shape-2
    # flip basis, 18/18). Pinned per named record, as every machine
    # verdict over committed numbers is.
    cdw32 = _ident("gpu-simdgroup-reduce-m1max-crossday-20261025/w32")
    _expect(cdw32["verdict"] == "identity-refuted"
            and len(cdw32["divergent"]) == 5
            and [lv["runs"] for lv in cdw32["levels"]["max"]]
                == [[5], [1, 2], [4], [3, 6]]
            and [lv["runs"] for lv in cdw32["levels"]["min"]]
                == [[5, 6], [4], [1, 2], [3]]
            and [lv["runs"] for lv in cdw32["levels"]["sum"]]
                == [[1], [2, 4], [3, 5, 6]]
            and cdw32["refinements"] == [],
            "cross-day w32 (2026-10-25): identity refuted (5/15) with "
            "NO refinement edge -- the corpus's first cross-cutting-"
            "only refutation, decided a legal refuted shape "
            "2026-10-25", stats)
    cdw32s = _ident("gpu-simdgroup-reduce-m1max-crossday-20261025/"
                    "w32-shape2")
    _expect(cdw32s["verdict"] == "identity-refuted"
            and len(cdw32s["divergent"]) == 10
            and [lv["runs"] for lv in cdw32s["levels"]["max"]]
                == [[5, 6], [4], [3], [1, 2]]
            and [lv["runs"] for lv in cdw32s["levels"]["min"]]
                == [[5, 6], [4], [3], [1, 2]]
            and [lv["runs"] for lv in cdw32s["levels"]["sum"]]
                == [[1], [2, 3, 4, 5, 6]]
            and len(cdw32s["refinements"]) == 2
            and set(cdw32s["refinements"]) == {("max", "min"),
                                               ("min", "max")},
            "cross-day w32-shape2 (2026-10-25): identity refuted "
            "(10/15) with only the max=min mutual (non-strict) "
            "refinement and both cross-cutting sum -- the corpus's "
            "second crossing-only refutation, a DIFFERENT shape from "
            "the first one's", stats)
    cdw128s = _ident("gpu-simdgroup-reduce-m1max-crossday-20261025/"
                     "w128-shape2")
    _expect(cdw128s["verdict"] == "identity-refuted"
            and len(cdw128s["divergent"]) == 4
            and [lv["runs"] for lv in cdw128s["levels"]["max"]]
                == [[6], [4, 5], [3], [1, 2]]
            and [lv["runs"] for lv in cdw128s["levels"]["min"]]
                == [[5, 6], [4], [3], [1, 2]]
            and [lv["runs"] for lv in cdw128s["levels"]["sum"]]
                == [[5], [3], [6], [1, 2, 4]]
            and cdw128s["refinements"] == [],
            "cross-day w128-shape2 (2026-10-25): identity refuted "
            "(4/15) with NO refinement edge -- the corpus's third "
            "crossing-only refutation and second cross-cutting-only "
            "one (every operator pair cross-cutting), at four observed "
            "levels per operator", stats)

    crossing_only = [rel for rel, per_op in records
                     if (lambda i: i["verdict"] == "identity-refuted"
                         and not any((o1, o2) in i["refinements"]
                                     and (o2, o1) not in i["refinements"]
                                     for o1 in i["ops"] for o2 in i["ops"]
                                     if o1 != o2))(
                             cross_operator_level_identity(per_op))]
    _expect(crossing_only == ["gpu-simdgroup-reduce-m1max-crossday-"
                              "20261025/w128-shape2",
                              "gpu-simdgroup-reduce-m1max-crossday-"
                              "20261025/w32",
                              "gpu-simdgroup-reduce-m1max-crossday-"
                              "20261025/w32-shape2"],
            f"the corpus's crossing-only refuted records are exactly "
            f"the named set (the 2026-10-25 cross-day shape-1 W = 32 "
            f"record, the 2026-10-25 cross-day shape-2 W = 32 record "
            f"and the 2026-10-25 cross-day shape-2 W = 128 record); a "
            f"future crossing-only record fails this "
            f"pin on purpose ({crossing_only})", stats)

    # the closing cell (shape2-resweep w512): its own prose names the
    # regime split ACROSS operators ("this session's run 3 sat
    # fast/intermediate"; "fast-level :max 1.026 / :min 1.021-1.026 vs
    # slow ~0.92") -- the machine LICENSES that cross-operator naming:
    # all three partitions agree on {3} / {1,2,4,5,6}
    closing = _ident("gpu-subgroup-reduce-m1max-shape2-resweep-20261023/w512")
    _expect(closing["verdict"] == "identity-holds"
            and all([lv["runs"] for lv in closing["levels"][op]]
                    == [[3], [1, 2, 4, 5, 6]] for op in closing["ops"]),
            "closing cell w512: identity holds -- the three operators' "
            "partitions agree on {3} / {1,2,4,5,6}, licensing the "
            "record's cross-operator fast/slow prose", stats)

    # wsweep-low w32: the record's "runs 4/6 one fast regime" prose is
    # :max's partition; the machine REFUTES cross-operator identity
    # here -- :min's partition is [3,4,5,6]/[2]/[1], :sum pools all
    # six, and :max and :min cross-cut. The cross-operator "the fast
    # regime" naming is NOT mechanically licenseable in this record.
    w32 = _ident("gpu-subgroup-reduce-m1max-wsweep-low-20261023/w32")
    _expect(w32["verdict"] == "identity-refuted"
            and len(w32["divergent"]) == 13
            and [lv["runs"] for lv in w32["levels"]["max"]]
                == [[4, 6], [1, 2, 3, 5]]
            and [lv["runs"] for lv in w32["levels"]["min"]]
                == [[3, 4, 5, 6], [2], [1]]
            and [lv["runs"] for lv in w32["levels"]["sum"]]
                == [[1, 2, 3, 4, 5, 6]]
            and ("max", "min") not in w32["refinements"]
            and ("min", "max") not in w32["refinements"],
            "wsweep-low w32: identity refuted (13 divergent pairs) -- "
            "the 'runs 4/6 fast regime' naming is :max's partition "
            "alone", stats)

    # the op-order cell: one of the corpus's TWO :sum-refines-:max
    # records (the second arrived 2026-10-24 with the shape-2 W = 1024
    # record) and still the only one where :sum ran LAST -- the
    # within-run ramping the pair-level slice named shows up at run
    # level in the operator that ran last. The 2026-10-23 "the ONLY
    # record where :sum's partition is the finest" reading is
    # SUPERSEDED; the corpus-wide fact is the set pinned below.
    oo = _ident("gpu-subgroup-reduce-m1max-oporder-20261023/w32-sum-last")
    _expect(oo["verdict"] == "identity-refuted"
            and len(oo["divergent"]) == 12
            and [lv["runs"] for lv in oo["levels"]["max"]]
                == [[1, 2, 3, 4, 5, 6]]
            and ("sum", "max") in oo["refinements"]
            and ("sum", "min") in oo["refinements"]
            and ("max", "sum") not in oo["refinements"],
            "op-order cell: identity refuted; :sum -- the operator that "
            "ran LAST -- refines both others (:max pools all six)", stats)

    # the op-order RE-SESSION (12 fresh processes, 2026-10-24, the
    # W = 1024 fast-level capture session): the same ramp shape as the
    # 6-run op-order cell's at 12 runs -- :sum, the operator that ran
    # LAST, reached the fastest observed level in runs 8..12 while
    # :max's FIRST block sat at the slow level in every one of the
    # twelve (in runs 8 and 12 :min's second block was still slow when
    # :sum's third block was already fast -- the ramp onset moves
    # within a process), so :sum's partition refines :max's and :min
    # and :sum cross-cut. THIRD member of the corpus's
    # :sum-refines-:max set (below). Levels fastest-first (GAP-1.15):
    # sum [[8..12],[7],[6],[1..5]], min [[9,10,11],[7],[6],
    # [1,2,3,4,5,8,12]], max one level.
    oor = _ident("gpu-subgroup-reduce-m1max-oporder-resweep-20261024/"
                 "w1024-sum-last")
    _expect(oor["verdict"] == "identity-refuted"
            and len(oor["divergent"]) == 52
            and [lv["runs"] for lv in oor["levels"]["max"]]
                == [list(range(1, 13))]
            and [lv["runs"] for lv in oor["levels"]["sum"]]
                == [[8, 9, 10, 11, 12], [7], [6], [1, 2, 3, 4, 5]]
            and [lv["runs"] for lv in oor["levels"]["min"]]
                == [[9, 10, 11], [7], [6], [1, 2, 3, 4, 5, 8, 12]]
            and ("sum", "max") in oor["refinements"]
            and ("min", "max") in oor["refinements"]
            and ("max", "sum") not in oor["refinements"]
            and ("max", "min") not in oor["refinements"]
            and ("sum", "min") not in oor["refinements"]
            and ("min", "sum") not in oor["refinements"],
            "op-order re-session: identity refuted; :sum -- the "
            "operator that ran LAST -- refines :max (:max pools all "
            "twelve), :min and :sum cross-cut (ramp onset moves within "
            "a process)", stats)

    # shape2 w32: the record's own prose already knew the operators
    # disagreed ("all six :sum runs sat at the slow level" vs :max's
    # three named levels); the machine reproduces exactly that split
    s2 = _ident("gpu-subgroup-reduce-m1max-shape2-20261023/w32")
    _expect(s2["verdict"] == "identity-refuted"
            and len(s2["divergent"]) == 12
            and [lv["runs"] for lv in s2["levels"]["sum"]]
                == [[1, 2, 3, 4, 5, 6]]
            and [lv["runs"] for lv in s2["levels"]["max"]]
                == [[4], [3], [1, 2, 5, 6]],
            "shape2 w32: identity refuted -- :sum one level vs :max's "
            "three prose-named levels", stats)

    # the corpus's :sum-refines-:max set, stated as a corpus-wide fact.
    # THREE records carry the strict edge as of 2026-10-24 (the third
    # arrived with the op-order RE-SESSION's 12-run capture session,
    # whose own pin above is its story): the op-order
    # cell (:sum ran LAST -- the dispatch-position ramping story) and
    # the shape-2 W = 1024 record
    # (gpu-simdgroup-reduce-m1max-shape2-20261024/w1024, added
    # 2026-10-24 by the W = 1024 measurement slice -- which ran no
    # self-test over its evidence addition, so this pin's red went
    # unnoticed until the 2026-10-24 corpus-pin fix slice). At that
    # record :sum ran FIRST and its refinement is the single-run
    # clock-level split (sum [[2], [1, 3, 4, 5, 6]] against :max/:min
    # pooling all six), so refinement does NOT track the last-
    # dispatched operator. The 2026-10-23 claim "the op-order cell is
    # the corpus's only record where :sum refines :max" is SUPERSEDED
    # by this set, not silently dropped. A future record entering this
    # set fails this pin on purpose: the corpus fact must be re-stated
    # with its own story, never drift silently. The re-session's entry
    # (2026-10-24, this tick) is exactly that re-statement: its story
    # is the fast-level capture -- :sum at the LAST block reached the
    # fastest observed rule-1 level while :max's first block never
    # left the slow level, so its refinement edge is the block-
    # ordered clock ramp, not an operator property.
    finest_sum = [rel for rel, per_op in records
                  if (lambda i: ("sum", "max") in i["refinements"]
                      and ("max", "sum") not in i["refinements"])(
                          cross_operator_level_identity(per_op))]
    _expect(finest_sum == ["gpu-simdgroup-reduce-m1max-shape2-20261024/"
                           "w1024",
                           "gpu-subgroup-reduce-m1max-oporder-20261023/"
                           "w32-sum-last",
                           "gpu-subgroup-reduce-m1max-oporder-resweep-"
                           "20261024/w1024-sum-last"],
            f"the corpus's :sum-refines-:max records are the shape-2 "
            f"W = 1024 record (:sum FIRST, run-2 clock split), the "
            f"op-order cell (:sum LAST, dispatch ramping) and the "
            f"op-order re-session (:sum LAST, 12 runs, the fast-level "
            f"capture) ({finest_sum})",
            stats)

    print(f"cross-operator level identity: {len(records)} multi-operator "
          f"records -- {len(holds)} identity-holds "
          f"({multi_level_holds} of them multi-level), {len(refuted)} "
          f"identity-refuted ({strict_edge_records} with refinement "
          f"structure, {len(crossing_only)} crossing-only: the named "
          f"set pin's members)")
    print("per-record verdicts (printed, GAP-1.15 ethos):")
    for rel, per_op in records:
        ident = cross_operator_level_identity(per_op)
        nlv = {op: len(lvs) for op, lvs in sorted(ident["levels"].items())}
        print(f"  {rel}: {ident['verdict']} "
              f"({len(ident['divergent'])} divergent pairs; levels "
              + ", ".join(f"{op} {n}" for op, n in nlv.items()) + ")")


def _self_test_pair_identity_unit(stats):
    # ---- pair-level cross-operator identity: partition agreement at
    # ---- (run, pair) granularity ----

    # fewer than two operators refuses (there is no cross-operator
    # question)
    try:
        cross_operator_pair_level_identity({"sum": {(1, 0): 100.0}})
        raise AssertionError("one operator must raise")
    except ValueError:
        stats["passed"] += 1

    # fewer than two SHARED pair keys refuses (there is no agreement
    # to test)
    try:
        cross_operator_pair_level_identity(
            {"sum": {(1, 0): 100.0, (1, 1): 101.0},
             "max": {(1, 0): 100.0, (2, 0): 101.0}})
        raise AssertionError("one shared key must raise")
    except ValueError:
        stats["passed"] += 1

    # operators' key sets may DISAGREE (a pair can lose an arm in one
    # operator's block): that does NOT refuse -- the incomplete keys
    # are NAMED in "excluded" and the agreement test runs on the
    # shared ground set only
    ident = cross_operator_pair_level_identity(
        {"sum": {(1, 0): 100.0, (1, 1): 101.0, (1, 2): 500.0},
         "max": {(1, 0): 100.0, (1, 1): 101.0}})
    _expect(ident["excluded"] == {(1, 2): ["sum"]},
            "a key completed by some operators only is NAMED in "
            "excluded, never silently dropped", stats)
    _expect(ident["verdict"] == "identity-holds" and ident["keys"]
            == [(1, 0), (1, 1)],
            "the agreement test runs on the shared ground set only",
            stats)

    # identical pair partitions -> identity holds (partitions refine
    # each other in both directions)
    ident = cross_operator_pair_level_identity(
        {"sum": {(1, 0): 100.0, (1, 1): 101.0,
                 (2, 0): 300.0, (2, 1): 305.0},
         "max": {(1, 0): 100.5, (1, 1): 101.5,
                 (2, 0): 301.0, (2, 1): 306.0}})
    _expect(ident["verdict"] == "identity-holds" and not ident["divergent"],
            "identical pair partitions: identity holds", stats)
    _expect(("sum", "max") in ident["refinements"]
            and ("max", "sum") in ident["refinements"],
            "equal pair partitions refine each other in both directions",
            stats)

    # one operator splits a pair the others pool -> identity refuted,
    # the divergent key pairs NAMED with every operator's relation
    ident = cross_operator_pair_level_identity(
        {"sum": {(1, 0): 100.0, (1, 1): 101.0, (1, 2): 102.0},
         "max": {(1, 0): 100.0, (1, 1): 101.0, (1, 2): 300.0}})
    _expect(ident["verdict"] == "identity-refuted"
            and ident["divergent"] == [((1, 0), (1, 2),
                                        {"sum": "same-level",
                                         "max": "split-level"}),
                                       ((1, 1), (1, 2),
                                        {"sum": "same-level",
                                         "max": "split-level"})],
            "the divergent key pairs are named with each operator's "
            "relation", stats)

    # the GAP-1.15 boundary decides pair identity exactly as it
    # decides a pair level: 100 -> 115 merges in both operators
    # (holds); one operator just over 1.15x splits (refuted)
    ident = cross_operator_pair_level_identity(
        {"sum": {(1, 0): 100.0, (1, 1): 115.0},
         "max": {(1, 0): 101.0, (1, 1): 116.0}})
    _expect(ident["verdict"] == "identity-holds",
            "exactly 1.15x merges in both operators: pair identity "
            "holds", stats)
    ident = cross_operator_pair_level_identity(
        {"sum": {(1, 0): 100.0, (1, 1): 115.0},
         "max": {(1, 0): 101.0, (1, 1): 116.17}})
    _expect(ident["verdict"] == "identity-refuted",
            "one operator just over 1.15x splits: pair identity "
            "refuted", stats)

    # refinement shapes: strict refinement
    ident = cross_operator_pair_level_identity(
        {"sum": {(1, 0): 100.0, (1, 1): 101.0, (1, 2): 102.0},
         "max": {(1, 0): 100.0, (1, 1): 101.0, (1, 2): 300.0}})
    _expect(("max", "sum") in ident["refinements"]
            and ("sum", "max") not in ident["refinements"],
            "strict refinement at pair granularity: max's partition "
            "refines sum's", stats)

    # refinement shapes: cross-cutting (neither refines) -- sum pools
    # {(1,0),(1,1)} where max splits them, max pools {(1,1),(1,2)}
    # where sum splits them
    ident = cross_operator_pair_level_identity(
        {"sum": {(1, 0): 100.0, (1, 1): 101.0,
                 (1, 2): 300.0, (1, 3): 301.0},
         "max": {(1, 0): 100.0, (1, 1): 200.0,
                 (1, 2): 201.0, (1, 3): 302.0}})
    _expect(("sum", "max") not in ident["refinements"]
            and ("max", "sum") not in ident["refinements"]
            and len(ident["divergent"]) == 3,
            "cross-cutting pair partitions refine in neither "
            "direction (3 divergent key pairs)", stats)

    # rendering: divergent key pairs are published by CLASS, every
    # pair in exactly one class, and the class counts SUM to the
    # verdict's total -- nothing is silently dropped (the contract
    # render_pair_identity_section states)
    sec = render_pair_identity_section(
        {"sum": {(1, 0): 100.0, (1, 1): 101.0,
                 (1, 2): 300.0, (1, 3): 301.0},
         "max": {(1, 0): 100.0, (1, 1): 200.0,
                 (1, 2): 201.0, (1, 3): 302.0}})
    _expect("identity refuted" in sec and "3 of 6 key pairs" in sec,
            "the refuted section names the divergent total over the "
            "key-pair ground set", stats)
    rows = re.findall(
        r"^\| ((?:same-level|split-level)(?: \| (?:same-level|split-level))*)"
        r" \| (\d+) \| ", sec, re.M)
    _expect(rows and sum(int(n) for _sig, n in rows) == 3,
            f"divergent key pairs published by class; the class counts "
            f"sum to the verdict's total ({sum(int(n) for _s, n in rows)})"
            f" -- nothing silently dropped", stats)
    _expect(("split-level | same-level", "2") in rows
            and ("same-level | split-level", "1") in rows,
            "each divergent class publishes its own count and "
            "operator relations", stats)
    _expect("run 1 pair 0 vs run 1 pair 1" in sec,
            "the class examples name real divergent key pairs", stats)

    # rendering: the refuted section carries the refinement shape and
    # the rule-4 disclaimer
    _expect("cross-cut (neither partition refines the other)" in sec,
            "the partition relation is published", stats)
    _expect("changes no rule-2 verdict" in sec and "rule 4" in sec,
            "the section carries the rule-4 disclaimer", stats)

    # rendering: the holds section licenses cross-operator pair naming
    sec_ok = render_pair_identity_section(
        {"sum": {(1, 0): 100.0, (1, 1): 115.0},
         "max": {(1, 0): 101.0, (1, 1): 116.0}})
    _expect("identity holds" in sec_ok
            and "may name one pair level across these operators" in sec_ok,
            "the holds section licenses cross-operator pair naming",
            stats)

    # rendering: excluded keys are NAMED in the section
    sec_ex = render_pair_identity_section(
        {"sum": {(1, 0): 100.0, (1, 1): 101.0, (1, 2): 500.0},
         "max": {(1, 0): 100.0, (1, 1): 101.0}})
    _expect("Excluded keys, named and not compared (1;" in sec_ex
            and "run 1 pair 2 (sum)" in sec_ex,
            "excluded keys are named in the section, never dropped",
            stats)

    # via names the publication path that actually published
    sec_via = render_pair_identity_section(
        {"sum": {(1, 0): 100.0, (1, 1): 101.0},
         "max": {(1, 0): 100.5, (1, 1): 101.5}},
        via="pair-identity-test")
    _expect(sec_via.splitlines()[2].startswith(
                "Published by pair-identity-test: "),
            "via names the publication path that actually published",
            stats)

    # render_pair_level_section (the --pairs output) carries the pair
    # identity section for >= 2 operators and omits it for one
    two_ops = {(1, "sum", 0): {"baseline": 100.0, "variant": 90.0,
                               "order": "A"},
               (1, "sum", 1): {"baseline": 300.0, "variant": 290.0,
                               "order": "B"},
               (1, "max", 0): {"baseline": 101.0, "variant": 91.0,
                               "order": "A"},
               (1, "max", 1): {"baseline": 301.0, "variant": 291.0,
                               "order": "B"}}
    out = render_pair_level_section(two_ops)
    _expect("## Pair-level cross-operator identity" in out
            and "identity holds" in out,
            "the --pairs output carries the pair identity section for "
            "two operators", stats)
    out1 = render_pair_level_section(
        {(1, "sum", 0): {"baseline": 100.0, "variant": 90.0,
                         "order": "A"}})
    _expect("## Pair-level cross-operator identity" not in out1,
            "the --pairs output omits the pair identity section for "
            "one operator", stats)


def _self_test_wgsl_unit(stats):
    # ---- the WGSL wall-clock channel's rule-1 publication ----
    # Synthetic measure-log lines in the 2026-10-25 format's `time` shape
    # (the classification reads the log's PRINTED per-run medians, so the
    # published section re-derives from the carrier text exactly).
    log = "\n".join([
        "time n=1048576 w=32 op=sum arm=subgroup "
        "single_median_ms=0.5100 single_rounds=11 "
        "batch32_median_ms=0.0700 batch32_rounds=7",
        "time n=1048576 w=32 op=sum arm=baseline "
        "single_median_ms=0.5000 single_rounds=11 "
        "batch32_median_ms=0.0638 batch32_rounds=7",
        "time n=1048576 w=64 op=sum arm=baseline "
        "single_median_ms=0.5200 single_rounds=11 "
        "batch32_median_ms=0.0600 batch32_rounds=7",
        "time n=1048576 w=64 op=sum arm=subgroup "
        "single_median_ms=0.5050 single_rounds=11 "
        "batch32_median_ms=0.0610 batch32_rounds=7",
        "time n=1048576 w=128 op=sum arm=baseline "
        "single_median_ms=0.8000 single_rounds=11 "
        "batch32_median_ms=0.0900 batch32_rounds=7",
        "time n=1048576 w=128 op=sum arm=subgroup "
        "single_median_ms=0.8100 single_rounds=11 "
        "batch32_median_ms=0.0910 batch32_rounds=7",
    ])
    parsed = parse_wgsl_measure_log(log)
    _expect(parsed["single"]["sum"][(1048576, 32)]["baseline"] == 0.5
            and parsed["single"]["sum"][(1048576, 32)]["subgroup"] == 0.51,
            "wgsl parse: per-arm per-run medians from the time line", stats)
    _expect(parsed["batch32"]["sum"][(1048576, 128)]["baseline"] == 0.09,
            "wgsl parse: batch32 is its own metric", stats)
    _expect(set(parsed["single"]["sum"]) == {(1048576, 32), (1048576, 64),
                                             (1048576, 128)},
            "wgsl parse: the run identity is (n, W) -- one cell-arm "
            "sampling block", stats)

    # duplicate blocks refuse (a measurement error, not a merge candidate)
    try:
        parse_wgsl_measure_log(log + "\n" + log.splitlines()[0])
        raise AssertionError("duplicate wgsl time line must raise")
    except ValueError:
        stats["passed"] += 1

    # a log with no time lines refuses
    try:
        parse_wgsl_measure_log("check n=1 w=32 op=sum arm=baseline ok=1\n")
        raise AssertionError("wgsl log with no time lines must raise")
    except ValueError:
        stats["passed"] += 1

    out = render_wgsl_rule1_section(parsed)
    # the metric is NAMED BY THE CHANNEL: host-ms, never gpu-ns
    _expect("host wall-clock submit->completion" in out
            and "host-ms range" in out and "gpu-ns" not in out,
            "wgsl section names the channel's own metric, not gpu-ns",
            stats)
    _expect("## Regime classification (claim protocol rule 1, "
            "WGSL wall-clock channel)" in out,
            "wgsl section title", stats)
    _expect("### metric: single -- host wall-clock submit->completion, "
            "milliseconds (one dispatch per queue submit; the "
            "performance.now bracket submit -> onSubmittedWorkDone)" in out
            and "### metric: batch32" in out,
            "wgsl section keeps single and batch32 apart with each "
            "metric's own name", stats)

    # single metric: 0.5000/0.5200 merge at GAP-1.15, 0.8000 splits
    single_part = out.split("### metric: batch32")[0]
    rows = [l for l in single_part.splitlines()
            if l.startswith("| sum |") and "fastest observed" in l]
    _expect(rows == ["| sum | 1 (fastest observed) | 0.5000..0.5200 | "
                     "n=1048576 W=32 (0.5000), n=1048576 W=64 (0.5200) |"],
            "wgsl single metric: the fastest level merges W = 32/64",
            stats)
    rows = sorted(l for l in out.splitlines()
                  if l.startswith("| sum |") and "slowest observed" in l)
    _expect(rows == ["| sum | 2 (slowest observed) | 0.0900 | "
                     "n=1048576 W=128 (0.0900) |",
                     "| sum | 2 (slowest observed) | 0.8000 | "
                     "n=1048576 W=128 (0.8000) |"],
            "wgsl: each metric clusters only its own runs -- the two "
            "slowest rows carry their own metric's values", stats)
    _expect("| sum | n=1048576 W=32 | 0.5000 |" in out.splitlines(),
            "wgsl rule 1's first publication: per-run baseline medians",
            stats)

    # one run -> one level, named
    out1 = render_wgsl_rule1_section(parse_wgsl_measure_log(
        "time n=1 w=32 op=max arm=baseline single_median_ms=0.4000 "
        "single_rounds=11 batch32_median_ms=0.0500 batch32_rounds=7\n"))
    _expect("1 (the only observed level)" in out1,
            "wgsl single run: degenerate one level, named", stats)

    # a block with no baseline arm sample is NAMED, never silently dropped
    outm = render_wgsl_rule1_section(parse_wgsl_measure_log(
        "time n=1 w=32 op=min arm=subgroup single_median_ms=0.4000 "
        "single_rounds=11 batch32_median_ms=0.0500 batch32_rounds=7\n"
        "time n=1 w=64 op=min arm=baseline single_median_ms=0.4100 "
        "single_rounds=11 batch32_median_ms=0.0510 batch32_rounds=7\n"))
    _expect("Named and excluded" in outm and "min n=1 W=32" in outm,
            "wgsl: the baseline-less block is named and excluded", stats)
    _expect("| min | n=1 W=64 | 0.4100 |" in outm,
            "wgsl: the complete block still classifies", stats)

    # no sign verdict is rendered anywhere (rule 2 on this channel is
    # published in its own section -- render_wgsl_sign_section -- and
    # the rule-1 section itself still renders none)
    _expect("regime-invariant" not in out and "regime-scoped" not in out,
            "wgsl rule-1 section renders no rule-2 sign verdict", stats)


def _self_test_wgsl_sign_unit(stats):
    # ---- the WGSL wall-clock channel's rule-2 publication ----
    # Rule 2's unit on this channel is the `pair` line (the block's
    # paired-median subgroup/baseline ratio); the regimes are rule 1's
    # GAP-1.15 clusters of the SAME runs' baseline medians. The machine
    # is the MSL channel's sign_classification, unchanged.
    times = "\n".join([
        "time n=1048576 w=32 op=sum arm=subgroup "
        "single_median_ms=0.5100 single_rounds=11 "
        "batch32_median_ms=0.0700 batch32_rounds=7",
        "time n=1048576 w=32 op=sum arm=baseline "
        "single_median_ms=0.5000 single_rounds=11 "
        "batch32_median_ms=0.0638 batch32_rounds=7",
        "time n=1048576 w=64 op=sum arm=baseline "
        "single_median_ms=0.5200 single_rounds=11 "
        "batch32_median_ms=0.0600 batch32_rounds=7",
        "time n=1048576 w=64 op=sum arm=subgroup "
        "single_median_ms=0.5050 single_rounds=11 "
        "batch32_median_ms=0.0610 batch32_rounds=7",
        "time n=1048576 w=128 op=sum arm=baseline "
        "single_median_ms=0.8000 single_rounds=11 "
        "batch32_median_ms=0.0900 batch32_rounds=7",
        "time n=1048576 w=128 op=sum arm=subgroup "
        "single_median_ms=0.8100 single_rounds=11 "
        "batch32_median_ms=0.0910 batch32_rounds=7",
    ])

    def pair_line(w, s, b):
        return (f"pair n=1048576 w={w} op=sum single_paired_ratio={s} "
                f"batch32_paired_ratio={b} rounds=11/7")

    # -- parse: both metrics come off one pair line, per (n, W, op) --
    plog = "\n".join([pair_line(32, "0.931", "0.984"),
                      pair_line(64, "0.950", "0.959"),
                      pair_line(128, "1.020", "0.990")])
    pairs = parse_wgsl_measure_pairs(plog)
    _expect(pairs["single"]["sum"][(1048576, 32)] == 0.931
            and pairs["batch32"]["sum"][(1048576, 32)] == 0.984,
            "wgsl pair parse: one pair line carries both metrics' "
            "paired-median ratios", stats)
    _expect(set(pairs["single"]["sum"])
            == {(1048576, 32), (1048576, 64), (1048576, 128)},
            "wgsl pair parse: the run identity is (n, W)", stats)

    # duplicate pair blocks refuse (measurement error, not a merge)
    try:
        parse_wgsl_measure_pairs(plog + "\n" + pair_line(32, "0.931", "0.984"))
        raise AssertionError("duplicate wgsl pair line must raise")
    except ValueError:
        stats["passed"] += 1

    # a log with no pair lines refuses
    try:
        parse_wgsl_measure_pairs(times)
        raise AssertionError("wgsl log with no pair lines must raise")
    except ValueError:
        stats["passed"] += 1

    # -- by-regime straddle (single) beside regime-invariant (batch32):
    #    the two metrics NEVER mix in one classification --
    parsed = parse_wgsl_measure_log(times)
    out = render_wgsl_sign_section(parsed, parse_wgsl_measure_pairs(plog))
    _expect("## Sign classification (claim protocol rule 2, "
            "WGSL wall-clock channel)" in out,
            "wgsl rule-2 section title", stats)
    _expect("host wall-clock submit->completion" in out
            and "host-ms" in out and "gpu-ns" not in out,
            "wgsl rule-2 section names the channel's own metric",
            stats)
    _expect("never flips an MSL cell" in out
            and "never answers a workgroup row" in out
            and ":measured?" in out,
            "wgsl rule-2 sign claims are channel-scoped and rule 4 "
            "stands", stats)
    # per-level sign rows, exact
    rows = [l for l in out.splitlines()
            if l.startswith("| sum |")
            and ("| one-sided" in l or "| mixed sides" in l
                 or "| all at 1.0" in l)]
    _expect(rows == [
        "| sum | 1 (fastest observed) | n=1048576 W=32 (0.931), "
        "n=1048576 W=64 (0.950) | one-sided faster (2/2 below 1.0) |",
        "| sum | 2 (slowest observed) | n=1048576 W=128 (1.020) | "
        "one-sided slower (1/1 above 1.0) |",
        "| sum | 1 (fastest observed) | n=1048576 W=32 (0.984), "
        "n=1048576 W=64 (0.959) | one-sided faster (2/2 below 1.0) |",
        "| sum | 2 (slowest observed) | n=1048576 W=128 (0.990) | "
        "one-sided faster (1/1 below 1.0) |",
    ], "wgsl rule 2: regime-matched sign per level rows", stats)
    # single: level 1 faster / level 2 slower -> by-regime straddle
    _expect("| sum | regime-scoped | straddles 1.0 | straddle separates "
            "by regime (every regime one-sided, regimes disagree): "
            "level 1 (fastest observed): n=1048576 W=32 0.931 below "
            "1.0, n=1048576 W=64 0.950 below 1.0; level 2 (slowest "
            "observed): n=1048576 W=128 1.020 above 1.0 |" in out,
            "wgsl rule 2 single: by-regime straddle named", stats)
    single_part = out.split("### metric: batch32")[0]
    batch_part = out.split("### metric: batch32")[1]
    _expect("Cell (metric single, all 3 paired ratios pooled): "
            "**regime-scoped** (1 above 1.0, 2 below 1.0) -- not a "
            "selection basis; non-invariant operators: sum."
            in single_part,
            "wgsl rule 2 single metric: cell roll-up regime-scoped",
            stats)
    _expect("| sum | regime-invariant | faster | all 3 per-run ratios "
            "below 1.0 (3/3 faster); every observed regime one-sided |"
            in batch_part,
            "wgsl rule 2 batch32: same runs, own metric -- regime-"
            "invariant faster", stats)
    _expect("Cell (metric batch32, all 3 paired ratios pooled): "
            "**regime-invariant**, faster (3/3 faster)." in batch_part,
            "wgsl rule 2 batch32 metric: cell roll-up regime-invariant",
            stats)

    # -- within-regime straddle + no-side in one fixture --
    plog2 = "\n".join([pair_line(32, "0.958", "1.000"),
                       pair_line(64, "1.017", "1.000"),
                       pair_line(128, "1.100", "1.000")])
    out2 = render_wgsl_sign_section(parsed, parse_wgsl_measure_pairs(plog2))
    _expect("| sum | regime-scoped | straddles 1.0 | straddle within "
            "regime 1 (one regime holds both sides): level 1 (fastest "
            "observed): n=1048576 W=32 0.958 below 1.0, n=1048576 W=64 "
            "1.017 above 1.0; level 2 (slowest observed): n=1048576 "
            "W=128 1.100 above 1.0 |" in out2,
            "wgsl rule 2: within-regime straddle named", stats)
    _expect("| sum | regime-scoped | none | every ratio is exactly 1.0 "
            "-- no sign exists to claim |" in out2,
            "wgsl rule 2: no-side named when every ratio is exactly "
            "1.0", stats)

    # -- regime-invariant, the only admissible selection basis --
    plog3 = "\n".join([pair_line(32, "0.931", "0.900"),
                       pair_line(64, "0.950", "0.910"),
                       pair_line(128, "0.990", "0.950")])
    out3 = render_wgsl_sign_section(parsed, parse_wgsl_measure_pairs(plog3))
    _expect("Cell (metric single, all 3 paired ratios pooled): "
            "**regime-invariant**, faster (3/3 faster)." in out3
            and "Cell (metric batch32, all 3 paired ratios pooled): "
            "**regime-invariant**, faster (3/3 faster)." in out3,
            "wgsl rule 2: regime-invariant when every per-run ratio of "
            "every regime is on one side", stats)

    # -- incomplete data: named and excluded, never silently dropped --
    plog4 = "\n".join([pair_line(32, "0.931", "0.984"),
                       pair_line(64, "0.950", "0.959"),
                       pair_line(128, "1.020", "0.990"),
                       "pair n=1048576 w=256 op=sum single_paired_ratio="
                       "0.900 batch32_paired_ratio=0.900 rounds=11/7"])
    times4 = times + "\n" + "\n".join([
        "time n=1048576 w=32 op=max arm=baseline "
        "single_median_ms=0.4000 single_rounds=11 "
        "batch32_median_ms=0.0500 batch32_rounds=7",
        "time n=1048576 w=32 op=max arm=subgroup "
        "single_median_ms=0.4100 single_rounds=11 "
        "batch32_median_ms=0.0510 batch32_rounds=7",
    ])
    out4 = render_wgsl_sign_section(parse_wgsl_measure_log(times4),
                                    parse_wgsl_measure_pairs(plog4))
    _expect("n=1048576 W=256 (sum)" in out4
            and "no baseline per-run median, so no regime" in out4,
            "wgsl rule 2: a pair line the rule-1 levels cannot place "
            "is named and excluded", stats)
    _expect("n=1048576 W=32 (max)" in out4
            and "rule 2 has no unit for it" in out4,
            "wgsl rule 2: a rule-1 run with no pair line is named and "
            "excluded", stats)
    _expect("Cell (metric single, all 3 paired ratios pooled)" in out4,
            "wgsl rule 2: excluded runs do not enter the classification",
            stats)

    # -- the combined publication: rule-1 section, token, rule-2 --
    full = render_wgsl_claim_protocol(times + "\n" + plog)
    _expect("claim-protocol-rule2: PUBLISHED" in full
            and "## Sign classification (claim protocol rule 2, "
            "WGSL wall-clock channel)" in full,
            "wgsl claim-protocol publication carries the rule-2 token "
            "and section", stats)
    full_none = render_wgsl_claim_protocol(times)
    _expect("claim-protocol-rule2: NOT PUBLISHED" in full_none
            and "carries no sign to classify" in full_none,
            "wgsl claim-protocol publication names a rule-2 absence "
            "when the record has no pair lines", stats)
    _expect("## Regime classification (claim protocol rule 1, "
            "WGSL wall-clock channel)" in full
            and full.index("## Regime classification")
            < full.index("claim-protocol-rule2:"),
            "wgsl claim-protocol publication keeps rule 1 first", stats)


def _self_test_wgsl_corpus(stats, corpus_root):
    # STRUCTURE-ONLY regression over the committed pre-adoption WGSL
    # measure-log -- the deliberate boundary in the module docstring: the
    # classifier is never run over this record's VALUES (the record stays
    # OUT of the claim protocol; the named UNMEASURED question of whether
    # the WGSL host-clock baselines cluster into more than one regime
    # level waits on a fresh claim-protocol run).
    log_path = (corpus_root / "gpu" / "wgsl-measure-chrome-20261025"
                / "measure-log.txt")
    text = log_path.read_text()
    n_time = sum(1 for line in text.splitlines() if WGSL_TIME_RE.match(line))
    _expect(n_time == 72,
            f"the committed wgsl log carries 72 time lines (36 blocks x "
            f"2 arms), got {n_time}", stats)
    parsed = parse_wgsl_measure_log(text)
    runs_expected = {(n, w) for n in (1000003, 1048576)
                     for w in (32, 64, 128, 256, 512, 1024)}
    for metric in WGSL_METRICS:
        _expect(set(parsed[metric]) == {"sum", "max", "min"},
                f"wgsl corpus {metric}: the three operators", stats)
        for op in ("sum", "max", "min"):
            _expect(set(parsed[metric][op]) == runs_expected,
                    f"wgsl corpus {metric}/{op}: the 12 (n, W) runs", stats)
            for run, rec in parsed[metric][op].items():
                _expect(rec["baseline"] is not None
                        and rec["subgroup"] is not None,
                        f"wgsl corpus {metric}/{op}/{run}: both arms "
                        "present", stats)
    # the pre-adoption record still publishes no regime section
    _expect("regime" not in text.lower(),
            "the committed pre-adoption wgsl log stays rule-1 EMPTY",
            stats)


def _self_test_wgsl_sign_corpus(stats, corpus_root):
    # Rule-2 regression over the COMMITTED claim-protocol run-1 record
    # (docs/evidence/gpu/wgsl-claimprotocol-run1-20261025): the sign
    # classification re-derives from that log's own `pair` lines and the
    # pinned verdicts reproduce. (The deliberate boundary above excludes
    # only the PRE-ADOPTION log's values; run 1 is a claim-protocol
    # record and its values are exactly the machine's business.)
    log_path = (corpus_root / "gpu" / "wgsl-claimprotocol-run1-20261025"
                / "measure-log.txt")
    text = log_path.read_text()
    n_pair = sum(1 for l in text.splitlines() if WGSL_PAIR_RE.match(l))
    _expect(n_pair == 36,
            f"the run-1 wgsl log carries 36 pair lines (12 runs x 3 "
            f"ops), got {n_pair}", stats)
    pairs = parse_wgsl_measure_pairs(text)
    runs_expected = {(n, w) for n in (1000003, 1048576)
                     for w in (32, 64, 128, 256, 512, 1024)}
    for metric in WGSL_METRICS:
        _expect(set(pairs[metric]) == {"sum", "max", "min"},
                f"wgsl run-1 {metric}: the three operators", stats)
        for op in ("sum", "max", "min"):
            _expect(set(pairs[metric][op]) == runs_expected,
                    f"wgsl run-1 {metric}/{op}: the 12 (n, W) pair "
                    f"ratios", stats)
    out = render_wgsl_claim_protocol(text)
    _expect("claim-protocol-rule2: PUBLISHED" in out,
            "wgsl run-1: the claim-protocol publication carries the "
            "rule-2 token", stats)
    sign = out.split("## Sign classification (claim protocol rule 2, "
                     "WGSL wall-clock channel)")[1]
    single_part = sign.split("### metric: batch32")[0]
    batch_part = sign.split("### metric: batch32")[1]
    # pinned cell roll-ups (printed-precision: the machine classifies
    # the PRINTED pair ratios -- 3 single / 1 batch32 pairs print at
    # exactly 1.000 and classify 'at 1.0', where the log's own
    # aggregate counts from unrounded medians; the same
    # printed-precision class as the 12-vs-13 gap named in the
    # row-mapping record)
    _expect("Cell (metric single, all 36 paired ratios pooled): "
            "**regime-scoped** (19 above 1.0, 14 below 1.0, 3 at 1.0) "
            "-- not a selection basis; non-invariant operators: "
            "max, min, sum." in single_part,
            "wgsl run-1 single metric: the cell roll-up is "
            "regime-scoped, pinned", stats)
    _expect("Cell (metric batch32, all 36 paired ratios pooled): "
            "**regime-scoped** (20 above 1.0, 15 below 1.0, 1 at 1.0) "
            "-- not a selection basis; non-invariant operators: "
            "max, min, sum." in batch_part,
            "wgsl run-1 batch32 metric: the cell roll-up is "
            "regime-scoped, pinned", stats)
    # run 1 carries NO regime-invariant sign at any operator or cell --
    # the ADR-0360 first leg's "a fresh run carries a regime-invariant
    # sign" does not fire from this record
    _expect("| regime-invariant |" not in sign
            and "**regime-invariant**" not in sign,
            "wgsl run-1: no regime-invariant sign anywhere -- the "
            "first leg does not fire from run 1", stats)
    # one-sided LEVELS exist inside the straddling classifications and
    # are published (regime-matched sign per level, the row's target)
    _expect("one-sided slower (3/3 above 1.0)" in batch_part
            and "one-sided faster (1/1 below 1.0)" in single_part,
            "wgsl run-1: regime-matched sign per level is published "
            "(one-sided levels named inside regime-scoped operators)",
            stats)


def main():
    args = sys.argv[1:]
    if args == ["--self-test"]:
        stats = {"passed": 0}
        _self_test_unit(stats)
        print(f"unit fixtures: {stats['passed']} assertions passed")
        _self_test_corpus(stats, ROOT / "docs" / "evidence")
        _self_test_rule3_unit(stats)
        _self_test_rule3_corpus(stats, ROOT / "docs" / "evidence")
        _self_test_rule3_autowire(stats, ROOT / "docs" / "evidence")
        _self_test_pair_level_unit(stats)
        _self_test_pair_level_corpus(stats, ROOT / "docs" / "evidence")
        _self_test_identity_unit(stats)
        _self_test_identity_corpus(stats, ROOT / "docs" / "evidence")
        _self_test_pair_identity_unit(stats)
        _self_test_wgsl_unit(stats)
        _self_test_wgsl_sign_unit(stats)
        _self_test_wgsl_corpus(stats, ROOT / "docs" / "evidence")
        _self_test_wgsl_sign_corpus(stats, ROOT / "docs" / "evidence")
        print(f"TOTAL: {stats['passed']} assertions passed, 0 failed")
        return
    if len(args) == 2 and args[0] == "--wgsl-log":
        text = (sys.stdin.read() if args[1] == "-"
                else pathlib.Path(args[1]).read_text())
        print(render_wgsl_claim_protocol(text))
        return
    if len(args) == 2 and args[0] == "--pairs":
        complete, incomplete = parse_run_log_pairs(
            pathlib.Path(args[1]).read_text())
        print(render_pair_level_section(complete, incomplete))
        return
    if len(args) == 3 and args[0] == "--compare":
        hist = load_comparison_cell(pathlib.Path(args[1]).read_text(),
                                    args[1])
        new = load_comparison_cell(pathlib.Path(args[2]).read_text(),
                                   args[2])
        print(render_rule3_section(hist, new))
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
