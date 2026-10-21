#!/usr/bin/env python3
"""Prototype per-lane leaf skips in the current four-wide xgboost kernel."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

BASE_SHA256 = "1eac8f0f999f632bd2e33d5f7632674606ec38761976c83582f15288ca81ad65"
PATCH_START = 0x1668
PATCH_END = 0x1A28
LEVEL_BASES = (0x1678, 0x1768, 0x1858, 0x1948)
WORDS_PER_WALK = 14
WALK_BYTES = WORDS_PER_WALK * 4


def sha(data):
    return hashlib.sha256(data).hexdigest()


def macho_text(path):
    data = Path(path).read_bytes()
    if struct.unpack_from("<I", data)[0] != 0xFEEDFACF:
        raise SystemExit("assembler output is not a 64-bit little-endian Mach-O object")
    ncmds = struct.unpack_from("<I", data, 16)[0]
    offset = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", data, offset)
        if cmd == 0x19:
            nsects = struct.unpack_from("<I", data, offset + 64)[0]
            section_offset = offset + 72
            for i in range(nsects):
                sec = section_offset + i * 80
                sectname = data[sec:sec + 16].split(b"\0", 1)[0]
                segname = data[sec + 16:sec + 32].split(b"\0", 1)[0]
                size = struct.unpack_from("<Q", data, sec + 40)[0]
                fileoff, nreloc = struct.unpack_from("<II", data, sec + 48)[0], struct.unpack_from("<I", data, sec + 60)[0]
                if (segname, sectname) == (b"__TEXT", b"__text"):
                    if nreloc:
                        raise SystemExit("unexpected relocations in hand-patched instruction block")
                    return data[fileoff:fileoff + size]
        offset += cmdsize
    raise SystemExit("assembler output has no __TEXT,__text section")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True, help="pinned current M105 xgboost payload")
    ap.add_argument("--out", type=Path, required=True, help="new output directory")
    args = ap.parse_args()
    original = args.input.read_bytes()
    if sha(original) != BASE_SHA256:
        raise SystemExit("base image pin mismatch")
    if args.out.exists():
        raise SystemExit("output must be a new directory")
    args.out.mkdir(parents=True)

    def words_at(offset, count):
        return struct.unpack_from("<" + "I" * count, original, offset)

    def emit_words(offset, count):
        return "\n".join(f"  .word 0x{word:08x}" for word in words_at(offset, count))

    def emit_walk(depth, lane):
        offset = LEVEL_BASES[depth] + lane * WALK_BYTES
        return emit_words(offset, WORDS_PER_WALK)

    lines = [
        ".section __TEXT,__text,regular,pure_instructions",
        ".globl _lane_skip_patch",
        "_lane_skip_patch:",
        emit_words(PATCH_START, 4),  # preserve the root all-leaf exit
    ]
    lines.extend(emit_walk(0, lane) for lane in range(4))
    for depth in range(1, 4):
        for lane in range(4):
            lines.extend((
                f"  tbnz w{19 + lane}, #7, skip_d{depth}_l{lane}",
                emit_walk(depth, lane),
                f"skip_d{depth}_l{lane}:",
            ))
    source = "\n".join(lines) + "\n"
    (args.out / "lane-skip-patch.s").write_text(source)
    obj = args.out / "lane-skip-patch.o"
    result = subprocess.run(
        ["xcrun", "clang", "-target", "arm64-apple-macos14", "-c", str(args.out / "lane-skip-patch.s"), "-o", str(obj)],
        capture_output=True, text=True,
    )
    (args.out / "assembler.stdout").write_text(result.stdout)
    (args.out / "assembler.stderr").write_text(result.stderr)
    if result.returncode:
        raise SystemExit("AArch64 assembler failed; logs preserved")
    patch = macho_text(obj)
    expected_size = PATCH_END - PATCH_START
    if len(patch) != expected_size:
        raise SystemExit(f"patch size {len(patch)} != fixed region size {expected_size}")
    patched = original[:PATCH_START] + patch + original[PATCH_END:]
    output = args.out / "xgboost-lane-skip.bin"
    output.write_bytes(patched)
    report = {
        "status": "PASS_LANE_SKIP_HANDPATCH_BUILT",
        "baseImage": {"bytes": len(original), "sha256": sha(original)},
        "candidateImage": {"path": str(output), "bytes": len(patched), "sha256": sha(patched)},
        "patchRegion": {"start": PATCH_START, "end": PATCH_END, "bytes": expected_size},
        "layout": "root group exit; four-wide level one; then per-lane leaf skip before levels two through four",
        "perLaneChecks": 12,
        "checksReplaceGroupChecksAfterLevels": [1, 2, 3],
        "compilerSourceChanged": False,
        "exactnessVerified": False,
        "performanceMeasured": False,
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
