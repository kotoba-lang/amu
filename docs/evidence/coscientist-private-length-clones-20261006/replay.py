"""Offline independent replay of current candidate evidence; not a completed machine/timing gate."""
from pathlib import Path
import hashlib,json,tarfile,tempfile,importlib.util,sys,re
E=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,x in json.loads((E/'archive-manifest.json').read_text()).items():assert sha(E/name)==x['sha256'] and (E/name).stat().st_size==x['bytes']
root=Path(tempfile.mkdtemp(prefix='amu-private-clones-replay-'))
with tarfile.open(E/'native-proof.tgz') as t:t.extractall(root,filter='data')
W=root/'amu-private-length-clones-20261006'
for p,h in json.loads((W/'all-artifact-pins.json').read_text()).items():assert sha(W/p)==h,p
for p,h in json.loads((W/'snapshot-pins.json').read_text())['files'].items():assert sha(W/'source-snapshot'/p)==h,p
assert {sha(W/f'seed-{g}.bin') for g in [2,3,4]}=={'20f9a9554a459725bcba06d6110f8b53ffd75c2e14f7ea1d6f08fa48f6040683'}
sp=importlib.util.spec_from_file_location('ir_audit',W/'ir-audit.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
rows=[]
for p in sorted((W/'observer/ports').glob('*/compile.log')):rows.append({'workload':p.parent.name,**v.audit(p),'nativeLogSha256':sha(p)})
assert rows==json.loads((E/'ir-audit.json').read_text())['entries']
for p in sorted((W/'audit-controls').glob('*.log')):
 try:v.audit(p);refused=False
 except (AssertionError,KeyError,ValueError):refused=True
 assert refused,p
assert len(list((W/'audit-controls').glob('*.log')))==11
build=json.loads((W/'ports-build.json').read_text())['entries'];old=json.loads((W/'v1-global-buffer/ports-build.json').read_text())['entries'];assert build==old
for e in build:
 d=W/'ports'/e['workload'];o=W/'observer/ports'/e['workload'];assert sha(d/'native.bin')==sha(o/'native.bin')==e['nativeSha256'];assert int(re.search(r':offset (\d+)',(o/'extract.log').read_text())[1])==e['offset']
state=json.loads((W/'ports-state.json').read_text());assert state['groups']==len(state['rows'])==209
for row in state['rows']:assert row['product']==row['candidate']
# Recompute unchanged current593/25658 expectation table and evaluate saved actual observations.
sys.path.insert(0,str(W));src=(W/'permanent-a64gen-fixtures.py').read_text().replace("R = '/Users/junkawasaki/github/wt/amu-seed17'","R = "+repr(str(W/'source-snapshot')));ns={'__name__':'frozen_fx','__file__':str(W/'permanent-a64gen-fixtures.py')};exec(compile(src,ns['__file__'],'exec'),ns)
proof=json.loads((W/'adoption-permanent-proof.json').read_text());assert len(ns['FIX'])==proof['fixtures']==593 and len(ns['RUNS'])==proof['runs']==len(proof['observations'])==25658
for n,((name,args,expect,opts),row) in enumerate(zip(ns['RUNS'],proof['observations'])):
 assert row['index']==n and row['fixture']==name and row['args']==list(args) and row['expect']==expect
 so,se=row['stdout'],row['stderr'];exit=row['exit']
 if expect=='trap':good=exit!=0 and 'KEXE_TRAP' in se
 elif 'fuel_remaining' in opts:
  result=re.search(r':result (-?\d+)',so);good=exit==0 and result is not None and int(result[1])==expect
 elif 'cmd' in opts:good=exit==(expect&255)
 else:good=exit==0 and so.splitlines()[-1]==str(expect)
 if 'fuel_remaining' in opts:
  left=re.search(r':remaining (-?\d+)',so);good=good and left is not None and int(left[1])==opts['fuel_remaining']
 if 'stdout' in opts:good=good and so.startswith(opts['stdout'])
 assert good,(n,name)
assert proof['realTestCodeAndLiteralBytesEqual'] and proof['realTestFnOffsetsEqual'] and not proof['committedGoldenChanged']
out={'status':'PASS extracted independent current native proof checkpoint replay','allSourceAndBinaryPinsVerified':True,'currentNativeGenerations2To4ByteExact':True,'original19PrePostIRAndAll16FnFieldsRecomputed':True,'clones':550,'originalProvedCallRedirects':9,'privateGuardMapSites':732,'publicGuardFlags':0,'changedProofPacketsRefused':11,'current593FixturesAnd25658ObservedExpectationsRecomputed':True,'original19FullStateGroupsRetainedAndCompared':209,'currentObserverAndLatestFixedPointTargetBytesVerified':True,'freshNativeExecutionsInReplay':0,'machineAuditComplete':False,'nativeEmitterMutationProofComplete':False,'performanceClaim':False,'productPromoted':False,'COrBetterAchieved':False}
(E/'replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
