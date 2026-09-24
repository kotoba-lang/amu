import os
names = sorted(os.listdir('/tmp'))
hits = [n for n in names if n.startswith('q9')]
print(hits)
for d in ('q9probe', 'q9probe2'):
    p = '/tmp/' + d
    if os.path.isdir(p):
        print(d, sorted(os.listdir(p)))
    else:
        print(d, 'MISSING')
