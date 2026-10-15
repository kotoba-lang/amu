#!/usr/bin/env python3
"""Level (b) BUILD: public bootstrap -> fixed-point compiler G* of the measured source -> the 19 measured images, byte for byte.

  python3 bench/embench/reproduce-20261015/b_build.py --out <new-empty-dir> [--round rounds/<name>.json] [--record <dir>]
                                                       [--skip-bootstrap-check]
Default round: rounds/m93-20261015.json (the published round, commit be7f0ce3, all pins present).

Chain (all inputs are files of public commits of this repository, checked by SHA-256):
  0. loader  = clang -std=c11 -O2 seed/bootstrap/adopted-loader-20261012.c (bootstrap files read from git at be7f0ce3)
  1. check   : adopted-20261012.bin compiles its own source (seed/MANIFEST unity of ffa4cfc1) to itself (public fixed point)
  2. stage A : adopted compiles U_A = the ffa4cfc1 unity with seed/00-ns.kotoba taken from be7f0ce3
               (that file differs from ffa4cfc1's only in the 22 generated memory-map constants: the larger TOK/NODE/
               SIR/CODE/FIX/OUT tables the measured compiler source needs). Result: compiler A (old code generator,
               new memory map). The adopted compiler cannot compile S directly: it stops with 'seed: E101 compiler table full: region 1'
               (the token table).
  3. G1 = A(S), G2 = G1(S), G3 = G2(S) where S = seed/MANIFEST unity of be7f0ce3 (the measured source).
     G2 == G3 is required: G* = G2 is the fixed point S(S).
  4. G* compiles the 19 official ports (ports/official-*.kotoba); every kseed, native image and export table must equal
     the measured ones (expected/measured-images.json).
Result (expected/compiler-chain.json): G1 = A(S) is already the fixed point -- G1 = G2 = G3 = G* = bcd70b24..., the very
compiler the round measured (it had been built by the development compiler m92, which yields the same bytes). Reason: T2
and the post-emission passes are size-budgeted off for programs as large as the compiler (t2-max-sir = 131072 SIR
records), so the compiler's own code comes from the backend that ffa4cfc1 and be7f0ce3 share."""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import repro_lib as R


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--round', help='round config (default rounds/m93-20261015.json, the published round)')
    ap.add_argument('--record', type=Path, help='new round: write build-inputs.json, compiler-chain.json and images.json here')
    ap.add_argument('--skip-bootstrap-check', action='store_true', help='skip step 1 (saves one compile)')
    a = ap.parse_args()
    R.require_macos_arm64()
    rnd = R.load_round(a.round); commit = rnd['sourceCommit']; W = R.round_workloads(rnd)
    pins_p, chain_p, img_p = R.round_path(rnd, 'buildInputs'), R.round_path(rnd, 'compilerChain'), R.round_path(rnd, 'imageTable')
    pins = json.loads(pins_p.read_text()) if pins_p else None
    chain_pins = json.loads(chain_p.read_text()) if chain_p else None
    exp_img = json.loads(img_p.read_text()) if img_p else None
    boot = R.bootstrap_pins(rnd.get('bootstrapCommit', R.BOOTSTRAP_COMMIT))
    if pins: assert all(pins[k] == v for k, v in boot.items() if k in pins), 'round pins disagree with the bootstrap adoption receipt'
    out = R.fresh_dir(a.out); host = out / 'host'; host.mkdir()
    report = dict(level='b-build', round=rnd['round'], sourceCommit=commit, started=time.time(), steps=[], ok=False)
    def save(): (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    def step(name, **kw): report['steps'].append(dict(name=name, **kw)); save(); print(name, json.dumps(kw)[:300], flush=True)
    # ---- 0. pinned public inputs
    loader_src = R.bootstrap_file('adopted-loader-20261012.c', host / 'adopted-loader-20261012.c', boot['bootstrapCommit'])
    adopted = R.bootstrap_file('adopted-20261012.bin', host / 'adopted-20261012.bin', boot['bootstrapCommit'])
    assert R.sha_file(loader_src) == boot['adoptedLoaderSourceSHA256'], 'loader source pin'
    assert R.sha_file(adopted) == boot['adoptedImageSHA256'], 'adopted bootstrap image pin'
    loader = R.build_loader(loader_src, host / 'kexe-loader'); step('loader-built', loaderSourceSHA256=boot['adoptedLoaderSourceSHA256'])
    u_adopted, _ = R.unity(boot['adoptedSourceCommit']); assert R.sha(u_adopted) == boot['adoptedUnitySHA256'], 'adopted unity pin'
    u_a, _ = R.unity(boot['adoptedSourceCommit'], {f: (commit, f) for f in rnd.get('stageAFromSource', ['seed/00-ns.kotoba'])})
    s, _ = R.unity(commit)
    if pins:
        assert R.sha(u_a) == pins['stageAUnitySHA256'], 'stage-A unity pin'
        assert pins['measuredSourceCommit'] == commit and R.sha(s) == pins['measuredUnitySHA256'], 'measured unity pin'
    step('sources-pinned', adoptedUnity=R.sha(u_adopted), stageAUnity=R.sha(u_a), measuredUnity=R.sha(s))
    # ---- 1. the public bootstrap is the fixed point of its own source
    if not a.skip_bootstrap_check:
        r = R.build_compiler(loader, adopted, u_adopted, out / 'step1-adopted-self', 'adopted-self')
        assert r['ok'] and r['native']['sha256'] == boot['adoptedImageSHA256'], ('BOOTSTRAP_NOT_A_FIXED_POINT', r)
        step('bootstrap-fixed-point', native=r['native']['sha256'])
    # ---- 2. stage A
    rA = R.build_compiler(loader, adopted, u_a, out / 'step2-stageA', 'A'); assert rA['ok'], ('STAGE_A_FAILED', rA)
    step('stage-A', native=rA['native']['sha256'], bytes=rA['native']['bytes'])
    # ---- 3. G1, G2, G3
    prod = Path(rA['native']['path']); gens = []
    for g in (1, 2, 3):
        r = R.build_compiler(loader, prod, s, out / ('step3-G%d' % g), 'G%d' % g); assert r['ok'], ('GEN_FAILED', g, r)
        gens.append(r); prod = Path(r['native']['path']); step('G%d' % g, native=r['native']['sha256'], bytes=r['native']['bytes'])
    fixed = gens[1]['native']['sha256'] == gens[2]['native']['sha256']
    step('fixed-point', G2=gens[1]['native']['sha256'], G3=gens[2]['native']['sha256'], G2equalsG3=fixed)
    assert fixed, 'G2 != G3: no fixed point'
    gstar = Path(gens[1]['native']['path'])
    chain = dict(stageA=rA['native']['sha256'], G1=gens[0]['native']['sha256'], Gstar=gens[1]['native']['sha256'])
    if chain_pins:
        for k, v in chain.items(): assert chain_pins[k] == v, ('CHAIN_PIN_MISMATCH', k, v, chain_pins[k])
    # ---- 4. compile the 19 ports with G*
    d = out / 'step4-images'; d.mkdir(); rows = []; table = {}
    for w in sorted(W):
        src = (R.PKG / rnd['ports'] / ('official-' + w + '.kotoba')).read_bytes()
        if exp_img: assert R.sha(src) == exp_img[w]['sourceSHA256'], ('port source pin', w)
        r = R.compile_port(loader, gstar, src, d, 'official-' + w)
        table[w] = dict(sourceSHA256=R.sha(src), native=r['native'], kseed=r['kseed'], exports=r['exports'])
        same = (r['native']['sha256'] == exp_img[w]['native']['sha256'] and r['kseed']['sha256'] == exp_img[w]['kseed']['sha256']
                and r['exports'] == exp_img[w]['exports']) if exp_img else None
        rows.append(dict(workload=w, native=r['native'], kseed=r['kseed'], identicalToMeasured=same))
        print('%-15s %s %s' % (w, r['native']['sha256'][:16], {True: 'IDENTICAL', False: 'DIFFERS', None: 'recorded'}[same]), flush=True)
    if a.record:
        a.record.mkdir(parents=True, exist_ok=True)
        (a.record / 'build-inputs.json').write_text(json.dumps(dict(boot, stageAUnitySHA256=R.sha(u_a), stageAUnityBytes=len(u_a), measuredSourceCommit=commit,
                                                                    measuredUnitySHA256=R.sha(s), measuredUnityBytes=len(s)), indent=1) + '\n')
        (a.record / 'compiler-chain.json').write_text(json.dumps(chain, indent=1) + '\n')
        (a.record / 'images.json').write_text(json.dumps(table, indent=1, sort_keys=True) + '\n')
    ok = all(r['identicalToMeasured'] for r in rows) if exp_img else True
    report.update(chain=chain, measuredCompilerG1=rnd.get('measuredCompilerSHA256'), images=rows,
                  imagesIdenticalToMeasured=sum(bool(r['identicalToMeasured']) for r in rows) if exp_img else None, ok=ok, ended=time.time())
    save()
    print('LEVEL_B', 'PASS' if ok else 'FAIL', 'round', rnd['round'], 'G*', chain['Gstar'],
          ('images identical %d/19' % report['imagesIdenticalToMeasured']) if exp_img else 'images recorded (no pins for this round)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
