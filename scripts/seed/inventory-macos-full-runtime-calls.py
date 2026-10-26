#!/usr/bin/env python3
"""Count direct ABI-v11 slot calls in one pinned Amu-generated main.

This observes the aarch64 codegen form `ldr x16, [x0, #slot]; blr x16`.
Other context reads, inline fast paths and dynamic calls are outside its scope.
"""

from collections import Counter
import hashlib
import json
import struct
import sys
from pathlib import Path


RAW_SHA256 = "164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e"
SLOT_NAMES = {
    56: "pair_new",
    112: "equal",
    120: "concat",
    128: "typed_cap_call",
    136: "substring",
    144: "code_point_at",
    160: "vector_conj",
    176: "vector_at",
    184: "vector_assoc",
    200: "vector_alloc",
    216: "index_of",
    240: "compare",
    352: "from_utf8",
    360: "bytes_from_vector",
}


def inventory(raw_path):
    raw = raw_path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != RAW_SHA256 or len(raw) % 4:
        raise ValueError(f"unexpected full compiler raw code: {actual}")
    words = struct.unpack(f"<{len(raw) // 4}I", raw)
    counts = Counter()
    for left, right in zip(words, words[1:]):
        if right == 0xd63f0200 and left & 0xffc003ff == 0xf9400010:
            counts[((left >> 10) & 0xfff) * 8] += 1
    if set(counts) != set(SLOT_NAMES):
        raise ValueError(f"unexpected direct runtime slots: {sorted(counts)}")
    return {
        "schema": "amu.macos-full-runtime-callsite-inventory.v1",
        "rawSha256": RAW_SHA256,
        "rawBytes": len(raw),
        "instructionPattern": "ldr x16, [x0, #slot]; blr x16",
        "scope": "Direct generated ABI-v11 runtime calls only; inline context access and dynamic calls unmeasured",
        "callSites": sum(counts.values()),
        "slots": [{"offset": slot, "name": SLOT_NAMES[slot], "callSites": counts[slot]}
                  for slot in sorted(counts)],
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: inventory-macos-full-runtime-calls.py RAW OUTPUT_JSON")
    result = inventory(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
