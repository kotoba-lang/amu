#!/usr/bin/env python3
"""Level (d) TIMING: a same-host Kotoba + C campaign under the round's protocol, producing the full-19 geometric mean of
ratio_w = (4/m_w) * K_ns / C_ns on YOUR machine.

  python3 bench/embench/reproduce-20261015/tools/fetch_upstream.py --dest <upstream-dir>
  python3 bench/embench/reproduce-20261015/d_timing.py --upstream <upstream-dir> --out <new-dir> [--round rounds/<name>.json]
                                                       [--images <dir>] [--workloads w1,w2]

Protocol (the upstream benchmark_speed.py driver, unchanged): the Embench speed driver with the selected round's target module
harness/kotoba/run_trigger.py (Kotoba, GSF 8192, n_w = LSF*8192*m_w) and harness/c/run_trigger.py (C, GSF 32768); warm-up 1,
sample 1; CPU admission: raw host idle >= 70 % before, raw idle and estimated background idle >= 70 % over the run; at most
3 attempts, retries only for CPU reasons; the first qualified attempt is selected (never the fastest); 0.5 s floor;
Kotoba exactness against the expected values at n_w. Kotoba campaign first, then C, in one session. No subset GM: a GM is
printed only when all 38 runs are accepted.

C binaries are built here from upstream with c/build_c.py (your clang), or pass --c-binaries <dir>. Kotoba images default to
images/ (or pass --images <b_build out>/step4-images).
EXPECTED SPREAD: the corrected recorded M104 result is 0.82130 on one Apple M4 host. Do not use the historical M93
0.79988 result as a same-algorithm comparison. Other hosts, clang versions, background load and thermal state change both
arms; expect a different GM, and per-workload ratios can move by 10 % or more. This remains an Embench-derived translated-
port comparison, not an official Embench score."""
import argparse, json, math, os, platform, shutil, statistics, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import repro_lib as R

UPSTREAM_COMMIT = '09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'
C_FLAGS = ['-O2', '-std=gnu11', '-DWARMUP_HEAT=1', '-DGLOBAL_SCALE_FACTOR=32768']


def require(condition, message):
    if not condition: raise SystemExit(message)


def verify_images(image_dir, rnd, workloads):
    """Bind every timed Kotoba image to this round's source, kseed, native and export pins."""
    image_table_path = R.round_path(rnd, 'imageTable')
    require(image_table_path is not None, 'selected round has no pinned image table')
    image_table = json.loads(image_table_path.read_text())
    require(set(image_table) == set(R.round_workloads(rnd)), 'round image table does not cover the selected round')
    for workload in workloads:
        candidates = [Path(image_dir) / (workload + '.kseed'), Path(image_dir) / ('official-' + workload + '.kseed')]
        matches = [path for path in candidates if path.is_file()]
        require(len(matches) == 1, '%s: expected one matching kseed in %s' % (workload, image_dir))
        kseed = matches[0]
        pin = image_table[workload]
        exports, native = R.kseed_parts(kseed.read_bytes())
        require(R.sha_file(kseed) == pin['kseed']['sha256'] and kseed.stat().st_size == pin['kseed']['bytes'],
                '%s: kseed differs from selected round pin' % workload)
        require(R.sha(native) == pin['native']['sha256'] and len(native) == pin['native']['bytes'],
                '%s: native image differs from selected round pin' % workload)
        require(exports == pin['exports'], '%s: exports differ from selected round pin' % workload)
        source = R.PKG / rnd['ports'] / ('official-' + workload + '.kotoba')
        require(R.sha_file(source) == pin['sourceSHA256'], '%s: round source differs from image-table pin' % workload)


def compiled_sources(upstream, workload):
    src = sorted((upstream / 'src' / workload).glob('*.c'))
    require(bool(src), '%s: upstream source set is empty' % workload)
    paths = [*src, upstream / 'support/main.c', upstream / 'support/beebsc.c']
    require(all(path.is_file() for path in paths), '%s: a required C source is missing' % workload)
    return paths


def source_custody_paths(upstream, workload):
    sources = compiled_sources(upstream, workload)
    headers = sorted((upstream / 'src' / workload).glob('*.h')) + sorted((upstream / 'support').glob('*.h'))
    return sorted(set([*sources, *headers]), key=lambda path: path.relative_to(upstream).as_posix())


def expected_c_argv_template(upstream, workload, sources):
    rels = [path.relative_to(upstream).as_posix() for path in sources]
    return ['<compiler>', *C_FLAGS, '-I', '<upstream>/support', '-I', '<upstream>/src/' + workload,
            *['<upstream>/' + rel for rel in rels], '<package>/c/boardsupport.c', '-lm', '-o', '<out>/' + workload + '/' + workload]


def expected_c_argv(compiler, upstream, root, workload, sources):
    return [compiler, *C_FLAGS, '-I', '<upstream>/support', '-I', '<upstream>/src/' + workload,
            *['<upstream>/' + path.relative_to(upstream).as_posix() for path in sources],
            '<package>/c/boardsupport.c', '-lm', '-o', '<out>/' + workload + '/' + workload]


