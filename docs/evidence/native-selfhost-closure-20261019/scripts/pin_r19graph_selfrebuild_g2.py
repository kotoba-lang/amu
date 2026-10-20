#!/usr/bin/env python3
"""JUN-11 tick-51 part 2: regenerate the pinned source graph (module lock + block
store) from the CURRENT self-rebuild sources and verify it with the SELF-REBUILT
compiler (native-cli-selfrebuild-r19cli/native_cli.bin).

Measured gap closed here: the tick-41 fixture graph (native-cli-pinned-r16cli)
verified its own snapshot, which is 57/59 byte-identical to the sources the
r19 self-rebuild compiled; kotoba.compiler.kotoba-reader and
kotoba.compiler.selfhost-cli were edited since. This script rebuilds the lock +
blocks from the exact sources in the self-rebuild report (so pinned graph ==
compiled sources by construction), then drives the self-built image through
`modules --module-lock`, `check-entry --module-lock` (59 modules) and the four
negative probes.

CID scheme (from native_project_files.kotoba: raw-cid-byte/cid-from-digest):
CIDv1 raw(0x55) sha256(0x12 0x20) over the source bytes, RFC4648-lowercase
base32, 'b' prefix (59 chars).
"""
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/Users/junkawasaki/github")
ART = BASE / "workspaces/codex/kotoba-sema-native-bridge-20261017/artifacts/kotoba-core-selfhost-refactor-20261017/artifacts"
G2 = ART / "native-cli-selfrebuild-r19cli"
OUT = ART / "native-cli-pinned-selfrebuild-r19cli-r19graph"
BLOCKS = OUT / "blocks-r19graph"
LOCK = OUT / "kotoba.modules.host-r19graph.edn"
LOGS = OUT / "logs"
LOADER = BASE / "workspaces/codex/amu1323-rebuild-17-main-20261018/host/kexe-loader"
FIX = ART / "native-cli-pinned-r16cli"  # tiny fixtures reused as-is

IMAGE = G2 / "native_cli.bin"
ENTRY_OFFSET = json.loads((G2 / "report.json").read_text())["mainOffset"]
REPORT = OUT / "report.json"

OUT.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)


