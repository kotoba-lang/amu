"""Injected model SOURCE only; modeled receipt paths grant no runtime/build credit."""
from pathlib import Path
import json,copy,ast
import run,prepare
from qualification import parse,REPORT,COUNTERS
D=Path(__file__).resolve().parent
pr=run.load(D/'preregistration.json');ip=run.load(D/'input-pins.json');assert run.validate_scope(pr,ip)
rows=run.load(D/'packet.json')['entries'];root=Path('/modeled-root')
artifacts={r['workload']:{'path':str(root/'consumer-build-outputs'/r['workload']/'consumer'),'bytes':32,'sha256':'0'*64}for r in rows}
cs=prepare.qualification_cases(root,rows,artifacts)
assert len(cs)==342 and len({tuple(c['nativeArgv'])for c in cs})==342 and sum(c['calls']+c['warmup']for c in cs)==741
import importlib.util
spec=importlib.util.spec_from_file_location('wrapper',D/'launch-wrapper.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
runtime=dict(pr,environment=pr['environmentBase']|{'TMPDIR':'/modeled-root/output'})
for c in cs:assert w.runtime_case(c['nativeArgv'],runtime,c)
n=0
def refuses(f):
 global n
 try:f()
 except (AssertionError,ValueError,KeyError,TypeError):n+=1;return
 raise AssertionError('mutant accepted')
for k in ['qualificationChildCalls','freshQualificationCalls','repeatQualificationCalls','bodyInvocationsIncludingWarmup','qualificationCampaignSeconds','qualificationOutputReservationBytes','controlledFDLedgerMaximum','auxiliaryThreadsPerCall','maximumAuxiliaryThreadStarts','guestFuelPerCall']:
 q=copy.deepcopy(pr);q[k]+=1;refuses(lambda:run.validate_scope(q,ip))
for k in ['C2','noRetry','timingComparisonAuthorized']:
 q=copy.deepcopy(pr);q[k]=not q[k];refuses(lambda:run.validate_scope(q,ip))
q=copy.deepcopy(ip);q.pop(next(iter(q)));refuses(lambda:run.validate_scope(pr,q))
for c in cs:
 a=list(c['nativeArgv']);a.insert(1,'--');refuses(lambda:w.runtime_case(a,runtime,c))
# Pure reconstruct owned native raw, then two-record decoder; C never inherits fuel/arena claims.
for c in cs:
 e=c['expected'];used=e['finalUsed'];fuel=e['fuelRemaining'];arena=e['arena17']
 if c['arm']=='C':used=[0]*4;fuel=16777216;arena=[0]*17
 out=('{:status :ok :result '+str(e['result'])+' :fuel {:initial 16777216 :remaining '+str(fuel)+'} :heap {:capacity 2097152 :used '+str(used[0])+'} :string-pool {:capacity 65536 :used '+str(used[1])+'} :vectors {:capacity 4096 :used '+str(used[2])+'} :vector-items {:capacity 65536 :used '+str(used[3])+'}}\n').encode()
 t={'schema':'CURRENT17_TIMING_V1','arm':('OFF','ON','C').index(c['arm']),'calls':c['calls'],'warmup':1,'elapsedNs':1,'nativeObservablesAvailable':c['arm']!='C','resetIncluded':False}
 err=('KEXE_ARENA_USE {'+' '.join(':'+k+' '+str(v)for k,v in zip(COUNTERS,arena))+'}\n').encode();full=out+(json.dumps(t)+'\n').encode();q=parse(full,err,c,e,0)
 if c['arm']=='C':assert q['observables']['fuel']is None and q['observables']['arena17']is None
 refuses(lambda:parse(full+b'extra\n',err,c,e,0))
 refuses(lambda:parse(full,err,c,e,1))
for p in D.glob('*.py'):ast.parse(p.read_text(),feature_version=(3,9))
print(json.dumps({'modeledCases':342,'modeledInvocationCount':741,'rawDecoderPositives':342,'refusals':n,'actualBuilds':0,'actualGuests':0},sort_keys=True))
