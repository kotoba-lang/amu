import subprocess, time

samples = []
try:
    for i in range(4):
        r = subprocess.run(['/usr/sbin/sysctl','-n','vm.loadavg'],
                           capture_output=True, text=True)
        samples.append(r.stdout.strip())
        time.sleep(3)
except Exception as e:
    samples.append(repr(e))

out = 'SAMPLE=' + ' | '.join(samples) + '\n'
# find the Standing honesty constraints marker and the H-C2 row context
path = '/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md'
txt = open(path).read()
lines = txt.splitlines()
# H-C2 row
for i, l in enumerate(lines):
    if l.startswith('| H-C2 |'):
        out += 'HC2_ROW_LINE=%d\n' % (i+1)
        out += 'HC2_ROW_TAIL=' + l[-500:] + '\n'
        break
# standing marker
idx = txt.rfind('## Standing honesty constraints')
out += 'STANDING_MARKER_IDX=%d\n' % idx
if idx >= 0:
    out += 'STANDING_CONTEXT=' + txt[idx:idx+300].replace('\n',' | ') + '\n'
with open('/private/tmp/bench_probe3_out.txt', 'w') as f:
    f.write(out)
print('WROTE')