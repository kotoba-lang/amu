#!/usr/bin/env python3
"""Find the exact 104-word lp-entry machine-code body in pinned images."""
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "seed/41-a64gen.kotoba"
IMAGES = {
    "control": ROOT / "workspaces/codex/amu-sglib-input-table-20261017/attempt-1/profile-control/image.bin",
    "inputTableSourceCandidate": ROOT / "workspaces/codex/amu-sglib-input-table-20261017/attempt-1/candidate-build/official-sglib-combined.bin",
    "branchlessListMergeSourceCandidate": ROOT / "workspaces/codex/amu-sglib-list-branchless-20261017/attempt-1/candidate-build/official-sglib-combined.bin",
}

source = SOURCE.read_text()
block = source.split("(defn- lp-entry", 1)[1].split(";; ---- qp", 1)[0]
match = re.search(r"\(kb-words G \[(.*?)\]\)", block, re.S)
if not match:
    raise SystemExit("lp-entry kb-words payload not found")
words = [int(x, 16) for x in re.findall(r"0x[0-9A-Fa-f]+", match.group(1))]
signature = b"".join(struct.pack("<I", word) for word in words)
results = {}
for label, path in IMAGES.items():
    image = path.read_bytes()
    results[label] = {
        "path": str(path.relative_to(ROOT)),
        "imageSHA256": hashlib.sha256(image).hexdigest(),
        "signatureOffset": image.find(signature),
    }
print(json.dumps({
    "schema": "amu.embench.sglib-lp-kernel-fingerprint/v1",
    "sourceSHA256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "wordCount": len(words),
    "signatureBytes": len(signature),
    "images": results,
}, indent=2))
