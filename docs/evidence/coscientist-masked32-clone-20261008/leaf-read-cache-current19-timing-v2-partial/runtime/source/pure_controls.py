"""Synthetic only. Never reads old timing pools or invokes a host/API/process."""
import json
import math
from statistics_core import ARMS, PRNG, order, normalized, summarize, full_summary, paired_ci, need
from campaign_engine import next_calls, quiet_admission, run_finite_engine

def main():
    names = ['synthetic-%02d' % i for i in range(19)]
    zero = [{a: 100.0 for a in ARMS} for _ in range(30)]
    gain = [{'baseline': 120.0, 'candidate': 100.0, 'C': 110.0} for _ in range(30)]
    noise = [{'baseline': 120.0 + (40 if i % 2 else -40), 'candidate': 100.0, 'C': 110.0} for i in range(30)]
    z = summarize(zero, 'synthetic-v1', 'zero')
    need(not z['baselineAdoptionBenefit'] and z['stable'] and z['COrBetter'], 'zero-gain control')
    need(z['pairedCI95']['baseline/candidate']['lower95'] == 1.0, 'zero degenerate CI')
    a = summarize(gain, 'synthetic-v1', 'gain')
    need(a['baselineAdoptionBenefit'] and a['COrBetter'], 'adoption control')
    need(not summarize(gain, 'synthetic-v1', 'unchanged', False)['baselineAdoptionBenefit'], 'neutral attribution')
    need(not summarize(noise, 'synthetic-v1', 'noise')['baselineAdoptionBenefit'], 'noisy control')
    missing = full_summary({n: zero for n in names[:-1]}, names, 'synthetic-v1', set())
    need(missing['fixed19PairedGM'] is None and not missing['all19IndividualCOrBetter'], 'missing no subset GM')
    complete = full_summary({n: zero for n in names}, names, 'synthetic-v1', set())
    need(complete['all19IndividualCOrBetter'] and complete['fixed19PairedGM']['C/candidate']['lower95'] == 1, 'full19 zero-gain')
    for block in range(15):
        need(len({order('synthetic', block*6+i) for i in range(6)}) == 6, 'balanced six orders')
    need(normalized({a: (50000000, 2) for a in ARMS}, 2000)['candidate'] == 12500, 'body normalization')
    need(next_calls(3, 0) == 30 and next_calls(3, 300000000) == 3 and next_calls(100000000, 1) == 100000000, 'calibration clips')
    need(not quiet_admission({'elapsedNanoseconds': 50000000}, 4.01, 0, 100), 'load gate')
    # Inject deterministic synthetic callbacks; never call operational adapter.
    entries = [{'workload': n, 'bodyCountPerCall': 32} for n in names]
    def fake(e, arm, count, label):
        return {'calls': count, 'warmupCalls': 1, 'elapsedNanoseconds': 300000000}, False, 'synthetic'
    partial = run_finite_engine(entries, fake, lambda *args: None, lambda: 0, lambda state: None)
    need(partial['runnerCallbacks'] == 95 and not partial['complete'], 'calibration rejects consume fixed5, continue once')
    def fake2(e, arm, count, label):
        return {'calls': count, 'warmupCalls': 1, 'elapsedNanoseconds': 300000000}, '-cal-' in label, 'synthetic'
    cap = run_finite_engine(entries, fake2, lambda *args: None, lambda: 0, lambda state: None)
    need(cap['runnerCallbacks'] == 19*273 and not cap['complete'], 'ninety rejection triples no quiet retry')
    rng = PRNG('LC-current19-PRNG-test/v1'); sequence = [rng.next() for _ in range(8)]
    need(sequence == [1798358773,237354818,2155468580,3913041706,1526714118,3237253033,1899061769,4085119633], 'PRNG version vector')
    varied=[{'baseline':100+i/10,'candidate':90+i/20,'C':95+i/30} for i in range(30)]
    varied_ci=paired_ci(varied,'baseline','synthetic-v1','nondegenerate')
    expected=(1.118186406539862,1.1166914094871203,1.1196916704326092)
    need(all(math.isclose(varied_ci[k],v,rel_tol=1e-14,abs_tol=0) for k,v in zip(
        ('geometricMeanPairedRatio','lower95','upper95'),expected)), 'nondegenerate formula version vector')
    loses=[{'baseline':120.,'candidate':100.,'C':99.} for _ in range(30)]
    need(not summarize(loses,'synthetic-v1','losesC')['COrBetter'], 'each19 cannot hide one losing C workload')
    adapter_controls()
    print(json.dumps({'status': 'PASS_PURE_SYNTHETIC_TIMING_SOURCE_CONTROLS_ONLY', 'tests': 34,
                      'PRNGVector': sequence, 'performanceEvidence': False,
                      'nondegenerateFormulaVector':varied_ci,
                      'nativeCompilerSSHGuestCalls': 0}, indent=2))

def adapter_controls():
    import copy
    from pathlib import Path
    import timing,ledger
    from unittest.mock import patch
    from types import SimpleNamespace
    D=Path(__file__).resolve().parent
    expected=json.loads((D/'expected-semantics.json').read_bytes())
    for arm in ARMS:
        sem=expected['depthconv'][arm]
        q=dict(sem,calls=7,warmupCalls=1,elapsedNanoseconds=300000000,maxRssBytes=1)
        raw=(json.dumps(q)+'\n').encode()
        kind='dylib'if arm=='C'else'raw'
        timing.sample(raw,b'',7,kind,sem)
        for mutation in ['boolean','wrongresult','unknown','doubleline','stderr']:
            z=copy.deepcopy(q);err=b''
            if mutation=='boolean':z['calls']=True
            if mutation=='wrongresult':z['result']=0
            if mutation=='unknown':z['unknown']=0
            b=(json.dumps(z)+'\n').encode()
            if mutation=='doubleline':b+=b'{}\n'
            if mutation=='stderr':err=b'x'
            try:timing.sample(b,err,7,kind,sem)
            except (AssertionError,ValueError):pass
            else:raise AssertionError('parser mutation '+mutation)
    p=SimpleNamespace(pid=123,returncode=None,kill=lambda:None)
    usage=SimpleNamespace(ru_utime=.1,ru_stime=.2)
    with patch.object(ledger.os,'killpg',side_effect=ProcessLookupError),patch.object(ledger.os,'wait4',return_value=(123,0,usage))as wait:
        cpu=ledger.kill_and_reap(p)
    need(p.returncode==0 and wait.call_count==1 and cpu['childCpuNs']==300000000,'exit-before-kill always wait4 reaped')

if __name__ == '__main__': main()
