#!/usr/bin/env python3
# BOOTSTRAP-TOOL: unchanged upstream C bodies and paired Kotoba port timings.
import hashlib, json, math, pathlib, re, statistics, subprocess, sys, time

root = pathlib.Path(sys.argv[1]).resolve()
up = root / 'upstream'
out = root / 'c-comparison'
recalibrate = len(sys.argv) > 2 and sys.argv[2] == '--recalibrate-c'
if recalibrate:
    previous = json.loads((out / 'rows.json').read_text())
    (out / 'initial-rows.json').write_text(json.dumps(previous, indent=2)+'\n')
    (out / 'status.txt').unlink(missing_ok=True)
else:
    out.mkdir(exist_ok=False)
def run(args):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=120)
    if p.returncode:
        raise RuntimeError(str(args) + '\n' + p.stdout + p.stderr)
    return p.stdout
def load():
    return float(run(['sysctl', '-n', 'vm.loadavg']).split()[1])
def quiet():
    value = load()
    with (out / 'load.tsv').open('a') as f:
        f.write(f'{time.time()}\t{value}\n')
    if value > 4:
        raise RuntimeError(f'Quiet-host gate failed: {value}')
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

assert run(['git', '-C', up, 'rev-parse', 'HEAD']).strip() == '09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'
board = out / 'boardsupport.c'
board.write_text('''#include <stdint.h>
#include <stdio.h>
#include <time.h>
static uint64_t start;
static uint64_t now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return (uint64_t)t.tv_sec * 1000000000 + t.tv_nsec; }
void initialise_board(void) {}
void start_trigger(void) { start = now(); }
void stop_trigger(void) { printf("%llu\\n", (unsigned long long)(now() - start)); }
''')
baseline = json.loads((up / 'baseline-data/speed.json').read_text())
qual = json.loads((root / 'results/r6m/qualification.json').read_text())
rows = []
manifest = {str(p.relative_to(up)):sha(p) for folder in ['src','support','baseline-data'] for p in (up/folder).rglob('*') if p.is_file()}
for w in qual['workloads']:
    name = w['workload']
    sources = sorted((up / 'src' / name).glob('*.c'))
    lsf = int(next(re.search(r'#define\s+LOCAL_SCALE_FACTOR\s+(\d+)', p.read_text()).group(1) for p in sources if re.search(r'#define\s+LOCAL_SCALE_FACTOR\s+(\d+)', p.read_text())))
    exe = out / name
    def build(gsf):
        command = ['clang', '-O2', '-std=gnu11', '-DWARMUP_HEAT=1', f'-DGLOBAL_SCALE_FACTOR={gsf}', '-I', up/'support', '-I', up/'src'/name, *sources, up/'support/main.c', up/'support/beebsc.c', board, '-lm', '-o', exe]
        run(command)
        with (out/'build-commands.jsonl').open('a') as f: f.write(json.dumps([str(x) for x in command])+'\n')
    if recalibrate:
        prior = next(r for r in previous if r['workload'] == name)
        pilot = max(statistics.median(prior['c_ns']) / prior['global_scale_factor'], 1)
    else:
        build(1)
        pilot = max(int(run([exe]).strip()), 1)
    # Per-program scale is disclosed. It follows the upstream score formula,
    # but does not pretend to be a single global-scale official-driver run.
    gsf = max(1, round(4e9 / pilot))
    build(gsf)
    csamples = []
    for index in range(5):
        quiet(); elapsed = int(run([exe]).strip()); quiet()
        csamples.append(elapsed)
    row = {'workload':name, 'fidelity':w['fidelity'], 'local_scale_factor':lsf, 'global_scale_factor':gsf, 'c_ns':csamples, 'c_sha256':sha(exe), 'c_correct':True, 'c_ns_per_body':statistics.median(csamples)/(lsf*gsf), 'c_relative_speed':baseline[name]/(statistics.median(csamples)/1e6)*gsf}
    if recalibrate and 'kotoba_samples' in prior:
        row['kotoba_samples'] = prior['kotoba_samples']
        row['kotoba_ns_per_correctness_call'] = prior['kotoba_ns_per_correctness_call']
        row['kotoba_time_over_c_body'] = row['kotoba_ns_per_correctness_call']/row['c_ns_per_body']
    elif w['fidelity'] == 'full-correctness-translation':
        raw = root/'results/r6m'/name/f'{name}.bin'
        assert sha(raw) == w['raw_code_sha256']
        calls = max(1, round(4e9 / statistics.median(s['elapsedNanoseconds'] for s in w['execution'])))
        native = []
        for index in range(5):
            quiet()
            sample = json.loads(run([root/'runner', 'raw', raw, w['offset'], 'aarch64', 0, calls, 1, 16777216]))
            quiet()
            assert sample['result'] == 1 and sample['calls'] == calls and sample['warmupCalls'] == 1
            native.append(sample)
        row['kotoba_samples'] = native
        row['kotoba_ns_per_correctness_call'] = statistics.median(s['elapsedNanoseconds']/s['calls'] for s in native)
        row['kotoba_time_over_c_body'] = row['kotoba_ns_per_correctness_call']/row['c_ns_per_body']
    rows.append(row)
    (out/'rows.json').write_text(json.dumps(rows, indent=2)+'\n')
    print(name, 'PASS', flush=True)
assert manifest == {str(p.relative_to(up)):sha(p) for folder in ['src','support','baseline-data'] for p in (up/folder).rglob('*') if p.is_file()}
summary = {'upstream_commit':run(['git','-C',up,'rev-parse','HEAD']).strip(), 'compiler':run(['clang','--version']), 'host':run(['hostname']), 'c_official_driver_run':False, 'kotoba_official_score':None, 'reason':'C uses per-program calibrated scale; Kotoba ports omit ten full upstream bodies and time correctness exports including verification and ABI resets.', 'c_upstream_formula_speed_geomean':math.exp(statistics.mean(math.log(r['c_relative_speed']) for r in rows)), 'paired_full_9_time_ratio_geomean':math.exp(statistics.mean(math.log(r['kotoba_time_over_c_body']) for r in rows if 'kotoba_time_over_c_body' in r)), 'source_sha256':manifest, 'rows':rows}
(out/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
(out/'status.txt').write_text('PASS: 19 unchanged C workloads; nine paired full correctness ports; five warmed samples; all sampled loads <= 4\n')
print('PASS', flush=True)
