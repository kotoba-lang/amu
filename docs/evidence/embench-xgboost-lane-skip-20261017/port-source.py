#!/usr/bin/env python3
"""Port the exact xgboost lane-skip prototype into tw-entry's word stream."""
import argparse
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "seed/41-a64gen.kotoba"
WORD_COUNTS = (128, 128, 128, 32)
GROUP_CHECK = (0x8A140271, 0x8A150231, 0x8A160231)
OLD_GROUP_CHECKS = {
    186: (*GROUP_CHECK, 0x37381631),
    246: (*GROUP_CHECK, 0x37380EB1),
    306: (*GROUP_CHECK, 0x37380731),
}
LANE_SKIP = (0x373801F3, 0x373801F4, 0x373801F5, 0x373801F6)
BASE_COMMENT = (
    ";; Four-wide early stop: test whether x19..x22 are all leaves after each of\n"
    ";; the first four walk-level groups. TBNZ reaches common commit validation.\n"
    ";; Raw direct branches crossing these insertions are relocated with the added words."
)
LANE_COMMENT = (
    ";; Four-wide early stop: retain the root all-leaf check, then test each lane\n"
    ";; before walk levels two through four. A leaf lane skips its next 14-word body;\n"
    ";; all four walks still reach the common commit validation in their original order.\n"
    ";; Raw direct branches crossing these insertions are relocated with the added words."
)


def extract(text):
    start = text.index("(defn- tw-entry ")
    end = text.index(";; a one-parameter non-leaf stage", start)
    block = text[start:end]
    matches = list(re.finditer(r"\(kb-words G \[([^\]]*)\]\)", block))
    arrays = []
    for match in matches:
        literals = re.findall(r"0x([0-9A-Fa-f]+)", match.group(1))
        arrays.append((match, [int(word, 16) for word in literals]))
    return start, end, block, arrays


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--apply", action="store_true", help="rewrite the source in place")
    args = ap.parse_args()
    text = args.source.read_text()
    start, end, block, arrays = extract(text)
    if tuple(len(words) for _, words in arrays) != WORD_COUNTS:
        raise SystemExit("tw-entry word-array shape changed; refusing to patch")
    words = [word for _, arr in arrays for word in arr]
    if len(words) != 416:
        raise SystemExit("tw-entry payload word count changed; refusing to patch")
    payload_hash = lambda seq: __import__("hashlib").sha256(
        b"".join(struct.pack("<I", word) for word in seq)
    ).hexdigest()
    lane_positions = tuple(range(186, 366, 15))
    already_patched = all(words[pos] == LANE_SKIP[(n % 4)] for n, pos in enumerate(lane_positions))
    if already_patched and tuple(words[126:130]) == (*GROUP_CHECK, 0x37381DB1):
        print(f"source already contains lane-skip stream; transformed_words=416 sha256={payload_hash(words)}")
        return
    if tuple(words[126:129]) != GROUP_CHECK:
        raise SystemExit("root all-leaf check changed; refusing to patch")
    if any(tuple(words[pos:pos + 4]) != expected for pos, expected in OLD_GROUP_CHECKS.items()):
        raise SystemExit("one of the three level group checks changed; refusing to patch")

    deep_levels = (190, 250, 310)
    replacement = list(words[:130]) + list(words[130:186])
    for level_start in deep_levels:
        for lane in range(4):
            replacement.append(LANE_SKIP[lane])
            body_start = level_start + lane * 14
            replacement.extend(words[body_start:body_start + 14])
    replacement.extend(words[366:])
    if len(replacement) != len(words):
        raise SystemExit("fixed-size payload invariant failed")
    if replacement[126:130] != words[126:130]:
        raise SystemExit("root all-leaf check was not preserved")

    # Keep the existing four literal boundaries to minimize unrelated changes.
    rewritten = block
    for (match, _), offset, count in reversed(list(zip(arrays, (0, 128, 256, 384), WORD_COUNTS))):
        literal = " ".join(f"0x{word:08X}" for word in replacement[offset:offset + count])
        old = match.group(0)
        new = f"(kb-words G [{literal}])"
        rewritten = rewritten[:match.start()] + new + rewritten[match.end():]
    result = text[:start] + rewritten + text[end:]
    if result.count(BASE_COMMENT) != 1:
        raise SystemExit("four-wide source comment changed; refusing to patch")
    result = result.replace(BASE_COMMENT, LANE_COMMENT, 1)

    if not args.apply:
        print(f"source unchanged; transformed_words=416 sha256={payload_hash(replacement)}")
        return
    if text != args.source.read_text():
        raise SystemExit("source changed while preparing patch")
    args.source.write_text(result)
    print(f"patched {args.source}; transformed_words=416 sha256={payload_hash(replacement)}")


if __name__ == "__main__":
    main()
