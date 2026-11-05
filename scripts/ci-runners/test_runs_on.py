#!/usr/bin/env python3
"""Evaluate every rendered `runs-on` expression for event/profile scenarios.

Negative controls: a fork pull request never gets a self-hosted label, under any
profile; an unset or 'hosted' profile never does either (behaviour unchanged).
A tiny evaluator for the GitHub expression subset the template uses keeps the
test on the real workflow text.
"""
import json, re, pathlib, sys, itertools
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import runs_on

TOK = re.compile(r"\s*(&&|\|\||==|!=|\(|\)|,|'[^']*'|[A-Za-z_][\w.]*)")


def evaluate(expr, ctx):
    toks, pos = [], 0
    while pos < len(expr.rstrip()):
        m = TOK.match(expr, pos)
        assert m, f"cannot tokenize {expr[pos:pos+30]!r}"
        toks.append(m.group(1)); pos = m.end()
    it = [0]
    peek = lambda: toks[it[0]] if it[0] < len(toks) else None
    def take(): it[0] += 1; return toks[it[0] - 1]
    def truthy(v): return v not in ("", None, False, 0)
    def prim():
        t = take()
        if t == "(":
            v = orx(); assert take() == ")"; return v
        if t.startswith("'"): return t[1:-1]
        if t in ("contains", "fromJSON"):
            assert take() == "("
            args = [orx()]
            while peek() == ",": take(); args.append(orx())
            assert take() == ")"
            return (json.loads(args[0]) if t == "fromJSON" else (args[1] in args[0]))
        return ctx.get(t, "")
    def eq():
        v = prim()
        while peek() in ("==", "!="):
            op = take(); w = prim(); v = (v == w) if op == "==" else (v != w)
        return v
    def andx():
        v = eq()
        while peek() == "&&":
            take(); w = eq(); v = w if truthy(v) else v
        return v
    def orx():
        v = andx()
        while peek() == "||":
            take(); w = andx(); v = v if truthy(v) else w
        return v
    v = orx(); assert peek() is None
    return v


def main():
    covered = []
    for p in sorted(runs_on.WORKFLOWS.glob("*.yml")):
        for line in p.read_text().split("\n"):
            m = runs_on.LINE.match(line)
            if m and m.group(4):
                covered.append((p.name, m.group(2), m.group(4)))
    assert len(covered) >= 30, len(covered)
    repo = "kotoba-lang/amu"
    events = {
        "push": {"github.event_name": "push"},
        "merge_group": {"github.event_name": "merge_group"},
        "pr-same": {"github.event_name": "pull_request", "github.event.pull_request.head.repo.full_name": repo},
        "pr-fork": {"github.event_name": "pull_request", "github.event.pull_request.head.repo.full_name": "evil/amu"},
        "pr-fork-name-prefix": {"github.event_name": "pull_request", "github.event.pull_request.head.repo.full_name": repo + "-x"},
    }
    fails = 0
    for (f, value, tag), (ev, ectx), prof in itertools.product(covered, events.items(), ["", "hosted", "selfhosted-arm", "selfhosted"]):
        for matrix in (["ubuntu-24.04-arm", "ubuntu-latest"] if tag == "${{ matrix.runner }}" else [tag]):
            ctx = dict(ectx, **{"github.repository": repo, "vars.AMU_RUNNER_PROFILE": prof, "matrix.runner": matrix})
            got = evaluate(value.strip()[3:-2], ctx)
            arm = matrix == "ubuntu-24.04-arm"
            selfhost_ok = ev in ("push", "merge_group", "pr-same")
            want = matrix
            if selfhost_ok and prof in ("selfhosted", "selfhosted-arm") and (arm or matrix == "macos-15"):
                want = "amu-macos-arm64" if matrix == "macos-15" else "amu-linux-arm64"
            elif selfhost_ok and prof == "selfhosted" and matrix == "ubuntu-latest":
                want = "amu-linux-x86_64"
            if got != want:
                fails += 1
                print(f"FAIL {f} {tag} ev={ev} profile={prof!r}: got {got!r} want {want!r}")
            if ev.startswith("pr-fork") or prof in ("", "hosted"):
                assert got == matrix, (f, ev, prof, got)
    print("ok" if not fails else f"{fails} failure(s)", f"({len(covered)} covered lines)")
    sys.exit(1 if fails else 0)


main()
