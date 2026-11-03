#!/usr/bin/env python3
"""Refresh only complete24 x86 image pins from a matching native observer receipt.

The source fixture and expected result/exit/fuel ledger stay authoritative. This
tool requires all 24 source identities and observed tuples to match before it
changes image hashes. It never executes an oracle or changes case semantics.
The Kotoba gate image pin is deliberately left for the following exact-head
selfhost build, whose output must be reviewed and recorded separately.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(path.read_bytes())


def encode_words(digest):
    raw = digest.encode("ascii")
    assert re.fullmatch(r"[0-9a-f]{64}", digest) and len(raw) == 64
    return [f"0x{int.from_bytes(raw[i:i + 8], 'little'):016x}" for i in range(0, 64, 8)]


def replace_vector(source, index, image_digest):
    pattern = re.compile(rf"(\(defn- kg-vector-{index} \[\] :i64\n)(.*?)(?=\n;; case |\n;; The Kotoba native gate)", re.S)
    match = pattern.search(source)
    assert match, f"missing kg-vector-{index}"
    body = match.group(2)
    replacements = encode_words(image_digest)
    for offset, word in zip(range(0, 64, 8), replacements):
        hname = f"h1_{offset}"
        line = re.compile(rf"({hname} \(kc-word \(\+ p {offset + 64}\) )0x[0-9a-f]+( 8\))")
        body, count = line.subn(rf"\g<1>{word}\g<2>", body)
        assert count == 1, f"case {index}: expected one {hname} image digest word, got {count}"
    return source[:match.start(2)] + body + source[match.end(2):]


def controller_pin_metadata(source):
    fields = ["coreSourceSHA256", "coreContainerSHA256", "amuSelfhostGateSHA256",
              "kotobaNativeGateSHA256", "kotobaGateSourceSHA256"]
    found = {}
    for index, field in enumerate(fields):
        rows = re.findall(r"\bh" + str(index) + r"_(\d+)\s+\(kc-word\s+\(\+\s+\(kc-g\)\s+(\d+)\)\s+0x([0-9a-f]+)\s+8\)", source)
        assert len(rows) == 8 and [int(row[0]) for row in rows] == list(range(0, 64, 8)), (field, rows)
        assert all(int(address) == 20100000 + index * 64 + int(offset) for offset, address, _ in rows), field
        found[field] = b"".join(int(bits, 16).to_bytes(8, "little") for _, _, bits in rows).decode("ascii")
    return found


def vector_image_digest(source, index):
    block = re.search(rf"\(defn- kg-vector-{index} \[\] :i64\n(.*?)(?=\n;; case |\n;; The Kotoba native gate)", source, re.S)
    assert block, f"missing kg-vector-{index}"
    words = re.findall(r"h1_\d+ \(kc-word \(\+ p \d+\) 0x([0-9a-f]+) 8\)", block[1])
    assert len(words) == 8, f"case {index}: expected eight image hash words"
    return b"".join(int(word, 16).to_bytes(8, "little") for word in words).decode("ascii")


def update_controller_pin(source, index, digest):
    words = encode_words(digest)
    for offset, word in zip(range(0, 64, 8), words):
        address = 20100000 + index * 64 + offset
        pattern = re.compile(rf"(h{index}_{offset} \(kc-word \(\+ \(kc-g\) {address}\) )0x[0-9a-f]+( 8\))")
        source, count = pattern.subn(rf"\g<1>{word}\g<2>", source)
        assert count == 1, f"controller pin {index}:{offset} update count {count}"
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--head", required=True, help="exact Amu commit that produced the observer artifact")
    args = parser.parse_args()
    assert args.head == subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                       check=True, capture_output=True, text=True).stdout.strip()

    observations = json.loads(args.observations.read_text())
    policy_path = ROOT / "seed/cdci/policy.json"
    policy = json.loads(policy_path.read_text())
    original_policy = dict(policy)
    cases = json.loads((ROOT / "seed/static-cases.json").read_text())["cases"]
    assert observations["schema"] == "amu.early-native-kotoba24.v1"
    assert observations["producerSHA256"] == json.loads((ROOT / "native-product.json").read_text())["image"]["sha256"]
    assert observations["observerSourceSHA256"] == sha(ROOT / "scripts/seed/check-native-kotoba-early.py")
    assert observations["fixtureSHA256"] == sha(ROOT / "seed/static-cases.json")
    assert observations["fixtureSHA256"] == re.search(r"Canonical fixture SHA256 ([0-9a-f]{64})", (ROOT / "seed/cdci/kotoba-gate.kotoba").read_text())[1]
    combined = b"".join((ROOT / "seed/cdci" / name).read_bytes()
                        for name in ("entry.kotoba", "runtime.kotoba", "kotoba-gate.kotoba"))
    assert sha_bytes(combined) == policy["kotobaGateSourceSHA256"]
    assert observations["gateImageSHA256"] == policy["kotobaNativeGateSHA256"]
    assert len(cases) == len(observations["caseArtifacts"]) == len(observations["caseRuntimeObservations"]) == 24
    failures = [row for row in observations["caseRuntimeObservations"] if not row.get("matchesReference")]
    assert not failures, f"native case runtime mismatch: {failures}"
    native_gate = [row for row in observations["calls"] if row["name"] == "native-complete24"]
    assert len(native_gate) == 1 and native_gate[0]["exit"] == 2, "expected the diagnosed stale-image-pin gate refusal"
    assert (args.observations.parent / "native-complete24.stderr").read_bytes() == b"CDCI:E4002\n"

    gate_path = ROOT / "seed/cdci/kotoba-gate.kotoba"
    gate = gate_path.read_text()
    old_vectors = []
    evidence_rows = []
    for index, (case, artifact, observed) in enumerate(zip(cases, observations["caseArtifacts"], observations["caseRuntimeObservations"])):
        assert case["name"] == artifact["name"] == observed["name"]
        assert artifact["sourceSHA256"] == sha_bytes(case["source"].encode())
        assert artifact["imageBytes"] > 0 and re.fullmatch(r"[0-9a-f]{64}", artifact["imageSHA256"])
        assert observed["exit"] == observed["expectedExit"] == case["reference"]["exit"]
        assert observed["remainingFuel"] == observed["expectedRemainingFuel"] == case["reference"]["remainingFuel"]
        expected_result = case["result"] if case["reference"]["exit"] == 0 else None
        assert observed["expectedResult"] == expected_result
        if expected_result is not None:
            assert observed["result"] == expected_result
        block = re.search(rf"\(defn- kg-vector-{index} \[\] :i64\n(.*?)(?=\n;; case |\n;; The Kotoba native gate)", gate, re.S)
        assert block
        embedded_source = "".join(bytes.fromhex(f"{int(x, 16):016x}")[::-1].decode("ascii") for x in
                                   re.findall(r"h0_\d+ \(kc-word \(\+ p \d+\) 0x([0-9a-f]+) 8\)", block[1]))
        assert embedded_source == artifact["sourceSHA256"], f"embedded source pin mismatch in case {index}"
        old_vectors.append((index, case["name"], artifact["imageSHA256"]))
        evidence_rows.append(dict(index=index, name=case["name"], sourceSHA256=artifact["sourceSHA256"],
                                  imageSHA256=artifact["imageSHA256"], imageBytes=artifact["imageBytes"],
                                  exit=observed["exit"], result=observed["result"],
                                  remainingFuel=observed["remainingFuel"]))
        gate = replace_vector(gate, index, artifact["imageSHA256"])

    gate_source = sha_bytes((ROOT / "seed/cdci/entry.kotoba").read_bytes()
                            + (ROOT / "seed/cdci/runtime.kotoba").read_bytes()
                            + gate.encode())
    for index, case, digest in old_vectors:
        assert vector_image_digest(gate, index) == digest, (case, index)
    policy["kotobaGateSourceSHA256"] = gate_source
    policy["note"] = (f"The complete24 case image vectors were regenerated from exact-head native x86 run {args.run_id} "
                       f"({args.head}); all source identities and expected result/exit/fuel tuples remain unchanged. "
                       "The Kotoba gate image pin is pending exact-head selfhost rebuild and must be updated from its receipt.")
    controller_path = ROOT / "seed/cdci/controller.kotoba"
    controller = controller_path.read_text()
    before = controller_pin_metadata(controller)
    assert all(before[key] == original_policy[key] for key in before), "controller pins differ from original policy before source digest refresh"
    controller = update_controller_pin(controller, 4, gate_source)
    after = controller_pin_metadata(controller)
    for key in before:
        expected = gate_source if key == "kotobaGateSourceSHA256" else policy[key]
        assert after[key] == expected, (key, after[key], expected)
    evidence = dict(schema="amu.native-kotoba24-image-repin.v1", amuHead=args.head,
                    workflowRunId=args.run_id,
                    workflowRunUrl=f"https://github.com/kotoba-lang/amu/actions/runs/{args.run_id}",
                    producerSHA256=observations["producerSHA256"],
                    observerSourceSHA256=observations["observerSourceSHA256"],
                    fixtureSHA256=observations["fixtureSHA256"],
                    priorGateImageSHA256=observations["gateImageSHA256"],
                    priorGateExit=native_gate[0]["exit"],
                    allNativeRuntimeTuplesMatched=True,
                    sourceDigestsUnchanged=True,
                    expectedResultExitFuelUnchanged=True,
                    refreshedImagePins=evidence_rows,
                    kotobaGateSourceSHA256=gate_source,
                    kotobaNativeGateSHA256Pending=True)
    evidence_path = ROOT / "seed/cdci/evidence/complete24-image-repin-20261103.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(gate)
    policy_path.write_text(json.dumps(policy, indent=2) + "\n")
    controller_path.write_text(controller)
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
    print("REFRESHED_NATIVE_KOTOBA24_IMAGE_PINS", len(evidence_rows), "gate source", gate_source)
    print("EVIDENCE", evidence_path)


if __name__ == "__main__":
    main()
