#!/usr/bin/env python3
"""scripts/seed/kir_extract.py <in.kexe> <out.kir> -- BOOTSTRAP-TOOL (test harness only, never in the seed's process tree).

Writes the `:program` value of a stage-0 :kotoba.kexe/v1 artifact (the KIR text, `{:format :kotoba.kir/v3|v4 ...}`)
byte for byte as it appears in the kexe, plus one newline. Stage-0 has no --emit-kir flag: `amu compile --target
aarch64-macos --output x.kexe` writes the KIR as the kexe's :program, which is what this cuts out (balanced brackets,
string-aware). The seed itself also accepts the whole kexe (`compile-kir x.kexe`), so this tool only exists to have the
bare KIR file for the byte counts and as the primary compile-kir input of scripts/seed/kir-gate.sh.
"""
import sys


def program_span(s):
    i = s.index(':program {') + len(':program ')
    depth, j, in_str = 0, i, False
    while True:
        c = s[j]
        if in_str:
            if c == '\\':
                j += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                return i, j + 1
        j += 1


def main():
    s = open(sys.argv[1], encoding='utf-8').read()
    a, b = program_span(s)
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write(s[a:b] + '\n')


if __name__ == '__main__':
    main()
