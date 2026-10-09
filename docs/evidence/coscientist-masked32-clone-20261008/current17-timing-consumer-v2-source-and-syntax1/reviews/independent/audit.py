from pathlib import Path
import json,hashlib,sys,runpy,contextlib,io,copy
D=Path('/Users/junkawasaki/github/workspaces/codex/tc-hft-current17-timing-consumer-source-v2-20261009-crc')
A=Path(__file__).resolve().parent
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def verify():
 counts=[]
 for f,relative in [('source-pins.json',True),('input-pins.json',False)]:
  entries=json.loads((D/f).read_text());total=0
  for k,v in entries.items():
   p=D/k if relative else Path(k);assert p.is_file() and not p.is_symlink()
   r=pin(p);assert all(r[x]==v[x] for x in ('bytes','sha256'));total+=r['bytes']
  counts.append({'registry':pin(D/f),'files':len(entries),'bytes':total})
 return counts
before=verify();assert before[0]['files']==13 and before[1]['files']==541 and before[1]['bytes']==5208923
assert before[0]['registry']['sha256']=='a0d2bed0535e7cf2e9fd6d277303ba99ff1664aff83466989a3c124626ff7699'
assert before[1]['registry']['sha256']=='9aac91bac322eee920eeacfb4d0c868ceaba070bf84b6c4faa83499b02cf0715'
sys.path.insert(0,str(D));out=io.StringIO()
with contextlib.redirect_stdout(out):runpy.run_path(str(D/'source-controls.py'),run_name='__main__')
controls=json.loads(out.getvalue());assert controls['nativeRawPositives']==190 and controls['negativeControls']==774
from qualification import cases,native_raw,parse
from registration import registration
rows=json.loads((D/'packet.json').read_text())['entries'];cs=registration(rows)
assert len(cs)==342 and sum(x['calls']+x['warmup'] for x in cs)==741
recipes=json.loads(Path('/Users/junkawasaki/github/workspaces/codex/tc-hft-current19-transfer-packet-manifest-source-v1-20261009-dense/C-recipes.json').read_text())['commands']
by={x['workload']:x for x in recipes}
for r in rows:
 x=by[r['workload']];assert r['symbol']==x['cSymbol'] and r['profiles']==x['matrixIterations']
# Independent complete C-result decoder positive and key/type/counter/line/flag negatives.
q=cs[2];expected=q['expected'];e=expected
stdout=('{:status :ok :result '+str(e['result'])+' :fuel {:initial 16777216 :remaining 16777216} :heap {:capacity 2097152 :used 0} :string-pool {:capacity 65536 :used 0} :vectors {:capacity 4096 :used 0} :vector-items {:capacity 65536 :used 0}}\n').encode()
from qualification import COUNTERS
stderr=('KEXE_ARENA_USE {'+' '.join(':'+k+' 0' for k in COUNTERS)+'}\n').encode()
t={'schema':'CURRENT17_TIMING_V1','arm':2,'calls':1,'warmup':1,'elapsedNs':1,'nativeObservablesAvailable':False,'resetIncluded':False}
raw=stdout+(json.dumps(t)+'\n').encode();z=parse(raw,stderr,q,e,0);assert z['observables']=={'result':e['result'],'fuel':None,'arena17':None}
neg=0
for key,value in [('elapsedNs',0),('elapsedNs',30000000001),('arm',True),('calls',1.0),('resetIncluded',True),('nativeObservablesAvailable',True),('warmup',0),('schema','OLD')]:
 tt=copy.deepcopy(t);tt[key]=value
 try:parse(stdout+(json.dumps(tt)+'\n').encode(),stderr,q,e,0)
 except (AssertionError,ValueError):neg+=1
 else:raise AssertionError(key)
for bad in [raw+b'\n',raw.replace(b'{"schema"',b'{"arm":2,"schema"',1)]:
 try:parse(bad,stderr,q,e,0)
 except (AssertionError,ValueError):neg+=1
 else:raise AssertionError('raw')
assert neg==10 and verify()==before
report={'status':'PASS_SOURCE_ONLY_CURRENT17_TIMING_CONSUMER_AND_342_REGISTRATION_V2','subject':str(D),'sourcePinsSHA256':before[0]['registry']['sha256'],'inputPinsSHA256':before[1]['registry']['sha256'],'preregistrationSHA256':pin(D/'preregistration.json')['sha256'],'checkedPinsBeforeAndAfter':before,'reviewerRole':'Independent of CRC consumer implementation; authored ancestor current190 diagnostic registration and core packet manifest, not this reset/clock/decoder implementation. No compiler, native, process, network, real FD or thread operations.','reproducedPureControls':controls,'additionalControls':{'CResultPositive':1,'CResultRefusals':neg,'all19CRecipeSymbolAndProfileMatches':True},'findings':[], 'checkedSource':['Three inverse substitutions plus appended frontend recover whole exact V6 loader C 04428f47; helper function bank unchanged.','Reset clears all telemetry, cursors, validity/vector-region highwater prefixes, growth/string counts and scope marks, fuel/trap/result; stale region entries inaccessible by reset counts. Optional hashcons/census/effect-buffer states refuse. String cache clear relies on exact creation-counter premise.','CLOCK_MONOTONIC interval wraps only fn8 call; reset, startup/hash/dlopen, warmup, snapshots/parity, ownership/reap excluded. CPU envelope includes excluded work; clock-boundary overhead is not subtracted.','Original 19 workloads/95 profiles/native bench-or-batch symbols and current OFF/ON owners bound; C eight-argument ABI and C-recipe symbols match all19.','342 immutable qualification cases:285 fresh+57 repeat-reset,741 body invocations. Native results/fuel/final-use/all17 require exact saved-current190 parity; C only Boolean result exposed with fuel/counters unavailable. Duplicate and malformed timing JSON refuse.','Fresh C header requires explicit independent artifact/status/workload/symbol/I64_8ARGS identity; synthetic header controls confer zero build credit. Saved verifier still requires a separately reviewed adapter and exact per-child closure proof.'],'remainingOperationalHOLD':['Fresh source-bound C19 builds and independent per-workload audit before header generation.','Fresh 19 consumer builds; raw syntax, ABI and reset behavior must qualify via342 actual cases, not pure controls.','Reviewed immutable consumer-argv held-ownership/resource adapter with new transient FD/map/dlopen accounting; old44FD proof not silently reused.','Balanced quiet-host comparison/parser registration after functional qualification; no timing or official score from this review.'],'scope':{'productAdoption':False,'nativeRuntimeQualified':False,'performanceQualified':False,'officialEmbenchQualified':False,'generalResetCorrectnessProved':False,'C2':'OFF'}}
(A/'report.json').write_text(json.dumps(report,indent=2)+'\n');(A/'freeze.json').write_text(json.dumps({'status':'FROZEN_INDEPENDENT_SOURCE_REVIEW_ONLY','report':pin(A/'report.json'),'audit':pin(A/'audit.py')},indent=2)+'\n');print(json.dumps(pin(A/'report.json')))
