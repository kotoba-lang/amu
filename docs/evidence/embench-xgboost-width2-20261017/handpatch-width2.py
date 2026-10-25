#!/usr/bin/env python3
"""Hand-patch the current width-four xgboost payload into a pair-major width-two prototype."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

BASE_SHA256 = "1c4aab16450da5b1deef581688d13b1995b87fa0238789cff8563ddc941a400d"
PATCH_START = 0x13C0
PATCH_END = 0x1780
LEVEL_BASES = (0x13D0, 0x14C0, 0x15B0, 0x16A0)
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
        if cmd == 0x19:  # LC_SEGMENT_64
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
    ap.add_argument("--input", type=Path, required=True, help="pinned width-four xgboost payload")
    ap.add_argument("--out", type=Path, required=True, help="new scratch output directory")
    args = ap.parse_args()
    original = args.input.read_bytes()
    if sha(original) != BASE_SHA256:
        raise SystemExit("width-four base image pin mismatch")
    if args.out.exists():
        raise SystemExit("output must be a new directory")
    args.out.mkdir(parents=True)

    def words_at(offset, count):
        return struct.unpack_from("<" + "I" * count, original, offset)

    def emit_walk(depth, lane):
        offset = LEVEL_BASES[depth] + lane * WALK_BYTES
        return "\n".join(f"  .word 0x{word:08x}" for word in words_at(offset, WORDS_PER_WALK))

    lines = [
        ".section __TEXT,__text,regular,pure_instructions",
        ".globl _width2_patch",
        "_width2_patch:",
        # The input nodes for all four lanes have already been computed. Walk
        # lanes 0/1 to completion before walking 2/3. Pair branches skip only
        # pure walk-step bodies; one final four-lane validation and commit stay
        # byte-for-byte unchanged at the end of the region.
        "  and x17, x19, x20",
        "  tbnz w17, #7, pair_b_root",
    ]
    for depth in range(3):  # early exits after depths 2, 3, and 4
        lines.extend((emit_walk(depth, 0), emit_walk(depth, 1),
                      "  and x17, x19, x20", "  tbnz w17, #7, pair_b_root"))
    lines.extend((emit_walk(3, 0), emit_walk(3, 1), "pair_b_root:",
                  "  and x17, x21, x22", "  tbnz w17, #7, commit"))
    for depth in range(3):
        lines.extend((emit_walk(depth, 2), emit_walk(depth, 3),
                      "  and x17, x21, x22", "  tbnz w17, #7, commit"))
    lines.extend((emit_walk(3, 2), emit_walk(3, 3), "commit:"))
    source = "\n".join(lines) + "\n"
    (args.out / "width2-patch.s").write_text(source)
    obj = args.out / "width2-patch.o"
    result = subprocess.run(["xcrun", "clang", "-target", "arm64-apple-macos14", "-c",
                             str(args.out / "width2-patch.s"), "-o", str(obj)],
                            capture_output=True, text=True)
    (args.out / "assembler.stdout").write_text(result.stdout)
    (args.out / "assembler.stderr").write_text(result.stderr)
    if result.returncode:
        raise SystemExit("AArch64 assembler failed; logs preserved")
    patch = macho_text(obj)
    expected_size = PATCH_END - PATCH_START
    if len(patch) != expected_size:
        raise SystemExit(f"patch block size {len(patch)} != fixed region size {expected_size}")
    patched = original[:PATCH_START] + patch + original[PATCH_END:]
    if len(patched) != len(original):
        raise SystemExit("hand-patch unexpectedly changed the payload size")
    output = args.out / "xgboost-width2.bin"
    output.write_bytes(patched)
    report = {
        "status": "PASS_HANDPATCH_BUILT",
        "baseImage": {"bytes": len(original), "sha256": sha(original)},
        "patchedImage": {"path": str(output), "bytes": len(patched), "sha256": sha(patched)},
        "patchRegion": {"start": PATCH_START, "end": PATCH_END, "bytes": expected_size},
        "walkBodies": {"perWalkWords": WORDS_PER_WALK, "walksReordered": 16,
                       "pairWidth": 2, "schedule": "lanes 0/1 through steps 2-5, then lanes 2/3 through steps 2-5"},
        "pairChecks": 8,
        "allFourLeafAndBoundsValidation": "unchanged at payload offset 0x1780",
        "compilerSourceChanged": False,
        "exactnessVerified": False,
        "performanceMeasured": False,
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
