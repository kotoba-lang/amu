#!/usr/bin/env python3
"""Derive the bootstrap descriptors' digests from the Mac gate and cross receipts (JUN-545).

Inputs are the two receipts and the artifacts they name; no digest is passed
by hand. The writer re-hashes every artifact it reads, checks the receipts
against each other, and refuses on any mismatch. Python stages bytes and
compares them; it does not build or run a compiler.

Descriptors it can update (only their derived fields; every other field,
including status, qualification flags it cannot prove, and narrative text, is
kept as is):

* seed/bootstrap/aarch64-macos/root.json
    compiler, packager, fullSource, packagerSource, expectedFixedPoint and the
    two Mac fixed-point qualification flags.
* seed/bootstrap/aarch64-linux-static-root.json
    image, sourceUnity, producedBy.macFixedPointContainer.
* native-product.json
    image (the x86_64 full compiler), rootImage, sourceUnity, sourceModuleCount.
    Not derived here, because the Mac receipts do not prove them: the native x86
    compilerGenerations, sourceRevision (a git commit), qualification text.

--install (with --write) also copies the verified artifacts to
the paths the descriptors name: the signed Mac compiler and packager, the
aarch64 root ELF and bin/amu (bin/kotoba and bin/kotoba-compiler are links).

Two phases, because the cross gate and the descriptor-bound Mac gate refuse a
source the descriptor does not carry yet:

* --phase source (after a Mac gate run with explicit images on the new
  source): root.json takes the new fullSource, packagerSource and expected
  fixed point. The compiler pin stays the previous root, which is the bootstrap
  producer of the next run. The packager pin stays too, unless the packager's
  own source changed: then it moves to the receipt's fixed-point packager,
  because the next run must package with the new one (a packager change takes
  a staged run first: the old packager builds the new one, whose own run is the
  receipt). The other descriptors are not read.
* --phase final (default; after the descriptor-bound Mac gate and the cross
  gate): everything above.

Modes: --check (default) reports which fields differ and exits 1 if any;
--write rewrites the files. The signed Mach-O files differ in bytes between
hosts (ad hoc signatures), so the packager's signed digest is read from the
file in the build directory and tied to the receipt only through its
unsigned digest.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MAC_RECEIPT = "mac-aiueos-user-target.json"
CROSS_RECEIPT = "cross.json"


class Refused(Exception):
    pass


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest(), path.stat().st_size


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Refused(f"cannot read {path}: {error}")


def need(cond, message):
    if not cond:
        raise Refused(message)


def pin(path: Path, expected: dict, what: str):
    """The file at path must have exactly the receipt's digest and size."""
    need(path.is_file(), f"{what}: {path.name} is missing")
    digest, size = sha(path)
    need(digest == expected["sha256"] and size == expected["bytes"],
         f"{what}: {path.name} is {digest[:12]}/{size}, the receipt says "
         f"{expected['sha256'][:12]}/{expected['bytes']}")
    return {"bytes": size, "sha256": digest}


def derive_source(mac_dir: Path):
    """The new source's pins, from a Mac gate run alone."""
    mac = load(mac_dir / MAC_RECEIPT)
    need(mac.get("schema") == "amu.mac-aiueos-user-target.v3", "mac receipt schema")
    need(mac.get("status") == "PASS_MAC_NATIVE_USER_TARGET_SELFHOST", "mac gate did not pass")
    gens = mac["generations"]
    fp = mac["fixedPointGeneration"]
    need(isinstance(fp, int) and 2 <= fp <= len(gens), "fixedPointGeneration")
    last, prev = gens[fp - 1], gens[fp - 2]
    for key in ("container", "raw", "unsigned"):
        need(last[key] == prev[key], f"F{fp - 1} and F{fp} differ in {key}: not a fixed point")
    ps = mac["packagerSelfRebuild"]
    need(ps["unsigned"] == ps["repackagedUnsigned"], "packager did not repackage itself byte for byte")
    pin(mac_dir / f"F{fp}-signed.macho", last["signed"], f"F{fp} signed compiler")
    pin(mac_dir / f"F{fp}-unsigned.macho", last["unsigned"], f"F{fp} unsigned compiler")
    pin(mac_dir / "P1-unsigned.macho", ps["unsigned"], "packager unsigned")
    pk_digest, pk_size = sha(mac_dir / "P1-signed.macho")
    return {"install": [(mac_dir / "P1-signed.macho", "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho",
                         {"bytes": pk_size, "sha256": pk_digest})],
            "root": {"fullSource": dict(mac["source"]), "packagerSource": dict(ps["source"]),
                     "packager": {"bytes": pk_size, "sha256": pk_digest},
                     "container": last["container"]["sha256"],
                     "packagerUnsigned": ps["unsigned"]["sha256"]}}


