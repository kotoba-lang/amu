#!/usr/bin/env python3
"""Check fresh ARM artifact identity before execution; never qualification."""
import argparse
import json
import platform
from pathlib import Path

from aiueos_native_proof import ROOT, load_native_producers, pin


def main(boot, one, output):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "arm64")
    graph, producers, baseline = load_native_producers(build=boot)
    product = json.loads((ROOT / "native-product.json").read_text())
    root = json.loads((ROOT / "seed/bootstrap/aarch64-linux-static-root.json").read_text())
    assert pin(baseline) == root["image"] == product["rootImage"]
    proof = json.loads((one / "one-compiler.json").read_text())
    assert proof["status"] == "PASS_COMBINED_COMPILER"
    assert proof["host"][:2] == ["Linux", platform.machine()]
    assert not proof["cCompilerOrLoader"] and not proof["emulation"]
    assert proof["bootstrap"]["receipt"] == pin(boot / "selfhost-bootstrap.json")
    for bindings in proof["sources"].values():
        for path, identity in bindings.items():
            assert pin(ROOT / path) == identity, ("transport source drift", path)
    assert pin(one / "F2.elf") == proof["F"]["image"] == proof["F"]["packedByF"] == root["image"]
    assert pin(one / "F-x86_64.elf") == proof["completeX86Compiler"] == product["image"]
    # Artifact downloads lose execute bits. Restore them only after all checks.
    for path in [baseline, *producers, one / "F2.elf"]:
        path.chmod(0o755)
    output.write_text(json.dumps(dict(schema="amu.native-arm-transport.v1",
        status="PASS_CURRENT_NATIVE_ARM_TRANSPORT_IDENTITIES", nativeVerdictAuthority=False,
        qualificationReplacement=False, fullQualification=False, sourceGraph=graph,
        root=pin(baseline), completeARM=pin(one / "F2.elf"),
        completeX86=pin(one / "F-x86_64.elf"),
        allRemainingARMAndX86GatesRequired=True), indent=2) + "\n")
    print("PASS_CURRENT_NATIVE_ARM_TRANSPORT_IDENTITIES", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bootstrap", type=Path, required=True)
    p.add_argument("--one", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.bootstrap.resolve(), a.one.resolve(), a.output.resolve())
