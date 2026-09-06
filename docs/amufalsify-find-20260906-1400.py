import re
path = 'docs/codegen-coscientist.md'
txt = open(path).read()
lines = txt.splitlines()
out = []
# hypothesis table rows (H-C2 primary) + H-E fixture references + recent falsify NEXT notes about H-C2 A/B method
for i, l in enumerate(lines, 1):
    if re.search(r'H-E |instruction-order|timed A/B|0x7fffffff|kexe-benchmark .*kernel |runtime-comparison.*kernel\.kotoba', l):
        out.append(f"{i}|{l}")
open('/tmp/amu-he.txt', 'w').write("\n".join(out) + f"\nTOTAL {len(lines)}\n")
