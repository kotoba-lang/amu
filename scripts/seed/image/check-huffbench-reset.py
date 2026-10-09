#!/usr/bin/env python3
# BOOTSTRAP-TOOL: correctness/resource audit only, never a timing comparison.
import argparse, ctypes, hashlib, json, pathlib, re, subprocess

parser = argparse.ArgumentParser()
parser.add_argument('directories', nargs='+', type=pathlib.Path)
parser.add_argument('--compiler', required=True, type=pathlib.Path)
parser.add_argument('--runner', required=True, type=pathlib.Path)
parser.add_argument('--oracle-library', required=True, type=pathlib.Path)
args = parser.parse_args()
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def offset(p):
    return int(re.search(r':offset (\d+)', p.read_text()).group(1))
def native(p, symbol, n, fuel=16777216):
    return subprocess.run([str(args.runner.resolve()), 'raw', str(p / (symbol+'.bin')),
        str(offset(p/(symbol+'-extract.log'))), 'aarch64', str(n), '1', '0', str(fuel)],
        capture_output=True, text=True)
c = ctypes.CDLL(str(args.oracle_library.resolve()))
for name in ('state_cell', 'oracle_selfcheck', 'batch'):
    fn = getattr(c, name); fn.restype = ctypes.c_int64; fn.argtypes = [ctypes.c_int64]*8
assert c.oracle_selfcheck(0,0,0,0,0,0,0,0) == 1
expected = [c.state_cell(i,0,0,0,0,0,0,0) for i in range(3309)]
for directory in args.directories:
    p = directory.resolve(); output = p/'reset-audit.json'
    if output.exists():
        raise SystemExit('refusing to replace audit evidence: '+str(output))
    source = (p/'huffbench.kotoba').read_text()
    old = '(let [done (body (vector-alloc 3309))] (vector-at done i))'
    assert source.count(old) == 1
    # One diagnostic helper added to this newly authored benchmark. Poisoning
    # proves that skipped initialization cannot hide behind fresh zeroed memory.
    poison = '''(defn- poison [s :vector-i64 i :i64] :vector-i64
  (if (= i 3309) s (poison (vector-assoc! s i -17) (+ i 1))))
'''
    assert source.count('(defn batch ') == 1
    audit = source.replace('(defn batch ', poison+'(defn batch ', 1).replace(old,
        '(let [repetitions (quot i 3309) cell (rem i 3309) '
        'done (repeats (poison (vector-alloc 3309) 0) repetitions)] (vector-at done cell))', 1)
    (p/'audit.kotoba').write_text(audit)
    with (p/'audit-check.log').open('w') as f:
        subprocess.run([str(args.compiler.resolve()), 'check', str(p/'audit.kotoba')], stdout=f, check=True)
    with (p/'audit-compile.log').open('w') as f:
        subprocess.run([str(args.compiler.resolve()), 'compile', str(p/'audit.kotoba'),
            '--target', 'aarch64-macos', '--output', str(p/'audit.kexe')], stdout=f, check=True)
    with (p/'audit-extract.log').open('w') as f:
        subprocess.run([str(args.compiler.resolve()), 'extract-native', str(p/'audit.kexe'),
            '--symbol', 'state-cell', '--output', str(p/'audit.bin')], stdout=f, check=True)
    report = {'format':'amu.huffbench-reset-audit/v1', 'scope':'correctness/resources only; no timing claim',
        'status':'running', 'compilerSha256':sha(args.compiler), 'runnerSha256':sha(args.runner),
        'oracleLibrarySha256':sha(args.oracle_library), 'sourceSha256':sha(p/'huffbench.kotoba'),
        'nativeSha256':sha(p/'batch.bin'), 'auditSourceSha256':sha(p/'audit.kotoba'),
        'auditNativeSha256':sha(p/'audit.bin'), 'poisonValue':-17,
        'cells':[], 'batches':[], 'guards':[], 'formalPerfgateQualified':False}
    output.write_text(json.dumps(report,indent=2)+'\n')
    try:
        for n in (1,32):
            for i, value in enumerate(expected):
                result = native(p,'audit',n*3309+i)
                assert result.returncode==0,(n,i,result.returncode)
                answer = json.loads(result.stdout)['result']; assert answer==value,(n,i,answer,value)
                report['cells'].append({'iterations':n,'cell':i,'Kotoba':answer,'C':value})
                if (i+1)%500==0:
                    print(p.name,'iterations',n,'cells matched',i+1,flush=True)
            output.write_text(json.dumps(report,indent=2)+'\n')
        for n in (0,1,2,17,32):
            result=native(p,'batch',n);assert result.returncode==0,result
            answer=json.loads(result.stdout)['result'];value=c.batch(n,0,0,0,0,0,0,0)
            assert answer==value==int(n>0)
            report['batches'].append({'iterations':n,'Kotoba':answer,'C':value})
        for symbol,n,fuel,code in [('state-cell',3309,16777216,-4),('batch',1,1,-5)]:
            result=native(p,symbol,n,fuel);assert result.returncode==code,(symbol,result)
            report['guards'].append({'symbol':symbol,'input':n,'fuel':fuel,'returncode':result.returncode})
        report['status']='complete'
    except (AssertionError,subprocess.CalledProcessError) as error:
        report['status']='failed';report['failure']=str(error);raise
    finally:
        output.write_text(json.dumps(report,indent=2)+'\n')
    print(p.name,'PASS',len(report['cells']),'cells and batch/guard checks',flush=True)
