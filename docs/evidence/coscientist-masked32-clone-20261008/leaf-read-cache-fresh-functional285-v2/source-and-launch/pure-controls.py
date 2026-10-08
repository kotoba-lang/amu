"""Static source/actual saved-sample parser controls. Never spawn an OS child."""
from pathlib import Path
import ast,json,hashlib,copy,sys,re
D=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.path.insert(0,str(D))
from functional285 import sample,CAPS
H=lambda b:hashlib.sha256(b).hexdigest()
pr=json.loads((D/'preregistration.json').read_bytes());assert len(pr['cases'])==19 and sum(len(c['profiles']) for c in pr['cases'])==95
for n in ['functional285.py','launch.py','ledger.py','author-v2.py','pure-controls.py']:ast.parse((D/n).read_bytes())
P=Path('/Users/junkawasaki/github/workspaces/codex/vector-param-original19-transfer-v1-root/collected-functional171')
pins={};accepted=mutants=0
for p in sorted(P.glob('*.stdout')):
 m=re.search(r'-n([0-9]+)\.stdout$',p.name)
 if not m:continue
 b=p.read_bytes()
 if not b.startswith(b'{"format":"kotoba.runtime-sample/v1"'):continue
 q=json.loads(b);kind=q['artifactKind'];n=int(m.group(1));sample(b,b'',n,kind);accepted+=1;pins[str(p)]={'bytes':len(b),'sha256':H(b)}
 variants=[b[:-1],b+b'\n',b.replace(b'"calls":1',b'"calls":true'),b.replace(b'"result":',b'"result":false,"result":'),b.replace(b'"contextFuelBefore":16777216',b'"contextFuelBefore":0')]
 if kind=='raw':
  for k in CAPS:
   z=copy.deepcopy(q);z['nativeArenas'][k]['used']=True;variants.append((json.dumps(z)+'\n').encode())
  z=copy.deepcopy(q);z['contextFuelConsumed']+=1;variants.append((json.dumps(z)+'\n').encode())
 else:
  z=copy.deepcopy(q);z['nativeArenas']={};variants.append((json.dumps(z)+'\n').encode())
 for bad in variants:
  try:sample(bad,b'',n,kind)
  except (AssertionError,ValueError,TypeError):mutants+=1
  else:raise AssertionError('invalid terminal telemetry accepted')
assert accepted==171
for c in pr['cases']:
 assert c['profiles']==[0,1,2,17,c['n']] and c['buildAnchors']['C']==c['C'] and c['buildAnchors']['runner']==c['runner']
 for a in ['OFF','LC','OFFContainer','LCContainer']:assert c[a]['path'].startswith(pr['buildRoot']+'/package/evidence/')
# Both closures counted without dropping local originals/installed members.
for filename in ['input-pins.json','remote-input-pins.json']:
 q=json.loads((D/filename).read_bytes());assert len(q)<=4096 and sum(r['bytes'] for r in q.values())<=448*1024**2
(D/'parser-control-input-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
(D/'pure-controls-result.json').write_text(json.dumps(dict(status='PASS_STATIC_SOURCE_AND_SAVED_CB3F_PARSER_CONTROLS_ONLY',acceptedHistoricalSamples=accepted,rejectedMutants=mutants,originalWorkloads=19,profiles=95,futureCalls=285,sourceOperationalExecutions=0,OSChildren=0,SSH=0,compiler=0,native=0,guest=0,timing=0),indent=2)+'\n')
print('PASS source AST/19/95/285 and171 actual saved cb3f samples, '+str(mutants)+' mutants; no children')

assert (D/'collection-receipt.json').read_bytes()==Path(pr['syntheticReceiptBinding']['originalLocal']['path']).read_bytes()
assert pr['syntheticReceiptBinding']['remotePath'] in json.loads((D/'remote-input-pins.json').read_bytes())
assert pr['priorFailedLaunches']==1 and pr['priorNativeChildren']==0 and pr['maximumCumulativeLaunchChildren']==2 and pr['maximumCumulativeNativeChildren']==285
