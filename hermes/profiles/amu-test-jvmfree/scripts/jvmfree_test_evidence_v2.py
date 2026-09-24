#!/usr/bin/env python3
"""amu-jvmfree-test evidence v2 — 測定経路修正版 (2026-09-18).

v1 からの差分は §4 のみ: bare `nbb test/nbb/run.cljk` は classpath 未解決で
環境赤になる既知アーチファクト (sema/kir/wasm は deps.edn の git 依存)。正本経路は
sanctioned launcher `nbb --classpath scripts scripts/run-nbb-regression.cljk`
(origin/main 903ac54f 以降に存在)。stale なローカル main checkout (551d7b8a) の
影響を排除するため origin/main の detached worktree (/tmp) で実測し、node_modules は
main checkout から symlink する。測定後 worktree は削除。

それ以外は v1 と同一:
  1. amu checkout の HEAD を報告
  2. test_profile.cljk 内の JVM 依存を grep で数える
  3. `bin/amu test <probe> --jvm-free` を実測
  5. append-only ledger に追記
stdout: MEASURE<TAB>key<TAB>value / REFUSED <reason> (exit 2)
"""
import json, os, re, subprocess, sys, datetime

ROOT = os.environ.get("REFACTOR_ROOT", "~/github/com-junkawasaki")
AMU_DIR = os.environ.get("AMU_DIR", os.path.join(ROOT, "orgs/kotoba-lang/amu"))
HERMES_HOME = os.environ.get("HERMES_HOME",
                             os.path.join(os.environ["HOME"], ".hermes/profiles/amu-test-jvmfree"))
LEDGER = os.path.join(HERMES_HOME, "workspace", "jvmfree-test-ledger.jsonl")

JVM_PATTERNS = {
    "clojure.java.shell": r"clojure\.java\.shell",
    "java.util.Base64": r"java\.util\.Base64",
    "java.lang.Runtime": r"Runtime/",
    "java.lang.System": r"System/",
    "java.io": r"java\.io\.",
}
TEST_FILE = os.path.join(AMU_DIR, "src/kotoba/compiler/test_profile.cljk")


def sh(cmd, cwd=None, timeout=300):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, "ERR:" + str(e)


def measure():
    rows = {}
    rc, out = sh(["git", "rev-parse", "--short", "HEAD"], cwd=AMU_DIR)
    if rc != 0:
        return None, "amu HEAD unreadable: " + out[:200]
    rows["amu_head"] = out.strip()

    # 2. JVM 依存の残数 (test_profile.cljk)
    try:
        with open(TEST_FILE, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        return None, f"test_profile.cljk unreadable: {e}"
    for key, pat in JVM_PATTERNS.items():
        hits = re.findall(pat, text)
        rows[f"jvm_{key.replace('.', '_')}"] = len(hits)
    rows["jvm_total"] = sum(rows[k] for k in rows if k.startswith("jvm_"))

    # 3. bin/amu nbbNativeEligible が test を受理するか — 実際に --jvm-free で呼ぶ
    probe = os.path.join("/tmp", f"amu-test-probe-{os.getpid()}.kotoba")
    try:
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("(ns t (:export [test-always-passes]))\n(defn test-always-passes [] true)\n")
        rc, out = sh([os.path.join(AMU_DIR, "bin/amu"), "test", probe, "--jvm-free"], cwd=AMU_DIR)
        rows["amu_test_jvmfree_rc"] = rc
        rows["amu_test_jvmfree_head"] = out.strip().splitlines()[0][:120] if out.strip() else "(no output)"
    finally:
        try:
            os.unlink(probe)
        except OSError:
            pass

    # 4. JVM-free 回帰経路 — origin/main の worktree snapshot で launcher 経路を実測。
    wt = os.path.join("/tmp", f"amu-nbb-eval-{os.getpid()}")
    rc_add, out_add = sh(["git", "worktree", "add", "--detach", wt, "origin/main"], cwd=AMU_DIR)
    if rc_add != 0:
        rows["nbb_run_rc"] = None
        rows["nbb_run_tail"] = "worktree add failed: " + out_add.strip()[:120]
        rows["amu_nbb_eval_head"] = "n/a"
    else:
        try:
            rows["amu_nbb_eval_head"] = sh(["git", "rev-parse", "--short", "HEAD"], cwd=wt)[1].strip()
            nm_main = os.path.join(AMU_DIR, "node_modules")
            nm_wt = os.path.join(wt, "node_modules")
            if not os.path.exists(nm_wt) and os.path.exists(nm_main):
                os.symlink(nm_main, nm_wt)
            rc, out = sh(["nbb", "--classpath", "scripts", "scripts/run-nbb-regression.cljk"],
                         cwd=wt, timeout=240)
            rows["nbb_run_rc"] = rc
            lines = [l for l in out.splitlines() if l.strip()]
            rows["nbb_run_tail"] = lines[-1][:160] if lines else "(no output)"
        finally:
            sh(["git", "worktree", "remove", "--force", wt], cwd=AMU_DIR)

    return rows, None


def main():
    try:
        rows, err = measure()
        if err is not None:
            print(f"REFUSED {err}")
            sys.exit(2)
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        rec = {"as-of": datetime.datetime.now(datetime.timezone.utc).isoformat(), **rows}
        with open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        for k, v in rows.items():
            print(f"MEASURE\t{k}\t{v}")
        sys.exit(0)
    except Exception as e:
        print(f"REFUSED {type(e).__name__}: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
