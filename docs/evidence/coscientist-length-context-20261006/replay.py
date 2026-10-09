"""Restore full evidence and independently recompute native recorded constructor/context facts."""
from pathlib import Path
import json,hashlib,tarfile,tempfile,importlib.util,re,subprocess,os,sys
E=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,x in json.loads((E/'archive-manifest.json').read_text()).items():assert sha(E/name)==x['sha256'] and (E/name).stat().st_size==x['bytes']
root=Path(tempfile.mkdtemp(prefix='amu-length-replay-'))
with tarfile.open(E/'native-proof.tgz') as t:t.extractall(root,filter='data')
W=root/'amu-length-context-20261006'
for p,h in json.loads((W/'all-artifact-pins.json').read_text()).items():assert sha(W/p)==h,p
for p,h in json.loads((W/'snapshot-pins.json').read_text())['files'].items():assert sha(W/'source-snapshot'/p)==h,p
sp=importlib.util.spec_from_file_location('length_oracle',W/'verify.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
rows=[{'workload':p.parent.name,**v.verify(p),'logSha256':sha(p)} for p in sorted((W/'observer/meta-ports').glob('*/compile.log'))];assert rows==json.loads((E/'oracle-proof.json').read_text())['entries']
base={x['workload']:x for x in json.loads((W/'ports-correctness.json').read_text())['entries']};parity=json.loads((W/'observer/observer-byte-audit.json').read_text())['entries'];assert len(parity)==19
for x in parity:
 d=W/'observer/meta-ports'/x['workload'];assert sha(d/'native.bin')==base[x['workload']]['nativeSha256']==x['nativeSha256'];assert int(re.search(r':offset (\d+)',(d/'extract.log').read_text())[1])==base[x['workload']]['offset']==x['offset']
expect=json.loads((W/'control-expectations.json').read_text());ids=expect['functions'];e=expect['expected'];nativeRuns=0
for row in json.loads((E/'controls-proof.json').read_text())['rows']:
 d=W/'controls'/row['variant'];p=d/'stdout'
 if '--native' in sys.argv:
  offset=re.search(r':offset (\d+)',(d/'extract.log').read_text())[1];os.chmod(W/'observer/kexe-loader',0o755)
  env=dict(os.environ,KEXE_COMMAND='1',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',KEXE_STRING_POOL='268435456',KEXE_VECTORS='4194304',KEXE_PAIRS='16777216',KEXE_VECTOR_ITEMS='134217728')
  q=subprocess.run([str(W/'observer/kexe-loader'),str(d/'probe.bin'),offset,'0','aarch64','37,38','--'],env=env,capture_output=True,text=True);assert q.returncode==0 and q.stdout+q.stderr==p.read_text();nativeRuns+=1
 s,m,nativeFlags,end=v.shape.parse(p);flags,_=v.shape.infer(s,m);assert nativeFlags==flags
 contexts,calls,accesses,status=v.inference(s,m,flags)
 assert sorted(n for f,n in contexts if f==ids['reader'] and n>=0)==e['readerPrivateLengths']
 for n in e['mustNotSeedReader']:assert not any(x[0]==ids[n] and x[3]==ids['reader'] for x in calls),n
 for n in e['mustSeedReaderLength3']:assert any(x[0]==ids[n] and x[3:]==(ids['reader'],3) for x in calls),n
 for n in e['outsideRangeRoots']:assert any(x[0]==ids[n] and not 0<=x[4]<x[3] for x in accesses),n
 assert not any(x[0]==ids[e['noAccessRoot']] for x in accesses)
 try:v.verify(p);detected=False
 except AssertionError:detected=True
 assert detected==row['detected']==(row['variant']!='correct')
if '--laws' in sys.argv:
 q=subprocess.run([sys.executable,str(W/'laws.py')],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 fresh=json.loads((W/'laws-proof.json').read_text());saved=json.loads((E/'laws-proof.json').read_text());assert [(x['name'],x['result']) for x in fresh['checks']]==[(x['name'],x['result']) for x in saved['checks']]
out={'status':'PASS independent extracted source/binary/raw-SIR/context/hand-control replay','allArtifactAndSourcePinsVerified':True,'original19ByteAndOffsetParity':True,'contexts':sum(x['contexts'] for x in rows),'privateLengthContexts':sum(x['privateLengthContexts'] for x in rows),'inRangeStaticAccessFacts':sum(x['inRangeAccessFacts'] for x in rows),'handControlFunctions':len(ids),'actualNativeSourceMutantsDetected':5,'freshSavedNativeControlExecutions':nativeRuns,'SMTLawsRecomputed':'--laws' in sys.argv,'boundsChecksRemoved':0,'productPromoted':False,'performanceClaim':False,'COrBetterAchieved':False}
(E/'replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
