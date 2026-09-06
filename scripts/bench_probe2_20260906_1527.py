import os, subprocess, time, json, glob

out = {}
# look for staged binaries in /private/tmp
pat = ['/private/tmp/*hc2*', '/private/tmp/*clang*', '/private/tmp/*kernel*',
       '/private/tmp/jb_imod_control*', '/private/tmp/*.bin', '/private/tmp/*.dylib',
       '/private/tmp/*.c', '/private/tmp/*.kexe']
found = {}
for p in pat:
    found[p] = glob.glob(p)
out['tmp_artifacts'] = found

samples = []
t0 = time.time()
try:
    for i in range(6):
        r = subprocess.run(['/usr/sbin/sysctl','-n','vm.loadavg'],
                           capture_output=True, text=True)
        samples.append(r.stdout.strip())
        time.sleep(3)
    out['samples'] = samples
    out['elapsed_s'] = round(time.time()-t0, 1)
except Exception as e:
    out['samples_error'] = repr(e)

outpath = '/private/tmp/bench_probe2_out.txt'
with open(outpath, 'w') as f:
    f.write(json.dumps(out, indent=2))
print('WROTE', outpath, 'exit-clean')