def verify_c_binaries(binary_dir, upstream, workloads):
    """Require build_c.py's receipt, verified source custody, fixed -O2 recipe and matching binary hashes."""
    root = Path(binary_dir)
    receipt_path = root / 'build-c.json'
    require(receipt_path.is_file() and not receipt_path.is_symlink(),
            '--c-binaries requires build-c.json from c/build_c.py')
    receipt = json.loads(receipt_path.read_text())
    require(receipt.get('schemaVersion') == 2, 'unsupported or missing C build receipt schema')
    head = subprocess.run(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    require(head == UPSTREAM_COMMIT and receipt.get('upstreamCommit') == UPSTREAM_COMMIT,
            'C build receipt upstream commit does not match the pinned Embench source')
    changed = subprocess.run(['git', '-C', str(upstream), 'diff', '--quiet', 'HEAD', '--', 'src', 'support'])
    untracked = subprocess.run(['git', '-C', str(upstream), 'ls-files', '--others', '--exclude-standard', '--', 'src', 'support'],
                               capture_output=True, text=True, check=True).stdout.splitlines()
    require(changed.returncode == 0 and not [p for p in untracked if Path(p).suffix in {'.c', '.h'}],
            'pinned C source checkout is modified or has untracked C/header inputs')
    require(receipt.get('globalScaleFactor') == 32768, 'C build receipt has the wrong global scale factor')
    require(receipt.get('boardsupportSHA256') == R.sha_file(R.PKG / 'c/boardsupport.c'),
            'C build receipt boardsupport hash differs')
    compiler = receipt.get('compiler', {})
    compiler_path = compiler.get('path')
    require(isinstance(compiler_path, str) and Path(compiler_path).is_file() and os.access(compiler_path, os.X_OK),
            'C build receipt compiler is missing or not executable')
    version = subprocess.run([compiler_path, '--version'], capture_output=True, text=True, check=True).stdout
    require(compiler.get('version') == version, 'C build receipt compiler version differs from the current compiler')
    rows = receipt.get('rows', [])
    require({row.get('workload') for row in rows} == set(workloads) and len(rows) == len(workloads),
            'C build receipt workload set differs from this campaign')
    for row in rows:
        workload = row['workload']
        sources = compiled_sources(upstream, workload)
        source_hashes = {path.relative_to(upstream).as_posix(): R.sha_file(path)
                         for path in source_custody_paths(upstream, workload)}
        require(row.get('sourceHashes') == source_hashes, '%s: C build source custody differs from pinned upstream' % workload)
        require(row.get('argvTemplate') == expected_c_argv_template(upstream, workload, sources) and
                row.get('argv') == expected_c_argv(compiler_path, upstream, root, workload, sources),
                '%s: C build command is not the required -O2 recipe' % workload)
        binary = root / workload / workload
        require(binary.is_file() and not binary.is_symlink() and os.access(binary, os.X_OK),
                '%s: C binary is missing, symlinked, or not executable' % workload)
        require(R.sha_file(binary) == row.get('sha256') and binary.stat().st_size == row.get('bytes'),
                '%s: C binary hash or size differs from build receipt' % workload)


def setup_root(root, upstream, trigger):
    root.mkdir()
    shutil.copytree(upstream, root / 'upstream', ignore=shutil.ignore_patterns('.git'))
    shutil.copyfile(trigger, root / 'run_trigger.py'); shutil.copyfile(R.PKG / 'harness/darwin_cpu_idle.py', root / 'darwin_cpu_idle.py')
    (root / 'results/measured/src').mkdir(parents=True)


def drive(root, gsf):
    up = root / 'upstream'
    cmd = [sys.executable, str(up / 'benchmark_speed.py'), '--builddir', str(root / 'results/measured'), '--logdir', str(root / 'results/official-logs'),
           '--target-module', 'run_trigger', '--gsf', str(gsf), '--json-output', '--samples', '1']
    q = subprocess.run(cmd, env=dict(os.environ, PYTHONPATH=str(root)), cwd=up, capture_output=True, text=True, timeout=7200)
    (root / 'results/official.stdout').write_text(q.stdout); (root / 'results/official.stderr').write_text(q.stderr)
    return dict(driverExit=q.returncode, driverCommand=[str(c).replace(str(root), '<root>') for c in cmd])


def collect(root, names, gsf, mult, baseline):
    rows = {}
    for w in names:
        f = root / 'results/measured/raw' / (w + '.json')
        if not f.exists(): rows[w] = dict(accepted=False, reasons=['not-run (driver stopped)']); continue
        raw = json.loads(f.read_text()); sel = raw['selectedAttempt']
        s = raw['samples'][sel] if sel is not None else None
        rows[w] = dict(accepted=sel is not None, attempts=len(raw['samples']), reasons=[x['reasons'] for x in raw['samples']],
                       elapsedNs=s['elapsedNs'] if s else None, score=baseline[w] / (s['elapsedNs'] / 1e6) * gsf * mult.get(w, 1) if s else None)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--upstream', required=True, type=Path); ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--images', type=Path); ap.add_argument('--c-binaries', type=Path); ap.add_argument('--workloads')
    ap.add_argument('--host-model', help='optional user-reported host model to include in report.json')
    ap.add_argument('--round', help='round config (default rounds/sa-m104-20261015.json)')
    a = ap.parse_args(); R.require_macos_arm64()
    subprocess.run([sys.executable, str(R.PKG / 'tools/fetch_upstream.py'), '--dest', str(a.upstream), '--verify-only'], check=True)
    up = a.upstream.resolve()
    rnd = R.load_round(a.round); W = R.round_workloads(rnd); names = a.workloads.split(',') if a.workloads else sorted(W)
    require(len(names) == len(set(names)) and all(w in W for w in names), 'workload list has duplicates or unknown workloads')
    images = a.images or R.PKG / rnd['images']; exp_p = R.round_path(rnd, 'expectedAccounting')
    if not exp_p: raise SystemExit('this round has no expected values yet: derive them with c_reference.py --round ... --write <file>')
    verify_images(images, rnd, names)
    all_workloads = sorted(W)
    if a.c_binaries is not None: verify_c_binaries(a.c_binaries, up, all_workloads)
    out = R.fresh_dir(a.out)
    baseline = json.loads((up / 'baseline-data/speed.json').read_text()); mult = {w: W[w]['multiplier'] for w in W}
    report = dict(level='d-timing', round=rnd['round'], started=time.time(), workloads=names,
                  full19=len(names) == 19 and set(names) == set(W),
                  host=dict(platform=platform.platform(), architecture=platform.machine(), logicalCPUCount=os.cpu_count(),
                            userReportedModel=a.host_model),
                  protocol='round-specific protocol revision (see records/round/protocol-revision.txt)')
    def save(): (out / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    # C binaries
    cdir = a.c_binaries
    if cdir is None:
        subprocess.run([sys.executable, str(R.PKG / 'c/build_c.py'), '--upstream', str(up), '--out', str(out / 'c-build')], check=True); cdir = out / 'c-build'
        verify_c_binaries(cdir, up, all_workloads)
    # ---- Kotoba arm
    K = out / 'kotoba'; setup_root(K, up, R.PKG / 'harness/kotoba/run_trigger.py')
    shutil.copyfile(exp_p, K / 'expected-original-accounting.json')
    for w in names:
        e = W[w]; kseed = next(p for p in [Path(images) / (w + '.kseed'), Path(images) / ('official-' + w + '.kseed')] if p.is_file())
        exports, image = R.kseed_parts(kseed.read_bytes()); timer = R.build_timer(K / 'timers' / w, R.PKG / 'harness', image, exports, e)
        caps = R.caps_for(w, e['extraCaps']); d = K / 'results/measured/src' / w; d.mkdir()
        import shlex
        (d / w).write_text('#!/bin/sh\nexec env ' + ' '.join(shlex.quote(k + '=' + v) for k, v in caps.items()) + ' ' + shlex.quote(str(timer)) + ' ' + str(e['n']) + '\n'); (d / w).chmod(0o755)
    # R.fresh_dir() created this unique output root; a competing campaign cannot reuse it.
    report['kotoba'] = drive(K, 8192); report['kotoba']['rows'] = collect(K, names, 8192, mult, baseline); save()
    # ---- C arm (same session, after Kotoba)
    Cr = out / 'c'; setup_root(Cr, up, R.PKG / 'harness/c/run_trigger.py')
    for w in names:
        d = Cr / 'results/measured/src' / w; d.mkdir(); shutil.copyfile(Path(cdir) / w / w, d / w); (d / w).chmod(0o755)
    report['c'] = drive(Cr, 32768); report['c']['rows'] = collect(Cr, names, 32768, {}, baseline); save()
    kr, cr = report['kotoba']['rows'], report['c']['rows']
    ratios = {w: (4 / mult[w]) * kr[w]['elapsedNs'] / cr[w]['elapsedNs'] for w in names if kr[w]['accepted'] and cr[w]['accepted']}
    all38 = (report['full19'] and len(ratios) == 19 and
             report['kotoba'].get('driverExit') == 0 and report['c'].get('driverExit') == 0)
    report.update(ratios=ratios, acceptedKotoba=sum(r['accepted'] for r in kr.values()), acceptedC=sum(r['accepted'] for r in cr.values()),
                  geometricMean=math.exp(statistics.mean(math.log(v) for v in ratios.values())) if all38 else None,
                  note=None if all38 else 'NOT A FULL-19 RESULT: no geometric mean (no subset GM by protocol)', ended=time.time())
    save()
    for w in names:
        print('%-15s m_w %2d  Kotoba %s  C %s  ratio %s' % (w, mult[w], kr[w].get('elapsedNs') or kr[w]['reasons'], cr[w].get('elapsedNs') or cr[w]['reasons'],
              ('%.4f' % ratios[w]) if w in ratios else '-'))
    print('LEVEL_D', 'GM %.4f' % report['geometricMean'] if all38 else report['note'], 'accepted Kotoba %d/%d C %d/%d' % (report['acceptedKotoba'], len(names), report['acceptedC'], len(names)))


if __name__ == '__main__':
    main()
