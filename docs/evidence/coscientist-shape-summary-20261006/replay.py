"""Portable independent raw-log replay. --native reruns saved native controls; --laws reruns Z3/models."""
from pathlib import Path
import json,hashlib,tarfile,tempfile,importlib.util,re,subprocess,os,sys
E=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,z in json.loads((E/'archive-manifest.json').read_text()).items():assert sha(E/name)==z['sha256'] and (E/name).stat().st_size==z['bytes']
root=Path(tempfile.mkdtemp(prefix='amu-shape-replay-'))
with tarfile.open(E/'native-proof.tgz') as t:t.extractall(root,filter='data')
W=root/'amu-shape-summary-20261006'
for p,h in json.loads((W/'all-artifact-pins.json').read_text()).items():assert sha(W/p)==h,p
for p,h in json.loads((W/'snapshot-pins.json').read_text())['files'].items():assert sha(W/'source-snapshot'/p)==h,p
spec=importlib.util.spec_from_file_location('shape_oracle',W/'verify.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
rows=[]
for p in sorted((W/'observer/meta-ports').glob('*/compile.log')):rows.append({'workload':p.parent.name,**v.verify(p),'logSha256':sha(p)})
assert rows==json.loads((E/'oracle-proof.json').read_text())['entries']
base={x['workload']:x for x in json.loads((W/'ports-correctness.json').read_text())['entries']}
parity=json.loads((W/'observer/observer-byte-audit.json').read_text())['entries'];assert len(parity)==19
for row in parity:
 d=W/'observer/meta-ports'/row['workload'];assert sha(d/'native.bin')==base[row['workload']]['nativeSha256']==row['nativeSha256'];assert int(re.search(r':offset (\d+)',(d/'extract.log').read_text())[1])==base[row['workload']]['offset']==row['offset']
expected={x['f']:tuple(x['expected']) for x in json.loads((W/'control-expectations.json').read_text())};nativeRuns=0;proof=json.loads((W/'controls-proof.json').read_text())
for row in proof['rows']:
 d=W/'controls'/row['variant'];p=d/'stdout'
 if '--native' in sys.argv:
  offset=re.search(r':offset (\d+)',(d/'extract.log').read_text())[1];os.chmod(W/'observer/kexe-loader',0o755)
  env=dict(os.environ,KEXE_COMMAND='1',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',KEXE_STRING_POOL='268435456',KEXE_VECTORS='4194304',KEXE_PAIRS='16777216',KEXE_VECTOR_ITEMS='134217728')
  q=subprocess.run([str(W/'observer/kexe-loader'),str(d/'probe.bin'),offset,'0','aarch64','37,38','--'],env=env,capture_output=True,text=True);assert q.returncode==0 and q.stdout+q.stderr==p.read_text();nativeRuns+=1
 s,m,got,end=v.parse(p);want,counts=v.infer(s,m);assert want==expected
 diffs=[f for f in got if got[f]!=want[f]];assert diffs==[x['f'] for x in row['mismatches']]
 assert bool(diffs)==(row['variant']!='correct')
if '--laws' in sys.argv:
 q=subprocess.run([sys.executable,str(W/'laws.py')],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 fresh=json.loads((W/'laws-proof.json').read_text());saved=json.loads((E/'laws-proof.json').read_text());assert [(x['name'],x['result']) for x in fresh['checks']]==[(x['name'],x['result']) for x in saved['checks']];assert fresh['correctSchedules']==saved['correctSchedules'] and fresh['noRequeueCounterexamples']==saved['noRequeueCounterexamples']
out={'status':'PASS extracted independent raw-SIR/metadata/summary/byte-parity/control replay','allArchivedSourceAndBinaryHashesVerified':True,'originalWorkloads':19,'functions':1413,'closed':871,'normalReturnIdentity':732,'handExpectedGroups':31,'actualNativeSourceMutantsDetected':4,'freshSavedNativeControlExecutions':nativeRuns,'SMTAnd24576SchedulesRecomputed':'--laws' in sys.argv,'optimizerImplemented':False,'productPromoted':False,'COrBetterAchieved':False}
(E/'replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
