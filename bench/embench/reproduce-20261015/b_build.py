#!/usr/bin/env python3
"""Level (b) BUILD: public bootstrap -> fixed-point compiler G* of the measured source -> the 19 measured images, byte for byte.

  python3 bench/embench/reproduce-20261015/b_build.py --out <new-empty-dir> [--skip-bootstrap-check]

Chain (all inputs are files of public commits of this repository, checked by SHA-256):
  0. loader  = clang -std=c11 -O2 seed/bootstrap/adopted-loader-20261012.c
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
    ap.add_argument('--skip-bootstrap-check', action='store_true', help='skip step 1 (saves one compile)')
    a = ap.parse_args()
    R.require_macos_arm64()
    pins = R.load('expected/build-inputs.json'); exp_img = R.load('expected/measured-images.json')
    chain_pins = R.load('expected/compiler-chain.json') if (R.PKG / 'expected/compiler-chain.json').exists() else None
    out = R.fresh_dir(a.out); host = out / 'host'; host.mkdir()
    report = dict(level='b-build', started=time.time(), steps=[], ok=False)
    def save(): (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    def step(name, **kw): report['steps'].append(dict(name=name, **kw)); save(); print(name, json.dumps(kw)[:300], flush=True)
    # ---- 0. pinned public inputs
    loader_src = R.REPO / 'seed/bootstrap/adopted-loader-20261012.c'; adopted = R.REPO / 'seed/bootstrap/adopted-20261012.bin'
    assert R.sha_file(loader_src) == pins['adoptedLoaderSourceSHA256'], 'loader source pin'
    assert R.sha_file(adopted) == pins['adoptedImageSHA256'], 'adopted bootstrap image pin'
    loader = R.build_loader(loader_src, host / 'kexe-loader'); step('loader-built', loaderSourceSHA256=pins['adoptedLoaderSourceSHA256'])
    u_adopted, _ = R.unity(pins['adoptedSourceCommit']); assert R.sha(u_adopted) == pins['adoptedUnitySHA256'], 'adopted unity pin'
    u_a, _ = R.unity(pins['adoptedSourceCommit'], {'seed/00-ns.kotoba': (pins['measuredSourceCommit'], 'seed/00-ns.kotoba')})
    assert R.sha(u_a) == pins['stageAUnitySHA256'], 'stage-A unity pin'
    s, _ = R.unity(pins['measuredSourceCommit']); assert R.sha(s) == pins['measuredUnitySHA256'], 'measured unity pin'
    step('sources-pinned', adoptedUnity=R.sha(u_adopted), stageAUnity=R.sha(u_a), measuredUnity=R.sha(s))
    # ---- 1. the public bootstrap is the fixed point of its own source
    if not a.skip_bootstrap_check:
        r = R.build_compiler(loader, adopted, u_adopted, out / 'step1-adopted-self', 'adopted-self')
        assert r['ok'] and r['native']['sha256'] == pins['adoptedImageSHA256'], ('BOOTSTRAP_NOT_A_FIXED_POINT', r)
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
    d = out / 'step4-images'; d.mkdir(); rows = []
    for w, e in sorted(exp_img.items()):
        src = (R.PKG / 'ports' / ('official-' + w + '.kotoba')).read_bytes(); assert R.sha(src) == e['sourceSHA256'], ('port source pin', w)
        r = R.compile_port(loader, gstar, src, d, 'official-' + w)
        same = r['native']['sha256'] == e['native']['sha256'] and r['kseed']['sha256'] == e['kseed']['sha256'] and r['exports'] == e['exports']
        rows.append(dict(workload=w, native=r['native'], kseed=r['kseed'], identicalToMeasured=same)); print('%-15s %s %s' % (w, r['native']['sha256'][:16], 'IDENTICAL' if same else 'DIFFERS'), flush=True)
    report.update(chain=chain, measuredCompilerG1=pins['measuredCompilerSHA256'], images=rows,
                  imagesIdenticalToMeasured=sum(r['identicalToMeasured'] for r in rows), ok=all(r['identicalToMeasured'] for r in rows), ended=time.time())
    save()
    print('LEVEL_B', 'PASS' if report['ok'] else 'FAIL', 'G*', chain['Gstar'], 'images identical %d/19' % report['imagesIdenticalToMeasured'])
    sys.exit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()
