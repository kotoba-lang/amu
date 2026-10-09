from pathlib import Path
import json,hashlib,ast,copy,io,tarfile
D=Path(__file__).resolve().parent
ns={};exec(compile((D/'result-contract.py').read_bytes(),'result-contract.py','exec'),ns)
def fixture(n,failure):
 c={};rows=[]
 for i,label in enumerate(ns['LABELS'][:n]):
  r={'index':i+1,'label':label,'state':'terminal','returncode':0,'timeout':False,'stdoutSHA256':hashlib.sha256(b'').hexdigest(),'stderrSHA256':hashlib.sha256(b'').hexdigest()};rows.append(r)
  for ext in ['.stdout','.stderr']:c['functional171/'+label+ext]=b''
 if n:c['functional171/attempts.json']=json.dumps(rows).encode()
 c['functional171/terminal.json']=json.dumps({'allCallsClosed':True,'calls':n,'failure':failure}).encode()
 if failure:c['functional171/failure.json']=json.dumps({'calls':n,'completedTriples':n//3,'policy':'STOP_FIRST_FAILURE_NO_RETRY'}).encode()
 else:
  c['functional171/report.json']=json.dumps({'status':'PASS_FINITE_FULL_ORIGINAL19_171_FUNCTIONAL_ONLY','calls':171,'workloads':19}).encode();c['functional171/comparisons.json']=b'[]'
 return c
v=fixture(171,False);ns['validate_result'](v)
for n in [0,1,2,3,170,171]:ns['validate_result'](fixture(n,True))
reject=0
def bad(c):
 global reject
 try:ns['validate_result'](c)
 except (AssertionError,KeyError):reject+=1
 else:raise AssertionError('adverse accepted')
for k,z in [('calls',True),('calls',172),('allCallsClosed',False)]:
 c=copy.deepcopy(v);t=json.loads(c['functional171/terminal.json']);t[k]=z;c['functional171/terminal.json']=json.dumps(t).encode();bad(c)
c=copy.deepcopy(v);c['functional171/secret.txt']=b'X';bad(c)
c=copy.deepcopy(v);r=json.loads(c['functional171/attempts.json']);r[-1]['state']='started';c['functional171/attempts.json']=json.dumps(r).encode();bad(c)
c=copy.deepcopy(v);c['functional171/'+ns['LABELS'][0]+'.stdout']=b'altered';bad(c)
for p in D.glob('*.py'):ast.parse(p.read_text())
assert len(ns['LABELS'])==171 and len(set(ns['LABELS']))==171
(D/'offline-checks.json').write_text(json.dumps({'status':'PASS_PURE_LABEL_TERMINAL_CLOSURE_ONLY','labels171':True,'successfulTerminal':1,'partialTerminals':6,'rejectControls':reject,'nativeCompilerSSHCalls':0},indent=2)+'\n')
print('PURE_CHECKS_PASS')