def source_cid(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "b" + base64.b32encode(bytes([0x01, 0x55, 0x12, 0x20]) + digest).decode().lower().rstrip("=")


g2 = json.loads((G2 / "report.json").read_text())
modules = g2["modules"]
root = modules[-1]["namespace"]

# --- regenerate lock + blocks from the self-rebuild's own sources ---
BLOCKS.mkdir(exist_ok=True)
pins = {}
regen = []
for m in modules:
    ns, src = m["namespace"], Path(m["source"])
    data = src.read_bytes()
    cid = source_cid(data)
    (BLOCKS / cid).write_bytes(data)
    pins[ns] = cid
    regen.append({"namespace": ns, "source": str(src), "cid": cid,
                  "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})

lock_text = "{:schema :kotoba.module-lock/v1, :root " + root + ", :modules {" + ", ".join(
    f'{ns} "{pins[ns]}"' for ns in sorted(pins)) + "}}\n"
LOCK.write_text(lock_text)

# self-check: every block hashes to its CID
for ns, cid in pins.items():
    data = (BLOCKS / cid).read_bytes()
    if source_cid(data) != cid:
        raise SystemExit(f"block does not hash to its CID: {ns}")
print(f"graph regenerated: {len(pins)} pins, root={root}, lock={LOCK}", flush=True)


def run_native(name, args, cap_extra=()):
    env = dict(os.environ)
    env.update(
        KEXE_COMMAND="1",
        KEXE_CAP_RESOURCES_35=":".join(
            str(p) for p in [OUT, BLOCKS, FIX, *(Path(p) for p in cap_extra)]),
        KEXE_FUEL="off",
        KEXE_VECTORS="4194304",
        KEXE_VECTOR_ITEMS="134217728",
        KEXE_STRING_POOL="268435456",
        KEXE_PAIRS="67108864",
        KEXE_CPU_SECONDS="900",
        KEXE_WALL_SECONDS="900",
        TMPDIR=str(OUT),
    )
    prefix = [str(LOADER), str(IMAGE), str(ENTRY_OFFSET), "0", "aarch64", "3,35,37,38,39", "--"]
    result = subprocess.run(prefix + args, cwd=OUT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=900)
    (LOGS / (name + ".stdout")).write_text(result.stdout)
    (LOGS / (name + ".stderr")).write_text(result.stderr)
    return result.returncode, result.stdout, result.stderr


report = {
    "probe": "pinned-r19graph-selfrebuild-g2",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "driverImage": str(IMAGE),
    "driverNativeImageSha256": hashlib.sha256(IMAGE.read_bytes()).hexdigest(),
    "entryOffset": ENTRY_OFFSET,
    "lock": str(LOCK),
    "blocks": str(BLOCKS),
    "root": root,
    "pinCount": len(pins),
    "regenerated": regen,
}

rc, out, err = run_native("modules-locked-59",
                          ["modules", "--module-lock", str(LOCK), "--blocks", str(BLOCKS)])
report["modulesLocked59"] = {"rc": rc, "count": len(re.findall(r"module=(\S+)", out)), "stderr": err.strip()}

rc2, out2, err2 = run_native("check-entry-locked-59",
                             ["check-entry", "--module-lock", str(LOCK), "--blocks", str(BLOCKS)])
report["checkEntryLocked59"] = {"rc": rc2, "stdout": out2.strip(), "stderr": err2.strip(),
                                "vectors": 4194304}

lock_text_raw = LOCK.read_text()
m = re.search(r'(kotoba\.artifact\.core)\s+"(b[a-z2-7]{58})"', lock_text_raw)
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
                             ["modules", "--module-lock", str(LOCK), "--blocks", str(tampered_root)],
                             cap_extra=(tampered_root,))
report["negTamperedBlock"] = {"victim": victim_ns, "rc": rca, "stderr": erra.strip()}

missing_root = OUT / "blocks-missing"
if missing_root.exists():
    shutil.rmtree(missing_root)
shutil.copytree(BLOCKS, missing_root)
(missing_root / victim_cid).unlink()
rcb, outb, errb = run_native("neg-missing-block",
                             ["modules", "--module-lock", str(LOCK), "--blocks", str(missing_root)],
                             cap_extra=(missing_root,))
report["negMissingBlock"] = {"victim": victim_ns, "rc": rcb, "stderr": errb.strip()}

nopin_lock = OUT / "kotoba.modules.nopin.edn"
nopin_lock.write_text(re.sub(re.escape(victim_ns) + r'\s+"b[a-z2-7]{58}",?\s*', "", lock_text_raw, count=1))
rcc, outc, errc = run_native("neg-nopin",
                             ["modules", "--module-lock", str(nopin_lock), "--blocks", str(BLOCKS)])
report["negMissingPin"] = {"victim": victim_ns, "rc": rcc, "stderr": errc.strip()}

noroot_lock = OUT / "kotoba.modules.noroot.edn"
noroot_lock.write_text(re.sub(re.escape(root) + r'\s+"b[a-z2-7]{58}",?\s*', "", lock_text_raw, count=1))
rcd, outd, errd = run_native("neg-noroot",
                             ["modules", "--module-lock", str(noroot_lock), "--blocks", str(BLOCKS)])
report["negRootNotPinned"] = {"root": root, "rc": rcd, "stderr": errd.strip()}

REPORT.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("probe", "pinCount", "root")}))
print(json.dumps(report["modulesLocked59"]))
print(json.dumps(report["checkEntryLocked59"]))
print(json.dumps({k: report[k] for k in ("negTamperedBlock", "negMissingBlock", "negMissingPin", "negRootNotPinned")}))