def derive(mac_dir: Path, cross_dir: Path):
    mac = load(mac_dir / MAC_RECEIPT)
    cross = load(cross_dir / CROSS_RECEIPT)

    need(mac.get("schema") == "amu.mac-aiueos-user-target.v3", "mac receipt schema")
    need(mac.get("status") == "PASS_MAC_NATIVE_USER_TARGET_SELFHOST", "mac gate did not pass")
    need(cross.get("schema") == "amu.mac-cross-linux-candidates.v1", "cross receipt schema")
    need(cross.get("status") in ("MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED",
                                 "MAC_NATIVE_CROSS_CANDIDATES_UNADOPTED"), "cross gate status")
    need(cross.get("linuxProcessInThisGate") is False, "cross receipt records a Linux process")

    # the receipts must describe the same build
    pin(mac_dir / MAC_RECEIPT, cross["macSelfhostReport"], "cross receipt names the mac receipt")
    gens = mac["generations"]
    fp = mac["fixedPointGeneration"]
    need(isinstance(fp, int) and 2 <= fp <= len(gens), "fixedPointGeneration")
    last, prev = gens[fp - 1], gens[fp - 2]
    for key in ("container", "raw", "unsigned"):
        need(last[key] == prev[key], f"F{fp - 1} and F{fp} differ in {key}: not a fixed point")
    need(cross["container"] == last["container"], "cross container is not the fixed-point container")
    need(cross["producer"] == last["signed"], "cross producer is not the mac gate's fixed-point compiler")
    need(cross["fullSource"]["unity"] == mac["source"], "cross and mac gates saw different sources")
    need(cross["fullSource"]["manifest"] == mac["manifest"], "cross and mac gates saw different manifests")
    ps = mac["packagerSelfRebuild"]
    need(ps["unsigned"] == ps["repackagedUnsigned"], "packager did not repackage itself byte for byte")

    # every artifact the descriptors will pin is re-hashed from disk
    compiler = pin(mac_dir / f"F{fp}-signed.macho", last["signed"], f"F{fp} signed compiler")
    unsigned = pin(mac_dir / f"F{fp}-unsigned.macho", last["unsigned"], f"F{fp} unsigned compiler")
    pin(mac_dir / "P1-unsigned.macho", ps["unsigned"], "packager unsigned")
    pk_digest, pk_size = sha(mac_dir / "P1-signed.macho")
    arm = pin(cross_dir / "F-aarch64.elf", cross["aarch64Root"], "aarch64 root")
    x86 = pin(cross_dir / "F-x86_64.elf", cross["x86FullCompiler"], "x86_64 full compiler")
    del unsigned

    return {
        "install": [
            (mac_dir / f"F{fp}-signed.macho", "seed/bootstrap/aarch64-macos/amu-full-root.macho", compiler),
            (mac_dir / "P1-signed.macho", "seed/bootstrap/aarch64-macos/kotoba-packager-root.macho",
             {"bytes": pk_size, "sha256": pk_digest}),
            (cross_dir / "F-aarch64.elf", "seed/bootstrap/aarch64-linux-static-root.elf", arm),
            (cross_dir / "F-x86_64.elf", "bin/amu", x86),
        ],
        "root": {
            "compiler": compiler,
            "packager": {"bytes": pk_size, "sha256": pk_digest},
            "fullSource": dict(mac["source"]),
            "packagerSource": dict(ps["source"]),
            "container": last["container"]["sha256"],
            "packagerUnsigned": ps["unsigned"]["sha256"],
        },
        "linux": {
            "image": arm,
            "sourceUnity": dict(cross["fullSource"]["unity"]),
            "macContainer": dict(cross["container"]),
        },
        "product": {"image": x86, "rootImage": arm,
                    "sourceUnity": dict(cross["fullSource"]["unity"]),
                    "sourceModuleCount": cross["fullSource"]["modules"]},
    }


