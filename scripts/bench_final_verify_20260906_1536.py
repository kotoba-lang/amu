path = '/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md'
txt = open(path).read()
lines = txt.splitlines()
collect = []
for i, l in enumerate(lines):
    if l.startswith('| H-C2 | the remaining ~4.4% vs Clang'):
        collect.append('ROW_LINE=' + str(i+1))
        collect.append('ROW_TAIL=' + l[-650:])
        break
collect.append('COUNT_15:31=' + str(txt.count('2026-09-06 15:31 JST bench tick')))
collect.append('COUNT_15:34=' + str(txt.count('2026-09-06 15:34 JST bench tick preflight')))
open('/private/tmp/final_verify.txt','w').write('\n'.join(collect))
print('WROTE')