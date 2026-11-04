#!/usr/bin/env python3
"""S1 (JUN-804) gate: f32 programs built by two Amu Mac CLIs against C twins.

  python3 gate.py --old <amu-main>/bin/amu --new <amu-s1>/bin/amu --out result.json [--q8 <murakumo>/bench/kernels/q8_0-matvec]

Correctness: every program's checksum equals its C twin (cc -O2 -ffp-contract=off) under both compilers; the
1- and 4-accumulator matvecs differ (the values round, so order is observable); mutants differ; f32-from-bits
traps one past the 32-bit range and passes in range. Identity: integer-only programs compile to the same
__TEXT bytes under both compilers. Speed: CPU time (wait4 rusage) per 4864 x 896 matvec, (t[R] - t[0]) / R.
"""
import argparse, hashlib, json, os, shutil, statistics, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sh(*a, **kw):
    return subprocess.run([str(x) for x in a], capture_output=True, text=True, **kw)


def run(exe):
    p = subprocess.Popen([str(exe)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return p.returncode, out.decode().strip(), err.decode().strip()


def cpu(exe):
    p = subprocess.Popen([str(exe)], stdout=subprocess.PIPE)
    assert p.stdout is not None
    out = p.stdout.read().decode().strip()
    ru = os.wait4(p.pid, 0)[2]
    return ru.ru_utime + ru.ru_stime, out


def text_segment(path):
    data = Path(path).read_bytes()
    lc = sh("otool", "-l", path).stdout.split("\n")
    for i, line in enumerate(lc):
        if line.strip() == "segname __TEXT":
            fo = int(next(l for l in lc[i:i + 8] if "fileoff" in l).split()[1])
            fs = int(next(l for l in lc[i:i + 8] if "filesize" in l).split()[1])
            return hashlib.sha256(data[fo:fo + fs]).hexdigest()
    raise ValueError("no __TEXT in " + str(path))


def kotoba(work, name, text):
    p = work / f"{name}.kotoba"
    p.write_text(text)
    return p


def build(cli, src, exe):
    exe.unlink(missing_ok=True)
    r = sh(cli, "compile", src, "-o", exe)
    if r.returncode != 0:
        raise RuntimeError(f"{cli} compile {src}: {r.stdout} {r.stderr}")
    return exe


def ctwin(work, name, **defs):
    exe = work / f"c-{name}"
    flags = [f"-D{k}={v}" for k, v in defs.items()]
    r = sh("cc", "-O2", "-ffp-contract=off", *flags, "-o", exe, HERE / "twin.c", "-lm")
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return exe


def mv(rows, cols, reps, acc, op="add"):
    body = (HERE / f"rowdot{acc}.kotoba").read_text().replace("@OP@", op)
    return ((HERE / "mv.kotoba.in").read_text().replace("@ROWDOT@", body)
            .replace("@ROWS@", str(rows)).replace("@COLS@", str(cols)).replace("@REPS@", str(reps)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--q8", help="murakumo bench/kernels/q8_0-matvec, for the integer identity check")
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--rounds", type=int, default=5)
    a = ap.parse_args()
    work = Path(a.work).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    clis = {"old": Path(a.old).resolve(), "new": Path(a.new).resolve()}
    res = {"checks": [], "identity": {}, "speed": {}}

    def check(name, ok, **info):
        res["checks"].append({"name": name, "pass": bool(ok), **info})
        print(("PASS " if ok else "FAIL ") + name, json.dumps(info))

    # correctness against C twins
    progs = {
        "mv1": (mv(64, 896, 1, 1), ctwin(work, "mv1", PROG=1, ROWS=64, COLS=896, REPS=1, ACC=1)),
        "mv4": (mv(64, 896, 1, 4), ctwin(work, "mv4", PROG=1, ROWS=64, COLS=896, REPS=1, ACC=4)),
        "rms": ((HERE / "rms.kotoba.in").read_text().replace("@COLS@", "896").replace("@REPS@", "3"),
                ctwin(work, "rms", PROG=2, COLS=896, REPS=3)),
        "homes": ((HERE / "homes.kotoba").read_text(), ctwin(work, "homes", PROG=3)),
    }
    sums = {}
    for name, (text, cexe) in progs.items():
        expect = run(cexe)[1]
        src = kotoba(work, name, text)
        for tag, cli in clis.items():
            got = run(build(cli, src, work / f"{tag}-{name}"))
            sums[(tag, name)] = got[1]
            check(f"{tag}:{name} = C", got[0] == 0 and got[1] == expect, c=expect, kotoba=got[1], rc=got[0])
    check("mv1 != mv4 (order observable)", sums[("new", "mv1")] != sums[("new", "mv4")],
          mv1=sums[("new", "mv1")], mv4=sums[("new", "mv4")])
    for acc in (1, 4):
        src = kotoba(work, f"mut{acc}", mv(64, 896, 1, acc, op="sub"))
        for tag, cli in clis.items():
            got = run(build(cli, src, work / f"{tag}-mut{acc}"))
            check(f"{tag}:mutant{acc} != C", got[1] != sums[("new", f"mv{acc}")], kotoba=got[1])
    # f32-from-bits range: inline check on the new compiler, library assert on the old one
    for v, want in ((1069547520, "1075838976"), (-1069547520, "-1073741824"), (2147483647, None),
                    (2147483648, "trap"), (-2147483649, "trap")):
        src = kotoba(work, f"trap{abs(v)}{'n' if v < 0 else ''}", (HERE / "trap.kotoba.in").read_text().replace("@V@", str(v)))
        outs = {}
        for tag, cli in clis.items():
            rc, out, _ = run(build(cli, src, work / f"{tag}-{src.stem}"))
            outs[tag] = "trap" if rc != 0 else out
        same = outs["old"] == outs["new"]
        check(f"f32-from-bits {v}", same and (want is None or outs["new"] == want), old=outs["old"], new=outs["new"])
    # integer programs: identical __TEXT under both compilers (FP homes and the range wrapper never apply)
    ints = {}
    if a.q8:
        q8 = (Path(a.q8) / "q8_matvec.kotoba.in").read_text()
        ints["q8-small"] = q8.replace("@ROWS@", "64").replace("@COLS@", "896").replace("@REPS@", "1")
        ints["q8-full"] = q8.replace("@ROWS@", "4864").replace("@COLS@", "896").replace("@REPS@", "50")
    ints["hello"] = "(ns hello (:export [main]))\n(defn main [] :i64 (+ 40 2))\n"
    ints["loop"] = ("(ns probe.loop (:export [main]))\n(defn main [] :i64\n  (let [v (vector-alloc 64)]\n"
                    "    (loop [i 0 c 7]\n      (if (= i 100000) c\n        (recur (+ i 1) (bit-and (+ (* c 31) "
                    "(vector-at v (bit-and i 63))) 281474976710655))))))\n")
    for name, text in ints.items():
        src = kotoba(work, name, text)
        h = {tag: text_segment(build(cli, src, work / f"{tag}-{name}")) for tag, cli in clis.items()}
        res["identity"][name] = h
        check(f"identical __TEXT: {name}", h["old"] == h["new"], **h)
    # speed: CPU time per 4864 x 896 matvec
    for acc in (1, 4):
        exes = {}
        for reps in (0, a.reps):
            src = kotoba(work, f"perf{acc}-{reps}", mv(4864, 896, reps, acc))
            for tag, cli in clis.items():
                exes[(tag, reps)] = build(cli, src, work / f"{tag}-perf{acc}-{reps}")
            exes[("c", reps)] = ctwin(work, f"perf{acc}-{reps}", PROG=1, ROWS=4864, COLS=896, REPS=reps, ACC=acc)
        for e in exes.values():
            run(e)  # first exec pays the system scan
        per = {k: [] for k in ("old", "new", "c")}
        outs = {}
        for _ in range(a.rounds):
            for tag in per:
                z = cpu(exes[(tag, 0)])[0]
                t, out = cpu(exes[(tag, a.reps)])
                per[tag].append((t - z) / a.reps * 1e3)
                outs[tag] = out
        check(f"perf acc{acc} checksums agree", len(set(outs.values())) == 1, **outs)
        res["speed"][f"acc{acc}"] = {tag: {"ms_median": round(statistics.median(v), 3),
                                           "ms_range": [round(min(v), 3), round(max(v), 3)]} for tag, v in per.items()}
        print(f"speed acc{acc}", json.dumps(res["speed"][f"acc{acc}"]))
    res["loadavg"] = os.getloadavg()
    res["clis"] = {tag: hashlib.sha256(Path(c).read_bytes()).hexdigest() for tag, c in clis.items()}
    res["all_pass"] = all(c["pass"] for c in res["checks"])
    Path(a.out).write_text(json.dumps(res, indent=2) + "\n")
    print("ALL PASS" if res["all_pass"] else "SOME FAILED")
    sys.exit(0 if res["all_pass"] else 1)


if __name__ == "__main__":
    main()
