#!/bin/bash
python3 - <<'PYEOF'
doc = '~/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/lang-cosientist.md'
add = open('/tmp/langcos/iter15.md').read()
src = open(doc).read()
if 'Iteration 15' in src:
    print('ALREADY-PRESENT')
else:
    open(doc,'a').write('\n' + add)
    print('APPENDED')
PYEOF
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu
git add docs/lang-cosientist.md
git commit -m "lang-cosientist iteration 15: some-thread canonical temp repair - iter 14 defect root-caused (temp-name drift from *loop-counter*/gensym), parity matrix fully green (some->/some->> x 0-let/1-let == hand twins), branch bot/lang-some-thread-canonical-20260906 @ac5381a pushed" > /tmp/langcos/t15-doccommit.txt 2>&1
echo "commit exit:$?" >> /tmp/langcos/t15-doccommit.txt
git log --oneline -1 >> /tmp/langcos/t15-doccommit.txt
