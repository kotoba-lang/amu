from pathlib import Path
import hashlib,json,sys,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'current17-consumer-qualify342-source-v1-20261009-dense';A=W/'current17-consumer-qualify342-source-review-independent-20261009';P=W/'tc-hft-current19-packet-install-source-v3-20261009-crc';B=W/'tc-hft-g4-held-v6-original19-runtime190-source-v1-20261009-dense'
def rec(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p):return json.loads(p.read_bytes())
def check(p,r):assert p.is_file() and not p.is_symlink() and {k:rec(p)[k] for k in ('bytes','sha256')}=={k:r[k] for k in ('bytes','sha256')}
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');f=load(D/'freeze.json');assert len(sp)==25 and len(ip)==108 and sum(x['bytes']for x in ip.values())==2931240
for n,r in sp.items():check(D/n,r)
for n,k in [('source-pins.json','sourcePins'),('input-pins.json','inputPins'),('run.py','driver'),('preregistration.json','preregistration')]:check(D/n,f[k])
m={r['relativePath']:r for r in load(P/'manifest.json')['files']}
for n,r in ip.items():assert {k:m[n][k]for k in ('bytes','sha256')}==r;check(Path(m[n]['source']),r)
held=load(D/'held-component-identity.json')['components'];assert len(held)==7
for n,r in held.items():check(D/n,r);assert (D/n).read_bytes()==(B/n).read_bytes()
# Native call delta limited to ordered bound, case-aware decoder/C observability and root cwd.
old=(B/'native-call.py').read_text().replace("len(rows)<190","len(rows)<342").replace('fixed ordered190 no retry','fixed ordered342 no retry').replace("qualify(out,err,case['expectedResult'])","qualify(out,err,case)").replace("{'status':'valid','values':report['arena17']}","{'status':'unavailable-C'if case['arm']=='C'else'valid','values':report['arena17']}").replace('cwd=O,','cwd=Path(pr[\'taskRoot\']),');assert old==(D/'native-call.py').read_text()
sys.dont_write_bytecode=True;sys.path.insert(0,str(D));import run,prepare,qualification
pr=load(D/'preregistration.json');assert run.validate_scope(pr,ip)
sourceProof=W/'tc-hft-g4-held-v6-original19-runtime190-actual-review-independent-20261009-dense/report.json';actual=load(sourceProof);expect=load(D/'expected-observables.json');assert rec(sourceProof)['sha256']==expect['actualProofSHA256']==pr['current190ActualProofSHA256'];assert len(expect['cases'])==len(actual['calls'])==190
for e,a in zip(expect['cases'],actual['calls']):
 assert (e['workload'],e['n'],e['arm'])==(a['workload'],a['profile'],a['arm'])
 for key in ('stdout','stderr'):check(Path(a['raw'][key]['path']),a['raw'][key])
 decoded=qualification.native_raw(Path(a['raw']['stdout']['path']).read_bytes(),Path(a['raw']['stderr']['path']).read_bytes());assert decoded==e['observables']
rows=load(D/'packet.json')['entries'];root=Path('/modeled');arts={r['workload']:dict(path=str(root/'consumer-build-outputs'/r['workload']/'consumer'),bytes=32,sha256='0'*64)for r in rows};cases=prepare.qualification_cases(root,rows,arts);assert len(cases)==342 and len({tuple(c['nativeArgv'])for c in cases})==342 and sum(c['calls']+c['warmup']for c in cases)==741
assert sum(c['phase']=='fresh' for c in cases)==285 and sum(c['phase']=='repeat-reset'for c in cases)==57
for r in rows:
 w=r['workload'];assert r['profiles']==([0,1,2,17,2000]if w=='depthconv'else[0,1,2,17,32])
 for arm in ('OFF','ON'):
  for key in ('native','container'):check(Path(r[arm][key]['path']),r[arm][key])
  raw=Path(r[arm]['container']['path']).read_bytes();payload,exports=run.container(raw);assert payload==Path(r[arm]['native']['path']).read_bytes() and (r['symbol'],r[arm]['offset'],1)in exports
schema=load(D/'go-schema.json');assert set(schema['exactKeys'])==run.GO_KEYS
for n in sp:
 if n.endswith('.py'):ast.parse((D/n).read_text(),feature_version=(3,9))
s=(D/'run.py').read_text();assert s.index("finally:save(O/'terminal.json'")<s.index("save(O/'report.json'");assert "guard();t=load(O/'terminal.json')" in s
(A/'checks.json').write_text(json.dumps(dict(sourceFiles=25,inputFiles=108,inputBytes=2931240,heldExactComponents=7,originalExpectedRawDecoded=190,originalNativeContainerPairs=38,qualifierCases=342,fresh=285,repeatReset=57,warmupAndBodyCalls=741,pureControls=load(D/'pure-controls.json'),nativeCallDeltaClosed=True,operationalCalls=0),indent=2)+'\n')
print('PASS frozen registry/held delta/current190 expectations/342 source only')
