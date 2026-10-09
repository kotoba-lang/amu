"""Copied SOURCE registration authoring only; no operational driver invocation."""
from pathlib import Path
import json,hashlib,shutil
D=Path(__file__).parent;W=D.parent;T=W/'native-ctx-query-observer4-source-v2-20261009-independent';C=W/'native-ctx-positive-memo-source-v1-20261009-independent'
def load(p):return json.loads(Path(p).read_bytes())
def rec(p):b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
for n in ['capture.py','integration.py','controller.py','typed-adapter.py','runtime.py','artifact_admission.py','native-call.py']:
 shutil.copyfile(T/n,D/n)
for n in ['helpers.kotoba','41-memo.kotoba','unity-memo.kotoba','memo.patch','controls.json','writer-inventory.json','CONTRACT.md']:
 shutil.copyfile(C/n,D/n)
for n in ['statemate.kotoba','nsichneu.kotoba']:shutil.copyfile(T/n,D/n)
pr=load(T/'preregistration.json');oldRoot=pr['freshOutputRoot'];newRoot=str(D/'run-outputs')
# Concrete canonical prospective paths only; no rewriting external lineage receipts.
pr['format']='amu.current-g4-positive-memo4/source-v1';pr['freshOutputRoot']=newRoot
pr['environment']['TMPDIR']=newRoot;pr['environment']['KEXE_CAP_RESOURCES_35']=newRoot
pr['rootGOStatus']='GO_CURRENT_G4_POSITIVE_CTX_MEMO4_V1';pr['sourceReviewStatus']='PASS_SOURCE_ONLY_CURRENT_G4_POSITIVE_CTX_MEMO4_V1';pr['invocationSealVersion']='ctx-memo4-fixed-invocation/v1'
for c in pr['cases']:
 c['label']=c['label'].replace('observer','memo');c['outputPath']=c['outputPath'].replace(oldRoot,newRoot).replace('observer','memo');c['nativeArgv']=[v.replace(oldRoot,newRoot).replace('/unity-observer.kotoba','/unity-memo.kotoba').replace('/observer.','/memo.')for v in c['nativeArgv']];c['observer']=False
pr['sourceSHA256']=rec(D/'unity-memo.kotoba')['sha256'];pr['sourceAssembly']=str(D/'source-assembly.json');pr.pop('scratch');pr['memoSource']={'path':str(C/'source-pins.json'),**rec(C/'source-pins.json')};pr['memoCapacityContract']={'MM_WORDS':8388608,'MM_HEAP_BASE':6623488,'MM_HEAP_END':8388608,'generatorBlockWords':147680,'additionalWords':128,'oldTailWords':80,'newTailWords':208,'maximumFN':8192,'maximumSIR':196608,'actualTopKnownBeforeLaunch':False,'actualRemainingCapacityCheckedByNativeMemFits':True,'genericHeapBoundaryEquivalence':False};pr['nativeAnswerReuse']=True;pr['sharedCIDCacheImplemented']=False;pr.pop('observerActualParsingPending');pr['memoActualValidationPending']=True
for k in ['maximumProtocolRecords','maximumProtocolLineBytes','maximumTopSummaries','maximumFullyTracedTopQueries']:pr.pop(k)
pr['operationalHOLD']=['two exact SOURCE reviews and root GO absent','no native memo/capacity/artifact identity qualification','compiler fueloff only; general trap/fuelon/heap boundary unqualified','full19 guest correctness and performance separate future gates']
a=load(C/'source-assembly.json')
for r in a['modulePins']:
 if r['module']=='seed/41-a64gen.kotoba':r['path']=str(D/'41-memo.kotoba')
a['unity']={'path':str(D/'unity-memo.kotoba'),**rec(D/'unity-memo.kotoba')};save('source-assembly.json',a);save('preregistration.json',pr)
for n in ['launch-wrapper.py','producer_guard.py','run.py']:
 s=(T/n).read_text().replace('observer','memo').replace('OBSERVER','MEMO').replace('ctx-memo-generated-producer/v2','ctx-memo-generated-producer/v1')
 if n=='run.py':
  s=s.replace("     need('memoSummary'in r['report'],'strict parsed memo trace')\n",'')
  s=s.replace("'COMPLETE_CURRENT_G4_CTX_QUERY_MEMO4_ARTIFACT_AND_BOUNDED_TRACE_ONLY'","'COMPLETE_CURRENT_G4_POSITIVE_CTX_MEMO4_WHOLE_ARTIFACT_IDENTITY_ONLY'")
  s=s.replace("'nativeAnswerReuse':False","'nativeAnswerReuse':True").replace("'scratchAdditionalWords':8","'scratchAdditionalWords':128").replace("'equalKeysActualObservationRequired':True","'cachePerformanceQualified':False")
  s=s.replace("guard();need(not O.exists()", "guard();need(pr['compileFuel']=='off'and pr['environment']['KEXE_FUEL']=='off','compiler fueloff only');need(not O.exists()")
  s=s.replace("  b,e=container(Path(pr['candidateContainer']).read_bytes());", "  from source_capacity import source_capacity_contract\n  source_capacity_contract(D,pr)\n  b,e=container(Path(pr['candidateContainer']).read_bytes());")
 (D/n).write_text(s)
# Ordinary strict compile/extract only; no trace parser needed or unexpected stdout accepted.
shutil.copyfile(W/'tc-homogeneous-tail-frame-native4-source-v2-20261009/compiler_output.py',D/'compiler_output.py')