def updated(old: dict, new: dict, which: str, phase: str = "final"):
    doc = json.loads(json.dumps(old))
    if which == "root" and phase == "source":
        if doc["packagerSource"]["sha256"] != new["packagerSource"]["sha256"]:
            doc["packager"].update(new["packager"])
        doc["fullSource"].update(new["fullSource"])
        doc["packagerSource"].update(new["packagerSource"])
        doc["expectedFixedPoint"]["compilerContainerSha256"] = new["container"]
        doc["expectedFixedPoint"]["packagerUnsignedSha256"] = new["packagerUnsigned"]
    elif which == "root":
        doc["compiler"].update(new["compiler"])
        doc["packager"].update(new["packager"])
        doc["fullSource"].update(new["fullSource"])
        doc["packagerSource"].update(new["packagerSource"])
        doc["expectedFixedPoint"]["compilerContainerSha256"] = new["container"]
        doc["expectedFixedPoint"]["packagerUnsignedSha256"] = new["packagerUnsigned"]
        doc["qualification"]["sourceFixedPointOnMac"] = True
        doc["qualification"]["packagerFixedPointOnMac"] = True
    elif which == "linux":
        doc["image"].update(new["image"])
        doc["sourceUnity"].update(new["sourceUnity"])
        doc["producedBy"]["macFixedPointContainer"].update(new["macContainer"])
    else:
        doc["image"].update(new["image"])
        doc["rootImage"].update(new["rootImage"])
        doc["sourceUnity"].update(new["sourceUnity"])
        doc["sourceModuleCount"] = new["sourceModuleCount"]
    return doc


def flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat(v, f"{p}.{k}")
    else:
        yield p, o


def main(argv):
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--mac-build", type=Path, required=True,
                    help="output of check-aiueos-user-macos-native.py")
    ap.add_argument("--cross-build", type=Path,
                    help="output of check-macos-cross-linux-candidates.py (final phase)")
    ap.add_argument("--phase", choices=("source", "final"), default="final")
    ap.add_argument("--repo", type=Path, default=ROOT, help="repository whose descriptors are read")
    ap.add_argument("--install", action="store_true",
                    help="with --write in the final phase, copy the verified artifacts to the paths the descriptors name")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report differences (default)")
    mode.add_argument("--write", action="store_true", help="rewrite the descriptors")
    args = ap.parse_args(argv)

    files = {"root": args.repo / "seed/bootstrap/aarch64-macos/root.json",
             "linux": args.repo / "seed/bootstrap/aarch64-linux-static-root.json",
             "product": args.repo / "native-product.json"}
    try:
        if args.phase == "source":
            new = derive_source(args.mac_build)
            files = {"root": files["root"]}
        else:
            need(args.cross_build is not None, "--cross-build is required in the final phase")
            new = derive(args.mac_build, args.cross_build)
    except Refused as refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 2

    if args.install and not args.write:
        print("REFUSED: --install needs --write", file=sys.stderr)
        return 2
    # decided before anything is written: the descriptor still holds the old packager source
    packager_changed = (args.phase == "source" and
                        load(files["root"])["packagerSource"]["sha256"] != new["root"]["packagerSource"]["sha256"])
    differs = 0
    for which, path in files.items():
        old = load(path)
        doc = updated(old, new[which], which, args.phase)
        changes = [(k, a, b) for (k, a), (_, b) in zip(flat(old), flat(doc)) if a != b]
        for key, a, b in changes:
            print(f"{path.name}{key}: {str(a)[:16]} -> {str(b)[:16]}")
        differs += len(changes)
        if args.write and changes:
            path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.install:
        for src, rel, expected in new["install"]:
            if args.phase == "source" and not packager_changed:
                break
            digest, size = sha(src)
            need(digest == expected["sha256"] and size == expected["bytes"], f"{src.name} changed before install")
            dst = args.repo / rel
            if dst.is_file() and sha(dst)[0] == digest:
                continue
            tmp = dst.with_name(dst.name + ".installing")
            tmp.write_bytes(src.read_bytes())
            tmp.chmod(0o755)
            tmp.replace(dst)
            print(f"installed {rel}")
    print("DESCRIPTORS_CURRENT" if differs == 0 else
          ("DESCRIPTORS_WRITTEN" if args.write else f"DESCRIPTORS_DIFFER {differs}"))
    return 0 if (differs == 0 or args.write) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
