#!/usr/bin/env python3
"""JUN-11 tick-51: pinned-source-graph probes for the r19cli SELF-REBUILD output.

Driver image = native-cli-selfrebuild-r19cli/native_cli.bin (gen2; gen3 output is
byte-identical to gen2 per its comparison). This crosses the self-rebuild fixpoint
with the locked (pinned) route: the compiler the native-built AMU produced from its
own 59-module closure verifies the module-lock + block-CID source graph.

Sections (argv[1]):
  tiny     - tiny lock: `modules` locked RC 0 + `check-entry` locked (semantic ok)
  locked59 - 59-module lock: `modules` locked RC 0 listing + `check-entry` locked
             at KEXE_VECTORS=4,194,304 (tick-50: rc 0, min_passing 3,276,800)
  negative - 4 negatives (tampered block / missing block / missing pin / root not
             pinned), all must be RC 65 with the established refusal text
  unpinned - `modules` unpinned output byte-identical between r19cli (G1) and the
             self-rebuild G2 image

Same fixtures as verify_native_cli_pinned_r19cli.py (tick-41 fixture set).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/Users/junkawasaki/github")
ART = BASE / "workspaces/codex/kotoba-sema-native-bridge-20261017/artifacts/kotoba-core-selfhost-refactor-20261017/artifacts"
G1 = ART / "native-cli-current-g3-r19cli"
G2 = ART / "native-cli-selfrebuild-r19cli"
G3 = ART / "native-cli-selfrebuild-r19cli-g2"
FIX = ART / "native-cli-pinned-r16cli"          # fixtures + block stores (tick-41)
OUT = ART / "native-cli-pinned-selfrebuild-r19cli"
LOGS = OUT / "logs"
LOADER = BASE / "workspaces/codex/amu1323-rebuild-17-main-20261018/host/kexe-loader"

IMAGE = G2 / "native_cli.bin"
ENTRY_OFFSET = json.loads((G2 / "report.json").read_text())["mainOffset"]

TINY_LOCK = FIX / "tiny.modules.edn"
TINY_BLOCKS = FIX / "tiny-blocks"
LOCK = FIX / "kotoba.modules.host.edn"
BLOCKS = FIX / "blocks-host"

REPORT = OUT / "report.json"


def run_native(name, args, image=IMAGE, offset=ENTRY_OFFSET):
    env = dict(os.environ)
    env.update(
        KEXE_COMMAND="1",
        KEXE_CAP_RESOURCES_35=":".join(
            str(p) for p in [OUT, FIX, TINY_BLOCKS, BLOCKS,
                             OUT / "blocks-tampered", OUT / "blocks-missing"]),
        KEXE_FUEL="off",
        KEXE_VECTORS="4194304",
        KEXE_VECTOR_ITEMS="134217728",
        KEXE_STRING_POOL="268435456",
        KEXE_PAIRS="67108864",
        KEXE_CPU_SECONDS="900",
        KEXE_WALL_SECONDS="900",
        TMPDIR=str(OUT),
    )
    prefix = [str(LOADER), str(image), str(offset), "0", "aarch64", "3,35,37,38,39", "--"]
    result = subprocess.run(prefix + args, cwd=OUT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=900)
    (LOGS / (name + ".stdout")).write_text(result.stdout)
    (LOGS / (name + ".stderr")).write_text(result.stderr)
    return result.returncode, result.stdout, result.stderr


def load_report():
    return json.loads(REPORT.read_text()) if REPORT.exists() else {
        "probe": "pinned-selfrebuild-r19cli-g2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entryOffset": ENTRY_OFFSET,
        "driverImage": str(IMAGE),
    }


def save_report(report):
    report["timestamp"] = datetime.now(timezone.utc).isoformat()
    REPORT.write_text(json.dumps(report, indent=2) + "\n")


def section_tiny(report):
    rc, out, err = run_native("tiny-modules-locked",
                              ["modules", "--module-lock", str(TINY_LOCK), "--blocks", str(TINY_BLOCKS)])
    report["tinyModulesLocked"] = {"rc": rc, "stdout": out.strip(), "stderr": err.strip()}
    rc2, out2, err2 = run_native("tiny-check-entry-locked",
                                 ["check-entry", "--module-lock", str(TINY_LOCK), "--blocks", str(TINY_BLOCKS)])
    report["tinyCheckEntryLocked"] = {"rc": rc2, "stdout": out2.strip(), "stderr": err2.strip()}


def section_locked59(report):
    rc, out, err = run_native("modules-locked-59",
                              ["modules", "--module-lock", str(LOCK), "--blocks", str(BLOCKS)])
    report["modulesLocked59"] = {"rc": rc, "stdout": out.strip(), "stderr": err.strip()}

    modules = re.findall(r"module=(\S+)", out)
    report["modulesLocked59Count"] = len(modules)

    rc3, out3, err3 = run_native("check-entry-locked-59",
                                 ["check-entry", "--module-lock", str(LOCK), "--blocks", str(BLOCKS)])
    report["checkEntryLocked59"] = {"rc": rc3, "stdout": out3.strip(), "stderr": err3.strip(),
                                    "vectors": 4194304}


def section_negative(report):
    lock_text = LOCK.read_text()
    m = re.search(r'(kotoba\.artifact\.core)\s+"(b[a-z2-7]{58})"', lock_text)
    victim_ns, victim_cid = m.group(1), m.group(2)

    tampered_root = OUT / "blocks-tampered"
    if tampered_root.exists():
        shutil.rmtree(tampered_root)
    shutil.copytree(BLOCKS, tampered_root)
    victim = tampered_root / victim_cid
    data = bytearray(victim.read_bytes())
    data[len(data) // 2] ^= 0x01
    victim.write_bytes(bytes(data))
    rca, outa, erra = run_native("neg-tampered",
                                 ["modules", "--module-lock", str(LOCK), "--blocks", str(tampered_root)])
    report["negTamperedBlock"] = {"victim": victim_ns, "rc": rca, "stderr": erra.strip()}

    missing_root = OUT / "blocks-missing"
    if missing_root.exists():
        shutil.rmtree(missing_root)
    shutil.copytree(BLOCKS, missing_root)
    (missing_root / victim_cid).unlink()
    rcb, outb, errb = run_native("neg-missing-block",
                                 ["modules", "--module-lock", str(LOCK), "--blocks", str(missing_root)])
    report["negMissingBlock"] = {"victim": victim_ns, "rc": rcb, "stderr": errb.strip()}

    nopin_lock = OUT / "kotoba.modules.nopin.edn"
    nopin_lock.write_text(re.sub(re.escape(victim_ns) + r'\s+"b[a-z2-7]{58}",?\s*', "", lock_text, count=1))
    rcc, outc, errc = run_native("neg-nopin",
                                 ["modules", "--module-lock", str(nopin_lock), "--blocks", str(BLOCKS)])
    report["negMissingPin"] = {"victim": victim_ns, "rc": rcc, "stderr": errc.strip()}

    root = re.search(r":root\s+([^\s,}]+)", lock_text).group(1)
    noroot_lock = OUT / "kotoba.modules.noroot.edn"
    noroot_lock.write_text(re.sub(re.escape(root) + r'\s+"b[a-z2-7]{58}",?\s*', "", lock_text, count=1))
    rcd, outd, errd = run_native("neg-noroot",
                                 ["modules", "--module-lock", str(noroot_lock), "--blocks", str(BLOCKS)])
    report["negRootNotPinned"] = {"root": root, "rc": rcd, "stderr": errd.strip()}


def section_unpinned(report):
    entry = BASE / "wt/codex/amu-selfhost-only-20261016/src/kotoba/compiler/selfhost_cli.kotoba"
    roots = [
        BASE / "wt/codex/amu-selfhost-only-20261016/src",
        BASE / "workspaces/codex/kotoba-core-selfhost-refactor-20261017/compiler-src-with-runtime-overlay",
        BASE / "wt/codex/kotoba-runtime-selfhost-main/src",
        BASE / "kotoba-lang/kotoba-lang/src",
        BASE / "kotoba-lang/osaho/src",
        BASE / "wt/codex/artifact-core-kotoba-selfhost-20261016/src",
        BASE / "wt/codex/kotoba-hir-selfhost-20261016/src",
        BASE / "kotoba-lang/coll/src",
        BASE / "wt/codex/kotoba-text-selfhost-20261016/src",
        BASE / "kotoba-lang/bytes/src",
        BASE / "kotoba-lang/error/src",
        BASE / "workspaces/codex/kotoba-core-selfhost-refactor-20261017/artifacts/selfhost-overlay-r9probe",
    ]
    args = ["modules", str(entry)]
    for root in roots:
        args.extend(["--source-path", str(root)])
    args.append("--unpinned")

    env = dict(os.environ)
    env.update(
        KEXE_COMMAND="1",
        KEXE_CAP_RESOURCES_35=":".join([str(OUT), *(str(r) for r in roots)]),
        KEXE_FUEL="off", KEXE_VECTORS="4194304", KEXE_VECTOR_ITEMS="134217728",
        KEXE_STRING_POOL="268435456", KEXE_PAIRS="67108864",
        KEXE_CPU_SECONDS="900", KEXE_WALL_SECONDS="900", TMPDIR=str(OUT),
    )
    out = {}
    g1_offset = json.loads((G1 / "report.json").read_text())["mainOffset"]
    for tag, image, offset in (("g1", G1 / "native_cli.bin", g1_offset),
                               ("g2", IMAGE, ENTRY_OFFSET)):
        prefix = [str(LOADER), str(image), str(offset), "0", "aarch64", "3,35,37,38,39", "--"]
        result = subprocess.run(prefix + args, cwd=OUT, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=900)
        (LOGS / (f"unpinned-{tag}.stdout")).write_text(result.stdout)
        (LOGS / (f"unpinned-{tag}.stderr")).write_text(result.stderr)
        out[tag] = (result.returncode, result.stdout, result.stderr)
    report["unpinnedModules"] = {
        "g1rc": out["g1"][0], "g2rc": out["g2"][0],
        "identical": out["g1"][1] == out["g2"][1],
        "lineCount": len(out["g1"][1].splitlines()),
        "sha256": hashlib.sha256(out["g1"][1].encode()).hexdigest(),
        "g1stderr": out["g1"][2].strip(), "g2stderr": out["g2"][2].strip(),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    report = load_report()
    section = sys.argv[1] if len(sys.argv) > 1 else "all"
    if section in ("tiny", "all"):
        section_tiny(report)
    if section in ("locked59", "all"):
        section_locked59(report)
    if section in ("negative", "all"):
        section_negative(report)
    if section in ("unpinned", "all"):
        section_unpinned(report)
    g2 = json.loads((G2 / "report.json").read_text())
    g3 = json.loads((G3 / "report.json").read_text())
    report["selfrebuildFixpoint"] = {
        "g2NativeImageSha256": g2["nativeImageSha256"],
        "g3NativeImageSha256": g3["nativeImageSha256"],
        "g2EqualsG3": g2["nativeImageSha256"] == g3["nativeImageSha256"],
        "g2ContainerSha256": g2["containerSha256"],
        "g3ContainerSha256": g3["containerSha256"],
        "g2EqualsG3Container": g2["containerSha256"] == g3["containerSha256"],
    }
    save_report(report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
