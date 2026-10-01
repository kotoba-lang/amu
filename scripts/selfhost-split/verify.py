#!/usr/bin/env python3
"""selfhost-split step 3: run the sema tests against the UNSPLIT original and the SPLIT copy, compare.

  verify.py --sema DIR --orig FRONTEND.cljk --split SPLIT-DIR --out WORK [--all] [--ns ns ...]

Both runs put a scratch directory FIRST on the classpath (so `kotoba.compiler.frontend` resolves to the
snapshot / the facade, never to the repo copy).  Failing sets (FAIL/ERROR test names) are compared; they
must be identical.  Prints "LOADED-SPLIT-MODULES n" for the split run as proof the facade is in effect.
"""
import argparse, os, re, shutil, subprocess, sys

DEFAULT = ["library-heads", "abort-ability", "state-ability", "keyword-map-record-literal", "string-upper",
           "vector-end-and-map-projection", "frontend-tables"]
NBB = "/Users/junkawasaki/github/kotoba-lang/amu-measure/node_modules/nbb/cli.js"

def runner(nss):
    req = " ".join(f"[{n}]" for n in nss)
    lst = " ".join(nss)
    return f"""(ns split-runner (:require [cljs.test :as t] [clojure.string :as cs] {req}))
(println "LOADED-SPLIT-MODULES"
         (count (filter #(cs/starts-with? (str %) "kotoba.compiler.frontend.") (map str (all-ns)))))
(t/run-tests {" ".join("'" + n for n in nss)})
"""

def run(label, cp_first, sema, nss, work, cpfile):
    os.makedirs(work, exist_ok=True)
    rn = os.path.join(work, f"runner-{label}.cljs")
    open(rn, "w").write(runner(nss))
    cp = f"{cp_first}:{sema}/src:{sema}/test:" + open(cpfile).read().strip()
    p = subprocess.run(["node", "--stack-size=4096", NBB, "--classpath", cp, rn], cwd=sema,
                       capture_output=True, text=True, timeout=3000)
    out = p.stdout + p.stderr
    open(os.path.join(work, f"{label}.log"), "w").write(out)
    fails = sorted(set(re.findall(r"^(?:FAIL|ERROR) in \((\S+)\)", out, re.M)))
    ran = re.findall(r"Ran (\d+) tests containing (\d+) assertions", out)
    cnt = re.findall(r"(\d+) failures, (\d+) errors", out)
    loaded = re.findall(r"LOADED-SPLIT-MODULES (\d+)", out)
    crashed = ("----- Error" in out) or not ran
    return {"fails": fails, "ran": ran[-1] if ran else None, "counts": cnt[-1] if cnt else None,
            "loaded": int(loaded[0]) if loaded else None, "crashed": crashed, "log": os.path.join(work, f"{label}.log")}

def overlay(sema, split, out):
    """Patched COPIES of consumers whose binding/with-redefs reach facade vars (see consumers.py)."""
    d = os.path.join(out, "overlay")
    shutil.rmtree(d, ignore_errors=True)
    here = os.path.dirname(os.path.abspath(__file__))
    rep = os.path.join(split, "split-report.json")
    txt = ""
    for sub in ("src", "test"):
        r = subprocess.run([sys.executable, os.path.join(here, "consumers.py"), os.path.join(sema, sub), "--root",
                            os.path.join(sema, sub), "--rewrite", d, "--split-report", rep], capture_output=True, text=True)
        txt += r.stdout
    return d, txt

def probe(label, cp_first, sema, work, cpfile):
    here = os.path.dirname(os.path.abspath(__file__))
    cp = f"{cp_first}:{sema}/src:{sema}/test:" + open(cpfile).read().strip()
    p = subprocess.run(["node", "--stack-size=4096", NBB, "--classpath", cp, os.path.join(here, "probe-controls.cljs")],
                       cwd=sema, capture_output=True, text=True, timeout=600)
    return (p.stdout + p.stderr).strip().splitlines()[-2:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sema", required=True)
    ap.add_argument("--orig", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--all", action="store_true", help="every test namespace listed in the sema run-tests.cljk")
    ap.add_argument("--ns", nargs="*")
    ap.add_argument("--raw", action="store_true", help="also run the split WITHOUT the consumer overlay (informational)")
    ap.add_argument("--cp", default="/private/tmp/wall-cp-10.txt")
    ns = ap.parse_args()
    nss = ns.ns or [f"kotoba.compiler.{n}-test" for n in DEFAULT]
    if ns.all:
        nss = re.findall(r"'(kotoba\.[A-Za-z0-9.\-]+-test)", open(os.path.join(ns.sema, "run-tests.cljk")).read())
        nss = list(dict.fromkeys(nss))
    base = os.path.join(ns.out, "orig-cp", "kotoba", "compiler")
    shutil.rmtree(os.path.join(ns.out, "orig-cp"), ignore_errors=True)
    os.makedirs(base)
    shutil.copy(ns.orig, os.path.join(base, "frontend.cljk"))
    a = run("orig", os.path.join(ns.out, "orig-cp"), ns.sema, nss, ns.out, ns.cp)
    ov, ovtxt = overlay(ns.sema, ns.split, ns.out)
    print(ovtxt.strip())
    raw = run("split-raw", ns.split, ns.sema, nss, ns.out, ns.cp) if ns.raw else None
    b = run("split", f"{ov}:{ns.split}", ns.sema, nss, ns.out, ns.cp)
    print(f"namespaces: {len(nss)}")
    print("orig :", a)
    print("split:", b)
    same = a["fails"] == b["fails"] and a["ran"] == b["ran"] and a["counts"] == b["counts"] and not b["crashed"] and not a["crashed"]
    if raw:
        print("split WITHOUT consumer overlay:", {k: raw[k] for k in ("ran", "counts", "crashed")},
              "same failing set as orig:", raw["fails"] == a["fails"])
    print("controls probe (with-redefs on sema/max-functions): orig", probe("o", os.path.join(ns.out, "orig-cp"), ns.sema, ns.out, ns.cp),
          "| split+overlay", probe("s", f"{ov}:{ns.split}", ns.sema, ns.out, ns.cp),
          "| split raw", probe("r", ns.split, ns.sema, ns.out, ns.cp))
    print("LOADED split modules:", b["loaded"], "(orig:", a["loaded"], ")")
    print("IDENTICAL" if same and (b["loaded"] or 0) > 0 and not a["loaded"] else "DIFFERENT")
    if a["fails"] != b["fails"]:
        print("only in orig :", sorted(set(a["fails"]) - set(b["fails"])))
        print("only in split:", sorted(set(b["fails"]) - set(a["fails"])))
    sys.exit(0 if same else 1)

if __name__ == "__main__":
    main()
