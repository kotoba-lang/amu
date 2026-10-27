#!/usr/bin/env python3
"""JUN-59 session 30 -- the ANCHOR-CLASS SETTLING BAR evaluator (frozen).

Deterministic decision procedure for the bar frozen in settle-bar.txt
(this directory, freeze stamp 2026-10-27T23:40:56Z). The evaluator is
evidence-scoped tooling: it is NOT compiler code and it implements no
vendor optimization. Its verdict strings are the bar's letters.

Input: an append-only ledger file, one candidate reading per line, in
chronological (append) order:

  day=<YYYY-MM-DD> session=<tag> class=<CAPTURED|INTERMEDIATE/MIXED|FLOOR>
      median=<int> min=<int> flag=<token>

flag=none qualifies; any other flag token is FLAGGED (the session is
recorded and adds no reading; it consumes no UTC-day slot). COUNTED =
the FIRST qualifying reading of each UTC day in ledger order (later
qualifying same-day readings are named descriptive content and do not
advance the bar -- settle-bar.txt section 2).

Verdict over the first four COUNTED readings, in this frozen check
order (settle-bar.txt V1..V4):
  CONTRADICTION FLOOR           any counted class == FLOOR
  CONTRADICTION OUT-OF-BAND     any counted median not within +/-5% of
                                EACH frozen reference 1129 / 1132 / 1131
  UNSETTLED CLASS-SPLIT         counted classes not all identical
  UNSETTLED BAND                one class but medians not mutually
                                within 5% (max/min - 1 > 0.05)
  SETTLED <class>               four counted, one class, in band,
                                mutually within 5%
  PENDING <n>/4                 fewer than four counted readings

--self-test runs the frozen fixture set (settle-bar.txt section 3):
deterministic output, a section per fixture, then a TOTAL line.
Running it twice is byte-identical (recorded in record.txt).
"""
import sys

REFS = (1129, 1132, 1131)  # frozen numeric references (settle-bar.txt D3)
BAND = 0.05
MUTUAL = 0.05
NEED = 4


def parse_ledger(text):
    """Return (counted, descriptive, flagged) reading dicts in ledger order."""
    counted, descriptive, flagged = [], [], []
    seen_days = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        f = {}
        for tok in line.split():
            k, _, v = tok.partition("=")
            f[k] = v
        r = dict(day=f["day"], session=f["session"], cls=f["class"],
                 median=int(f["median"]), mn=int(f["min"]), flag=f["flag"])
        if r["flag"] != "none":
            flagged.append(r)
            continue
        if r["day"] in seen_days:
            descriptive.append(r)
            continue
        seen_days.add(r["day"])
        counted.append(r)
    return counted, descriptive, flagged


def in_band(m):
    return all(abs(m - ref) <= BAND * ref for ref in REFS)


def evaluate(text):
    """Return (verdict, counted, descriptive, flagged)."""
    counted, descriptive, flagged = parse_ledger(text)
    four = counted[:NEED]
    if any(r["cls"] == "FLOOR" for r in four):
        return "CONTRADICTION FLOOR", four, descriptive, flagged
    if any(not in_band(r["median"]) for r in four):
        return "CONTRADICTION OUT-OF-BAND", four, descriptive, flagged
    if len(four) < NEED:
        return f"PENDING {len(four)}/{NEED}", four, descriptive, flagged
    classes = {r["cls"] for r in four}
    if len(classes) != 1:
        return "UNSETTLED CLASS-SPLIT", four, descriptive, flagged
    meds = [r["median"] for r in four]
    if max(meds) / min(meds) - 1.0 > MUTUAL:
        return "UNSETTLED BAND", four, descriptive, flagged
    return f"SETTLED {classes.pop()}", four, descriptive, flagged


# ---- frozen fixtures (settle-bar.txt section 3) ----
# each: (name, ledger text, expected verdict)
L = lambda day, sess, cls, med, mn, flag="none": (
    f"day={day} session={sess} class={cls} median={med} min={mn} flag={flag}")

