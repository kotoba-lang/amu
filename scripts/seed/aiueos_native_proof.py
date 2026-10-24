"""Bind AIUEOS diagnostics to actual native compiler generations and source.

Process orchestration only. This does not own the native CDCI verdict.
"""
import hashlib
import json
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def load_native_producers(build=None, complete=None):
    assert platform.system() == "Linux"
    assert (build is None) != (complete is None), "select one native proof"
    paths = [p for p in (ROOT / "seed/FULL-MANIFEST").read_text().splitlines()
             if p and not p.startswith("#")]
    source = {p: pin(ROOT / p) for p in ["seed/FULL-MANIFEST", *paths]}
    if complete is not None:
        assert platform.machine() in ("x86_64", "AMD64"), "actual native Linux x86_64 required"
        receipt = json.loads((complete / "complete-x86.json").read_text())
        assert receipt["status"] == "PASS_COMPLETE_NATIVE_X86_COMPILER_BUILD"
        assert not receipt["cCompilerOrLoader"] and not receipt["JVMNodeOrGraalFallback"] and not receipt["emulation"]
        unity = b"".join((ROOT / p).read_bytes() + b"\n" for p in paths)
        assert dict(bytes=len(unity), sha256=hashlib.sha256(unity).hexdigest()) == receipt["sourceUnity"]
        gens = receipt["generations"]
        assert len(gens) == 3 and gens[0] == gens[1] == gens[2]
        producers = [(complete / f"F{i}.elf", {k: gens[i - 1][k] for k in ("bytes", "sha256")}) for i in (2, 3)]
        baseline = ROOT / "bin/amu"
        expected = json.loads((ROOT / "native-product.json").read_text())["image"]
    else:
        assert platform.machine() in ("aarch64", "arm64"), "actual native Linux ARM64 required"
        receipt = json.loads((build / "selfhost-bootstrap.json").read_text())
        assert receipt["status"] == "PASS_LOADERLESS_SELFHOST_BOOTSTRAP"
        assert not receipt["cCompilerOrLoader"] and not receipt["JVMNodeOrGraalFallback"] and not receipt["emulation"]
        assert source == receipt["sourceGraph"]["full"], "current full source differs"
        gens = receipt["generations"]
        if len(gens) == 1:
            # After adoption the root is already the fixed point. This is
            # valid only when the measured rebuild reproduces those bytes.
            assert receipt["rootReproduces"] and gens[0]["image"] == receipt["root"]["image"]
            producers = [(build / "root.elf", receipt["root"]["image"]),
                         (build / (gens[0]["name"] + ".elf"), gens[0]["image"])]
        else:
            assert len(gens) >= 2 and gens[-1]["image"] == gens[-2]["image"]
            producers = [(build / (g["name"] + ".elf"), g["image"]) for g in gens[-2:]]
        baseline, expected = build / "root.elf", receipt["root"]["image"]
    for path, identity in producers:
        assert pin(path) == identity, ("producer pin drift", path)
    assert pin(baseline) == expected, "baseline native compiler pin drift"
    return source, [p for p, _ in producers], baseline
