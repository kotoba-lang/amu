#!/usr/bin/env python3
"""Compile all pinned M104 ports with the isolated candidate selfhost G3."""
import hashlib, json, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('worktrees/codex/amu-crossdomain-coscientist-20261016')
PKG=ROOT/'bench/embench/reproduce-20261015'
sys.path.insert(0,str(PKG/'tools'))
import repro_lib as R
BUILD=HERE/'build'
COMPILER=BUILD/'artifacts/G3.bin'
LOADER=BUILD/'host/kexe-loader'
OUT=HERE/'all19-images'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    R.require_macos_arm64()
    receipt=json.loads((BUILD/'build-report.json').read_text())
    if receipt.get('status')!='PASS_G1_TO_GN_BYTE_IDENTICAL_FIXED_POINT' or sha(COMPILER)!=receipt.get('fixedPointSHA256'):
        raise SystemExit('candidate G3 is not fixed-point verified')
    if OUT.exists(): raise SystemExit('preserving existing all19-images directory')
    rnd=R.load_round('rounds/sa-m104-20261015.json')
    W=R.round_workloads(rnd)
    image_table=json.loads(R.round_path(rnd,'imageTable').read_text())
    OUT.mkdir()
    report={'status':'RUNNING','round':rnd['round'],'candidateCompilerSHA256':sha(COMPILER),'ports':[]}
    (HERE/'all19-build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    for name in sorted(W):
        source=PKG/rnd['ports']/('official-'+name+'.kotoba')
        src_sha=sha(source)
        if src_sha!=image_table[name]['sourceSHA256']: raise SystemExit('source pin mismatch: '+name)
        result=R.compile_port(LOADER,COMPILER,source.read_bytes(),OUT,'official-'+name)
        row={'workload':name,'sourceSHA256':src_sha,'kseed':result['kseed'],'native':result['native'],'exports':result['exports'],'identicalToM104Image':result['native']['sha256']==image_table[name]['native']['sha256'] and result['kseed']['sha256']==image_table[name]['kseed']['sha256'] and result['exports']==image_table[name]['exports']}
        report['ports'].append(row)
        (HERE/'all19-build-report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(name,row['native']['sha256'][:16],'IDENTICAL' if row['identicalToM104Image'] else 'DIFFERS',flush=True)
    report['identicalCount']=sum(x['identicalToM104Image'] for x in report['ports'])
    report['status']='PASS_COMPILED_ALL_19' if len(report['ports'])==19 else 'FAIL_PORT_COUNT'
    report['compiledAtUnix']=time.time()
    (HERE/'all19-build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('ALL19',report['status'],report['identicalCount'],'/19 identical to measured M104',flush=True)
if __name__=='__main__': main()
