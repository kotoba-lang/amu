path = '/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md'
txt = open(path).read()
marker = '2026-09-06 15:31 JST bench tick'
found = txt.count(marker)
lines = txt.splitlines()
n = len(lines)
hc2row = None
for i, l in enumerate(lines):
    if l.startswith('| H-C2 | the remaining ~4.4% vs Clang'):
        hc2row = i+1
        tail = l[-320:]
        break
out = 'COUNT_15:31=%d\nTOTAL_LINES=%d\nHC2_ROW=%s\nHC2_TAIL=%s\n' % (found, n, hc2row, tail)
open('/private/tmp/append_verify.txt', 'w').write(out)
print('WROTE')