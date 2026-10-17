#!/usr/bin/env python3
"""Restore tw-entry's original four-wide group checks after the lane-skip probe."""
import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "seed/41-a64gen.kotoba"
WORD_COUNTS = (128, 128, 128, 32)
LANE_SKIP = (0x373801F3, 0x373801F4, 0x373801F5, 0x373801F6)
OLD_GROUP_CHECKS = (
    (0x8A140271, 0x8A150231, 0x8A160231, 0x37381631),
    (0x8A140271, 0x8A150231, 0x8A160231, 0x37380EB1),
    (0x8A140271, 0x8A150231, 0x8A160231, 0x37380731),
)
CURRENT_COMMENT = (
    ";; Four-wide early stop: retain the root all-leaf check, then test each lane\n"
    ";; before walk levels two through four. A leaf lane skips its next 14-word body;\n"
    ";; all four walks still reach the common commit validation in their original order.\n"
    ";; Raw direct branches crossing these insertions are relocated with the added words."
)
RESTORED_COMMENT = (
    ";; Four-wide early stop: test whether x19..x22 are all leaves after each of\n"
    ";; the first four walk-level groups. TBNZ reaches common commit validation.\n"
    ";; Raw direct branches crossing these insertions are relocated with the added words."
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=SOURCE)
    args = ap.parse_args()
    text = args.source.read_text()
    start = text.index("(defn- tw-entry ")
    end = text.index(";; a one-parameter non-leaf stage", start)
    block = text[start:end]
    matches = list(re.finditer(r"\(kb-words G \[([^\]]*)\]\)", block))
    if tuple(len(re.findall(r"0x([0-9A-Fa-f]+)", match.group(1))) for match in matches) != WORD_COUNTS:
        raise SystemExit("tw-entry word-array shape changed; refusing to restore")
    words = [int(word, 16) for match in matches for word in re.findall(r"0x([0-9A-Fa-f]+)", match.group(1))]
    if len(words) != 416 or tuple(words[126:130]) != (0x8A140271, 0x8A150231, 0x8A160231, 0x37381DB1):
        raise SystemExit("lane-skip source is absent or root check changed; refusing to restore")

    restored = list(words[:186])
    for group, start_index in zip(OLD_GROUP_CHECKS, (186, 246, 306)):
        segment = words[start_index:start_index + 60]
        if len(segment) != 60:
            raise SystemExit("lane-skip block length changed; refusing to restore")
        restored.extend(group)
        for lane in range(4):
            lane_start = lane * 15
            if segment[lane_start] != LANE_SKIP[lane]:
                raise SystemExit("lane-skip branch pattern changed; refusing to restore")
            restored.extend(segment[lane_start + 1:lane_start + 15])
    restored.extend(words[366:])
    if len(restored) != 416:
        raise SystemExit("restored code size changed")

    rewritten = block
    offset = 0
    offsets = (0, 128, 256, 384)
    for match, offset, count in reversed(list(zip(matches, offsets, WORD_COUNTS))):
        values = restored[offset:offset + count]
        literal = " ".join(f"0x{word:08X}" for word in values)
        rewritten = rewritten[:match.start()] + f"(kb-words G [{literal}])" + rewritten[match.end():]
    result = text[:start] + rewritten + text[end:]
    if result.count(CURRENT_COMMENT) != 1:
        raise SystemExit("lane-skip source comment changed; refusing to restore")
    result = result.replace(CURRENT_COMMENT, RESTORED_COMMENT, 1)
    args.source.write_text(result)
    print(f"restored original four-wide checks in {args.source}; 416 words preserved")


if __name__ == "__main__":
    main()
