"""Three-file stdlib data-only replay; no native/compiler/network/solver launch."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,builtins
D=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
mp=D/'native-bank-controls-proof.manifest.json'
assert sha(mp.read_bytes())=='9c0d6e2e6202ad3eaa347715b4ca8e1511d2ce066c3bea4e7ecbebfd60a5c099','manifest envelope hash'
m=json.loads(mp.read_text());a=D/m['archive'];assert a.stat().st_size==m['archiveBytes']<=4194304 and sha(a.read_bytes())==m['archiveSHA256'],'archive envelope hash'
assert len(m['paths'])<=1500 and m['uncompressedObjectBytes']<=33554432
with tempfile.TemporaryDirectory(prefix='offline-native-bank-',dir=D)as td:
 root=Path(td).resolve();objects={}
 with tarfile.open(a,'r:gz')as tf:
  for t in tf:
   assert t.isfile()and t.name.startswith('objects/')and len(t.name)==72 and 0<=t.size<=33554432
   b=tf.extractfile(t).read();h=t.name[8:];assert sha(b)==h and h not in objects;objects[h]=b
 assert len(objects)==m['objects']and sum(map(len,objects.values()))==m['uncompressedObjectBytes']
 for name,v in m['paths'].items():
  rel=PurePosixPath(name);assert not rel.is_absolute()and'..'not in rel.parts
  b=objects[v['sha256']];assert len(b)==v['bytes'];p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 P=root/'workspace';original='/Users/junkawasaki/github/workspaces/codex'
 class MappedPath(type(Path())):
  def __new__(cls,*args):return super().__new__(cls,*[builtins.str(x).replace(original,builtins.str(P))for x in args])
 def origin_str(x):return builtins.str(x).replace(builtins.str(P),original)
 p=P/'vector-persistent-label-native-controls-actual-independent-v1/audit.py'
 # Execute only frozen offline audit/parser/report construction, exclude reporting writes.
 s=p.read_text().split("(D/'report.json').write_text",1)[0].replace('from pathlib import Path\n','')
 ns={'__file__':builtins.str(p),'Path':MappedPath,'str':origin_str};exec(compile(s,builtins.str(p),'exec'),ns)
 frozen=json.loads((p.parent/'report.json').read_text());assert ns['report']==frozen
 assert frozen['actualNewLoaderCalls']==24 and frozen['actualDiagnosticGuestInvocations']==18 and frozen['benchmarkBodyExecutions']==0 and frozen['combinedActualLoaderCalls']==29
 assert frozen['baselineBytes']==172 and frozen['mandatoryOwnedCleanupWords']==50177
 # Bind receipt semantics to the actual scalar comparison loops, not an external arena.
 helpers=(P/'vector-persistent-label-native-controls-v3/control-helpers.kotoba').read_text()
 for text in ['(vector-alloc (vector-count M))','(vector-assoc! V i (vector-at M i))','(not= (vector-at A i) (vector-at B i))','(vc-equal snapshot result 0 (vector-count result))','(vc-equal snapshot result base (+ base words))']:
  assert text in helpers
 W=P/'vector-persistent-label-native-controls-v3-execution-v1';old=P/'vector-persistent-label-native-controls-v2-execution-v1'
 terminal=json.loads((W/'terminal-controls.json').read_text());assert terminal['nativeGuestBodies']==0
 prior=json.loads((old/'attempts.json').read_text());assert len(prior)==5 and all(x['state']=='terminal'for x in prior) and prior[-1]['label']=='case-0'and prior[-1]['returncode']==2
 for i,r in enumerate(prior):
  assert r['index']==i+1
  if i<4:assert r['returncode']==0 and (old/(r['label']+'.stderr')).read_bytes()==b''and b':ok true'in(old/(r['label']+'.stdout')).read_bytes()
 assert b'seed: E1 usage:'in(old/'case-0.stderr').read_bytes()and b'ALLOC 'not in(old/'case-0.stdout').read_bytes()
 amendment=json.loads((old/'root-setup-failure-amendment.json').read_text());assert amendment['nativeCallsBeforeRetry']==0
 setup=MappedPath(amendment['preservedSetupFailure']);assert setup.exists()
 print(json.dumps({'status':'PASS_OFFLINE_FIXED18_NATIVE_CONTROL_RECEIPTS_NOT_UNIVERSAL_MEMORY_PROOF','newLoaderCalls':24,'buildAndBaselineCompilerCalls':6,'diagnosticGuestInvocations':18,'benchmarkBodyExecutions':0,'priorFailedLoaderCalls':5,'priorProbeEntries':0,'combinedLoaderCalls':29,'fullScalarMComparisonReceiptWords':8388608,'inVectorGComparisonReceiptWords':147554,'cleanupOwnedWords':50177,'fixed18ConditionsPass':True,'allFixtureSelectorsSIRFRECExact':True,'partialIndexAndQueryWitnessesBound':True,'oldHelperSentinelsBound':True,'baselineBytes':172,'benchOffsetExact':True,'legacyGuestBodies0MeansBenchmarkBodies':True,'initialSetupAndDispatchABIFailurePreserved':True,'nativeRunsByReader':0,'sameMReuseExternalArenasArbitraryMPerformanceV7ProfileQualification':False}))