FIXTURES = [
    ("pending-empty", "", "PENDING 0/4"),
    ("pending-3", "\n".join([
        L("2026-10-28", "s31", "INTERMEDIATE/MIXED", 1131, 990),
        L("2026-10-29", "s32", "INTERMEDIATE/MIXED", 1129, 995),
        L("2026-10-30", "s33", "INTERMEDIATE/MIXED", 1132, 988),
    ]), "PENDING 3/4"),
    ("settled-captured", "\n".join([
        L("2026-10-28", "s31", "CAPTURED", 1129, 1001),
        L("2026-10-29", "s32", "CAPTURED", 1132, 1003),
        L("2026-10-30", "s33", "CAPTURED", 1131, 1000),
        L("2026-10-31", "s34", "CAPTURED", 1128, 1002),
    ]), "SETTLED CAPTURED"),
    ("settled-mixed", "\n".join([
        L("2026-10-28", "s31", "INTERMEDIATE/MIXED", 1131, 990),
        L("2026-10-29", "s32", "INTERMEDIATE/MIXED", 1129, 985),
        L("2026-10-30", "s33", "INTERMEDIATE/MIXED", 1132, 991),
        L("2026-10-31", "s34", "INTERMEDIATE/MIXED", 1130, 988),
    ]), "SETTLED INTERMEDIATE/MIXED"),
    ("class-split", "\n".join([
        L("2026-10-28", "s31", "CAPTURED", 1129, 1001),
        L("2026-10-29", "s32", "INTERMEDIATE/MIXED", 1132, 976),
        L("2026-10-30", "s33", "CAPTURED", 1131, 1000),
        L("2026-10-31", "s34", "INTERMEDIATE/MIXED", 1128, 989),
    ]), "UNSETTLED CLASS-SPLIT"),
    ("band-split", "\n".join([
        L("2026-10-28", "s31", "CAPTURED", 1129, 1001),
        L("2026-10-29", "s32", "CAPTURED", 1076, 1004),
        L("2026-10-30", "s33", "CAPTURED", 1131, 1002),
        L("2026-10-31", "s34", "CAPTURED", 1129, 1000),
    ]), "UNSETTLED BAND"),
    ("contradiction-floor", "\n".join([
        L("2026-10-28", "s31", "INTERMEDIATE/MIXED", 1131, 990),
        L("2026-10-29", "s32", "FLOOR", 32, 31),
        L("2026-10-30", "s33", "INTERMEDIATE/MIXED", 1132, 988),
        L("2026-10-31", "s34", "INTERMEDIATE/MIXED", 1129, 991),
    ]), "CONTRADICTION FLOOR"),
    ("contradiction-oor", "\n".join([
        L("2026-10-28", "s31", "CAPTURED", 1200, 1050),
        L("2026-10-29", "s32", "CAPTURED", 1132, 1003),
        L("2026-10-30", "s33", "CAPTURED", 1131, 1000),
        L("2026-10-31", "s34", "CAPTURED", 1129, 1001),
    ]), "CONTRADICTION OUT-OF-BAND"),
    ("flagged-excluded", "\n".join([
        L("2026-10-28", "s31", "CAPTURED", 1130, 1001, "verify-mismatch"),
        L("2026-10-28", "s31", "CAPTURED", 1130, 1001, "pin-missing"),
        L("2026-10-29", "s32", "INTERMEDIATE/MIXED", 1131, 990),
        L("2026-10-30", "s33", "INTERMEDIATE/MIXED", 1129, 985),
        L("2026-10-31", "s34", "INTERMEDIATE/MIXED", 1132, 991),
        L("2026-11-01", "s35", "INTERMEDIATE/MIXED", 1130, 988),
    ]), "SETTLED INTERMEDIATE/MIXED"),
    ("same-day-duplicate", "\n".join([
        L("2026-10-28", "s31", "INTERMEDIATE/MIXED", 1131, 990),
        L("2026-10-28", "s31b", "CAPTURED", 1129, 1001),
        L("2026-10-29", "s32", "INTERMEDIATE/MIXED", 1129, 985),
        L("2026-10-30", "s33", "INTERMEDIATE/MIXED", 1132, 991),
        L("2026-10-31", "s34", "INTERMEDIATE/MIXED", 1130, 988),
    ]), "SETTLED INTERMEDIATE/MIXED"),
    ("same-day-after-flag", "\n".join([
        L("2026-10-28", "s31", "CAPTURED", 1130, 1001, "c1-b"),
        L("2026-10-28", "s31b", "INTERMEDIATE/MIXED", 1131, 990),
        L("2026-10-29", "s32", "INTERMEDIATE/MIXED", 1129, 985),
        L("2026-10-30", "s33", "INTERMEDIATE/MIXED", 1132, 991),
        L("2026-10-31", "s34", "INTERMEDIATE/MIXED", 1130, 988),
    ]), "SETTLED INTERMEDIATE/MIXED"),
]


def selftest():
    total = 0
    failed = 0
    for name, ledger, want in FIXTURES:
        verdict, counted, descriptive, flagged = evaluate(ledger)
        checks = [("verdict", verdict, want),
                  ("counted<=4", len(counted) <= NEED, True),
                  ("counted-days-unique",
                   len({r["day"] for r in counted}) == len(counted), True)]
        if name == "flagged-excluded":
            checks.append(("flagged-count", len(flagged), 2))
        if name == "same-day-duplicate":
            checks.append(("descriptive-count", len(descriptive), 1))
            checks.append(("first-of-day-wins", counted[0]["cls"],
                           "INTERMEDIATE/MIXED"))
        if name == "same-day-after-flag":
            checks.append(("flagged-count", len(flagged), 1))
            checks.append(("day-slot-not-consumed", counted[0]["session"],
                           "s31b"))
        print(f"fixture {name}: verdict {verdict!r} (want {want!r}); "
              f"counted {len(counted)} descriptive {len(descriptive)} "
              f"flagged {len(flagged)}")
        for what, got, exp in checks:
            total += 1
            ok = got == exp
            if not ok:
                failed += 1
            print(f"  check {what}: got {got!r} want {exp!r} -> "
                  f"{'ok' if ok else 'FAIL'}")
    print(f"TOTAL: {total} assertions passed, {failed} failed")
    return 1 if failed else 0


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        sys.exit(selftest())
    if len(sys.argv) != 2:
        print("usage: settle-bar-eval.py <ledger.txt> | --self-test")
        sys.exit(2)
    text = open(sys.argv[1]).read()
    verdict, counted, descriptive, flagged = evaluate(text)
    print(f"ledger: {sys.argv[1]}")
    for r in counted:
        print(f"counted    day={r['day']} session={r['session']} "
              f"class={r['cls']} median={r['median']} min={r['mn']}")
    for r in descriptive:
        print(f"descriptive day={r['day']} session={r['session']} "
              f"class={r['cls']} median={r['median']} min={r['mn']}")
    for r in flagged:
        print(f"flagged    day={r['day']} session={r['session']} "
              f"flag={r['flag']}")
    print(f"VERDICT: {verdict}")


if __name__ == "__main__":
    main()
