#!/usr/bin/env python3
"""Level (b) BUILD: public bootstrap -> fixed-point compiler G* of the selected round -> its measured images, byte for byte.

  python3 bench/embench/reproduce-20261015/b_build.py --out <new-empty-dir> [--round rounds/<name>.json] [--record <dir>]
                                                       [--skip-bootstrap-check]
Default round: rounds/sa-m104-20261015.json (the corrected same-algorithm round).

The selected round config pins its source commit, bootstrap inputs, compiler chain and measured images. The build uses the
public native bootstrap, constructs the stage-A compiler when needed, iterates the selected source to a fixed point, then
rebuilds all 19 ports and compares their kseed, native image and export-table hashes with the round's recorded pins."""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import repro_lib as R


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--round', help='round config (default rounds/sa-m104-20261015.json)')
    ap.add_argument('--record', type=Path, help='new round: write build-inputs.json, compiler-chain.json and images.json here')
    ap.add_argument('--skip-bootstrap-check', action='store_true', help='skip step 1 (saves one compile)')
    a = ap.parse_args()
    R.require_macos_arm64()
    rnd = R.load_round(a.round); commit = rnd['sourceCommit']; W = R.round_workloads(rnd)
    pins_p, chain_p, img_p = R.round_path(rnd, 'buildInputs'), R.round_path(rnd, 'compilerChain'), R.round_path(rnd, 'imageTable')
    pins = json.loads(pins_p.read_text()) if pins_p else None
    chain_pins = json.loads(chain_p.read_text()) if chain_p else None
    exp_img = json.loads(img_p.read_text()) if img_p else None
    boot = R.bootstrap_pins()
    if pins: assert all(pins[k] == v for k, v in boot.items()), 'round pins disagree with the repository adoption receipt'
    out = R.fresh_dir(a.out); host = out / 'host'; host.mkdir()
    report = dict(level='b-build', round=rnd['round'], sourceCommit=commit, started=time.time(), steps=[], ok=False)
    def save(): (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    def step(name, **kw): report['steps'].append(dict(name=name, **kw)); save(); print(name, json.dumps(kw)[:300], flush=True)
    # ---- 0. pinned public inputs
    loader_src = R.REPO / 'seed/bootstrap/adopted-loader-20261012.c'; adopted = R.REPO / 'seed/bootstrap/adopted-20261012.bin'
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
