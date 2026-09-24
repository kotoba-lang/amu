import os
hits = []
for root, dirs, files in os.walk('~/github/com-junkawasaki/orgs/kotoba-lang/amu'):
    dirs[:] = [d for d in dirs if d not in ('node_modules', '.git')]
    for f in files:
        if f.endswith('.cljk'):
            hits.append(os.path.join(root, f))
print('\n'.join(hits[:20]) or 'NONE')
