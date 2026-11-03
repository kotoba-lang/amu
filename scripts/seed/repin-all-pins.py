#!/usr/bin/env python3
"""Regenerate and verify every derived pin a seed PR can make stale (JUN-759).

repin-derived-pins.py covers the bootstrap roots, Linux images, product
descriptors and the Mac CLI. This command adds the two pin kinds it does not:

  core adoption   seed/<adoption receipt> and seed/compiler-core.json (sources,
                  source unity, G1=G2=G3 native image and container), computed by
                  the Mac fixed point exactly like check-macos-core-adoption.py;
  native CDCI     seed/cdci/policy.json, the controller pin rows, the 24 case
                  image rows of seed/cdci/kotoba-gate.kotoba and the two role
                  source hashes in seed/79-native-cdci.kotoba.

Write mode (default), on a PR worktree, Mac arm64 only (~8 minutes):
  scripts/seed/repin-all-pins.py --merge origin/main
merges origin/main (pin files, derived CDCI/adoption files and the hash lines of
seed/79 are resolved mechanically; any other conflict is owner work and ends
with exit 12), then repeats repin-derived-pins.py + this sync until a fixed
point (the CDCI pins depend on the compiler, which embeds seed/79). Review
`git status` and commit; nothing is committed here.

Check mode (never writes the tree): scripts/seed/repin-all-pins.py --check
builds the Mac fixed point of the current sources and fails when a pin is stale.

Exit codes: 0 current, 10 CDCI pins stale, 11 core adoption stale,
12 owner-authored content needed (message says which), 2 environment/usage.
Native only: the Mac Amu fixed point does all compilation; Python stages bytes
and hashes. No JVM, nbb or hand-edited pins.

Not covered (see AGENTS.md): docs/evidence receipts are historical records
bound to their own sources and are not regenerated (`--report-receipts` lists
the ones whose pinned source drifted); a changed seed/79 or cdci entry/runtime
source other than the two role hashes, new case sources, a fixed point that is
absent, and conflicts outside the mechanical set need an owner decision.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEED = Path(__file__).resolve().parent
EXIT_CDCI, EXIT_CORE, EXIT_OWNER, EXIT_ENV = 10, 11, 12, 2

PIN_FILES = [
    "bin/amu-linux-x86_64", "bin/x86_64-linux/amu",
    "examples/foundation-starter/MACOS-ARM64.md", "examples/foundation-starter/candidate.json",
    "native-product.json", "seed/bootstrap/aarch64-linux-static-root.elf",
    "seed/bootstrap/aarch64-linux-static-root.json", "seed/bootstrap/aarch64-macos/amu-cli.macho",
    "seed/bootstrap/aarch64-macos/amu-full-root.macho", "seed/bootstrap/aarch64-macos/cli.json",
    "seed/bootstrap/aarch64-macos/root.json",
    # Rebuilt by the staged packager run when seed/macos-fs2-runtime-packager.kotoba
    # changes; repin-derived-pins.py installs it, so a merge conflict takes main's.
    "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho",
]
# Whole files that are outputs of this command: on a merge conflict take the
# base's side and regenerate. kotoba-gate.kotoba and controller.kotoba are
# generated row tables; their non-row text must not be edited by a PR.
DERIVED_FILES = ["seed/cdci/policy.json", "seed/cdci/controller.kotoba", "seed/cdci/kotoba-gate.kotoba",
                 "seed/compiler-core.json"]
ROLE_LINE = re.compile(r'^.*\(string=\? role "[a-z-]+"\) "[0-9a-f]{64}".*$', re.M)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(h8):
    """Eight hex characters as the little-endian 64-bit literal the rows use."""
    return "0x" + h8.encode()[::-1].hex()


def git(root, *args, check=True):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError("git " + " ".join(args) + ": " + r.stderr.strip())
    return r


class Owner(Exception):
    """Content only the owner can author; the message says exactly what."""


class Sync:
    def __init__(self, root, mac_build, write):
        self.root, self.write, self.stale = Path(root).resolve(), write, []
        spec = importlib.util.spec_from_file_location("mac_gate", self.root / "scripts/seed/check-aiueos-user-macos-native.py")
        if spec is None or spec.loader is None:
            raise Owner("cannot load scripts/seed/check-aiueos-user-macos-native.py from " + str(self.root))
        self.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gate)
        report = json.loads((mac_build / "mac-aiueos-user-target.json").read_text())
        n = report["generations"][-1]["number"]
        self.producer = mac_build / f"F{n}-signed.macho"
        if not self.producer.is_file():
            raise Owner(f"no Mac fixed point image {self.producer}")
        self.tmp = Path(tempfile.mkdtemp(prefix="repin-all-", dir=str(mac_build.parent)))
        self.tmp.chmod(0o700)

    # -- helpers
    def path(self, rel):
        return self.root / rel

    def modules(self, manifest):
        return [s for s in self.path(manifest).read_text().splitlines() if s and not s.startswith("#")]

    def unity(self, manifest):
        return b"".join(self.path(p).read_bytes() + b"\n" for p in self.modules(manifest))

    def native(self, *args):
        return self.gate.native_run(self.producer, self.tmp, *args)

    def stage(self, name, data):
        (self.tmp / name).write_bytes(data)

    def put(self, rel, text, why):
        p = self.path(rel)
        if p.read_text() != text:
            self.stale.append((rel, why))
            if self.write:
                p.write_text(text)

    # -- core adoption
    def core(self):
        gate = self.gate
        core_path, core = "seed/compiler-core.json", json.loads(self.path("seed/compiler-core.json").read_text())
        adoption_rel = core["adoptionReceipt"]
        adoption = json.loads(self.path(adoption_rel).read_text())
        names = self.modules(adoption["sourceManifest"])
        if len(names) != len(set(names)):
            raise Owner("seed/MANIFEST lists a module twice")
        sources = []
        for name in names:
            p = Path(name)
            if p.is_absolute() or ".." in p.parts or p.parts[0] != "seed":
                raise Owner("invalid core source path " + name)
            sources.append({"path": name, **gate.require_regular(self.path(name))})
        unity = self.unity(adoption["sourceManifest"])
        want = {"bytes": len(unity), "sha256": sha(unity)}
        cur = {"bytes": adoption["sourceUnityBytes"], "sha256": adoption["sourceUnitySHA256"]}
        if sources == adoption["sources"] == core["sources"] and want == cur == {"bytes": core["sourceUnityBytes"], "sha256": core["sourceUnitySHA256"]}:
            return adoption_rel
        self.stale.append((adoption_rel, "core source drift (seed/MANIFEST modules changed): adoption round required"))
        self.core_drift = True
        if not self.write:
            return adoption_rel
        desc = json.loads(self.path("seed/bootstrap/aarch64-macos/root.json").read_text())
        packager = self.path(desc["packager"]["path"])
        self.stage("adopted-unity.kotoba", unity)
        generations, current = [], self.producer
        for number in (1, 2, 3):
            container, raw = f"G{number}.kseed", f"G{number}.bin"
            unsigned, signed = self.tmp / f"G{number}-unsigned.macho", self.tmp / f"G{number}-signed.macho"
            gate.native_run(current, self.tmp, "compile", "adopted-unity.kotoba", "--target", "aarch64-macos", "--output", container)
            out = gate.native_run(current, self.tmp, "extract-native", container, "--symbol", "main", "--output", raw)
            m = re.search(rb":offset (\d+), :length (\d+), :arity 0}", out.stdout)
            if m is None or int(m.group(2)) != (self.tmp / raw).stat().st_size:
                raise Owner("core main extraction mismatch")
            gate.native_run(packager, self.tmp, unsigned.name, raw, "fs2-cli-stdio-general", m.group(1).decode())
            gate.sign(unsigned, signed)
            generations.append({"name": f"G{number}", "native": gate.pin(self.tmp / raw), "container": gate.pin(self.tmp / container)})
            current = signed
        if not all(g["native"] == generations[0]["native"] and g["container"] == generations[0]["container"] for g in generations):
            raise Owner("core source fixed point G1=G2=G3 is absent: the PR's core change does not self-reproduce; fix the source")
        adoption.update(sourceUnityBytes=want["bytes"], sourceUnitySHA256=want["sha256"], sources=sources,
                        nativeImageBytes=generations[0]["native"]["bytes"], nativeImageSHA256=generations[0]["native"]["sha256"],
                        container=generations[0]["container"], generations=generations)
        core.update(sourceUnityBytes=want["bytes"], sourceUnitySHA256=want["sha256"], sources=sources)
        self.path(adoption_rel).write_text(json.dumps(adoption, indent=2) + "\n")
        self.path(core_path).write_text(json.dumps(core, indent=2) + "\n")
        return adoption_rel

    # -- native CDCI
    def cdci(self, adoption_rel):
        adoption = json.loads(self.path(adoption_rel).read_text())
        policy_rel = "seed/cdci/policy.json"
        policy = json.loads(self.path(policy_rel).read_text())
        new = dict(policy)
        core_unity = self.unity("seed/MANIFEST")
        new["coreSourceSHA256"] = sha(core_unity)
        new["coreContainerSHA256"] = adoption["container"]["sha256"]
        self.stage("core-static.kotoba", self.unity("seed/CORE-STATIC-MANIFEST"))
        self.native("compile", "core-static.kotoba", "--target", "x86_64-linux", "--output", "amu-selfhost.elf", "--format", "static")
        new["amuSelfhostGateSHA256"] = sha((self.tmp / "amu-selfhost.elf").read_bytes())

        cases = json.loads(self.path("seed/static-cases.json").read_text())["cases"]
        if len(cases) != policy["caseCount"]:
            raise Owner("seed/static-cases.json case count differs from policy.caseCount: new cases need owner-authored gate rows")
        gate_rel = "seed/cdci/kotoba-gate.kotoba"
        gtxt = self.path(gate_rel).read_text()
        for i, case in enumerate(cases):
            self.stage(f"case-{i}.kotoba", case["source"].encode())
            self.native("compile", f"case-{i}.kotoba", "--target", "x86_64-linux", "--output", f"case-{i}.elf", "--format", "static")
            vals = {"h0": sha(case["source"].encode()), "h1": sha((self.tmp / f"case-{i}.elf").read_bytes())}
            m = re.search(r"\(defn- kg-vector-%d \[\] :i64\n(.*?)\n        v0 " % i, gtxt, re.S)
            if not m:
                raise Owner(f"kotoba-gate.kotoba has no vector for case {i}")
            block = m.group(1)
            for tag, val in vals.items():
                for k in range(8):
                    pat = re.compile(r"(%s_%d \(kc-word \(\+ p \d+\) )0x[0-9a-f]+( 8\))" % (tag, k * 8))
                    if not pat.search(block):
                        raise Owner(f"kotoba-gate.kotoba vector {i} lacks row {tag}_{k * 8}")
                    block = pat.sub(lambda mm: mm.group(1) + word(val[k * 8:(k + 1) * 8]) + mm.group(2), block, count=1)
            gtxt = gtxt[:m.start(1)] + block + gtxt[m.end(1):]
        self.put(gate_rel, gtxt, "case image rows")

        entry, runtime = self.path("seed/cdci/entry.kotoba").read_bytes(), self.path("seed/cdci/runtime.kotoba").read_bytes()
        new["kotobaGateSourceSHA256"] = sha(entry + runtime + gtxt.encode())
        p79_rel = "seed/79-native-cdci.kotoba"
        t79 = self.path(p79_rel).read_text()
        t79 = re.sub(r'(string=\? role "kotoba-native"\) ")[0-9a-f]{64}', lambda m: m.group(1) + sha(gtxt.encode()), t79)

        self.stage("entry.kotoba", entry)
        self.stage("runtime.kotoba", runtime)
        self.stage("kotoba-gate.kotoba", gtxt.encode())
        self.roles_built = True
        try:
            self.native("cdci-build", "kotoba-native", "entry.kotoba", "runtime.kotoba", "kotoba-gate.kotoba", "kotoba-native.elf")
            new["kotobaNativeGateSHA256"] = sha((self.tmp / "kotoba-native.elf").read_bytes())
        except Exception as e:  # producer's seed/79 is stale: refused until the compiler is rebuilt
            self.roles_built = False
            self.stale.append((p79_rel, "producer does not yet pin the current role hash (rebuild after sync): " + str(e)[:80]))

        ctl_rel = "seed/cdci/controller.kotoba"
        ctl = self.path(ctl_rel).read_text()
        for idx, f in enumerate(["coreSourceSHA256", "coreContainerSHA256", "amuSelfhostGateSHA256", "kotobaNativeGateSHA256", "kotobaGateSourceSHA256"]):
            for k in range(8):
                pat = re.compile(r"(\bh%d_%d \(kc-word \(\+ \(kc-g\) %d\) )0x[0-9a-f]+( 8\))" % (idx, k * 8, 20100000 + idx * 64 + k * 8))
                if not pat.search(ctl):
                    raise Owner(f"controller.kotoba lacks pin row h{idx}_{k * 8}")
                ctl = pat.sub(lambda mm: mm.group(1) + word(new[f][k * 8:(k + 1) * 8]) + mm.group(2), ctl, count=1)
        self.put(ctl_rel, ctl, "controller pin rows")
        t79 = re.sub(r'(string=\? role "controller"\) ")[0-9a-f]{64}', lambda m: m.group(1) + sha(ctl.encode()), t79)
        self.put(p79_rel, t79, "role source hashes")
        self.put(policy_rel, json.dumps(new, indent=2) + "\n", "policy pins")
        if self.roles_built:
            self.stage("controller.kotoba", ctl.encode())
            try:
                self.native("cdci-build", "controller", "entry.kotoba", "runtime.kotoba", "controller.kotoba", "controller.elf")
            except Exception as e:
                self.roles_built = False
                self.stale.append((p79_rel, "controller role is not pinned in the producer: " + str(e)[:80]))

    def run(self):
        self.core_drift = False
        adoption_rel = self.core()
        self.cdci(adoption_rel)
        shutil.rmtree(self.tmp, ignore_errors=True)
        return self.stale, self.roles_built


def build_mac_fixed_point(root, out):
    subprocess.run([sys.executable, str(root / "scripts/seed/check-aiueos-user-macos-native.py"), "--output", str(out / "mac-root")],
                   cwd=root, check=True)
    return out / "mac-root"


def merge(root, ref):
    r = git(root, "merge", "--no-edit", ref, check=False)
    if r.returncode == 0:
        return
    left = []
    for f in git(root, "diff", "--name-only", "--diff-filter=U").stdout.split():
        if f in PIN_FILES or f in DERIVED_FILES or re.fullmatch(r"seed/adoption-[^/]+\.json", f):
            git(root, "checkout", ref, "--", f)
        elif f == "seed/79-native-cdci.kotoba":
            base = git(root, "merge-base", "HEAD", ref).stdout.strip()
            parts = [ROLE_LINE.sub("ROLE-HASH-LINE", git(root, "show", f"{r_}:{f}").stdout) for r_ in ("HEAD", base, ref)]
            with tempfile.TemporaryDirectory() as d:
                files = []
                for name, text in zip(("ours", "base", "theirs"), parts):
                    (Path(d) / name).write_text(text)
                    files.append(str(Path(d) / name))
                m = subprocess.run(["git", "merge-file", "-p", *files], capture_output=True, text=True)
            if m.returncode:
                left.append(f)
            else:
                (root / f).write_text(m.stdout)  # ROLE-HASH-LINE placeholders are rewritten by the sync
                left.append(None)
        else:
            left.append(f)
    left = [f for f in left if f]
    if left:
        raise Owner("merge conflicts outside the mechanical set (pin files, derived CDCI/adoption files, seed/79 hash lines): " + " ".join(left))
    # The placeholder lines must be real role lines again before committing.
    p79 = root / "seed/79-native-cdci.kotoba"
    if "ROLE-HASH-LINE" in p79.read_text():
        canon = git(root, "show", f"{ref}:seed/79-native-cdci.kotoba").stdout
        lines = ROLE_LINE.findall(canon)
        text = p79.read_text()
        for line in lines:
            text = text.replace("ROLE-HASH-LINE", line, 1)
        p79.write_text(text)
    git(root, "add", "-A")
    git(root, "-c", "core.editor=true", "commit", "--no-edit")


def report_receipts(root):
    """Informational: tracked docs JSON receipts whose pinned source hash drifted."""
    found = 0
    for f in git(root, "ls-files", "docs").stdout.split():
        if not f.endswith(".json"):
            continue
        try:
            data = json.loads((root / f).read_text())
        except Exception:
            continue
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                p, h = x.get("path"), x.get("sha256")
                if isinstance(p, str) and isinstance(h, str) and (root / p).is_file() and sha((root / p).read_bytes()) != h:
                    print("drifted receipt pin:", f, p)
                    found += 1
                stack.extend(x.values())
            elif isinstance(x, list):
                stack.extend(x)
    print(f"{found} historical receipt pins differ from the current tree (not regenerated; see AGENTS.md)")


def report(stale, check):
    for rel, why in stale:
        print(("STALE " if check else "REGENERATED ") + rel + ": " + why)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=REPO, help="worktree to operate on (default: this repository)")
    ap.add_argument("--check", action="store_true", help="verify only; exit non-zero when a pin is stale")
    ap.add_argument("--merge", metavar="REF", help="first merge REF (e.g. origin/main), resolving pin/derived conflicts mechanically")
    ap.add_argument("--mac-build", type=Path, help="existing mac-root build dir (skips building it; check mode)")
    ap.add_argument("--work", type=Path, help="work directory (default: a new temporary one)")
    ap.add_argument("--report-receipts", action="store_true")
    ap.add_argument("--rounds", type=int, default=5)
    a = ap.parse_args()
    root = a.root.resolve()
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        print("derived pins are produced on Mac arm64", file=sys.stderr)
        return EXIT_ENV
    if a.report_receipts:
        report_receipts(root)
        return 0
    work = a.work or Path(tempfile.mkdtemp(prefix="repin-all-"))
    work.mkdir(parents=True, exist_ok=True)
    try:
        if a.check:
            mac = a.mac_build or build_mac_fixed_point(root, work)
            stale, roles = Sync(root, mac.resolve(), write=False).run()
            report(stale, True)
            if not stale and roles:
                print("PASS_ALL_PINS_CURRENT")
                return 0
            core = any("core source drift" in why for _, why in stale)
            print("FAIL_STALE_PINS: run scripts/seed/repin-all-pins.py --merge origin/main", file=sys.stderr)
            return EXIT_CORE if core else EXIT_CDCI
        if a.merge:
            merge(root, a.merge)
        for i in range(1, a.rounds + 1):
            w = work / f"round-{i}"
            cmd = [sys.executable, str(root / "scripts/seed/repin-derived-pins.py"), "--work", str(w)]
            if i == 1 and a.merge:
                cmd += ["--take-pins-from", a.merge]
            subprocess.run(cmd, cwd=root, check=True)
            stale, roles = Sync(root, w / "mac-root", write=True).run()
            report(stale, False)
            if not stale and roles:
                git(root, "add", "-A", "--", *PIN_FILES, "seed/cdci", "seed/79-native-cdci.kotoba", "seed/compiler-core.json", "seed/adoption-*.json", check=False)
                print(f"PASS_ALL_PINS_FIXED_POINT after {i} round(s); review `git status` and commit")
                return 0
        print("FAIL_NO_FIXED_POINT: pins did not converge; owner review needed", file=sys.stderr)
        return EXIT_OWNER
    except Owner as e:
        print("OWNER_AUTHORED_CONTENT_NEEDED: " + str(e), file=sys.stderr)
        return EXIT_OWNER


if __name__ == "__main__":
    sys.exit(main())
