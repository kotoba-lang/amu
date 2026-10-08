"""SOURCE-only continuation preparation; no native execution."""
from pathlib import Path
import json,hashlib,ast
D=Path(__file__).resolve().parent;W=D.parent;P=W/'vector-compute-result-output-role-source-v1-census-review';B=W/'vector-compute-current19-query-census40-plan-v2-controls';A=W/'vector-compute-result-output-role-actual-review-v1-width';C=W/'vector-compute-result-output-role-actual-review-v1-census-review'
def load(p):return json.loads(p.read_text())
def pin(p):
 h=hashlib.sha256();n=0
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
 return {'bytes':n,'sha256':h.hexdigest()}
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
assert pin(A/'report.json')['sha256'].startswith('e8a21c06')and load(A/'report.json')['status']=='PASS_INDEPENDENT_ACTUAL_DECLARED_OUTPUT_ROLE_PILOT6_BYTE_IDENTITY_ONLY'
closure=load(A/'input-pins.json')
for n in ('source-pins.json','source-report.json','pilot-preregistration.json','run6.py'):closure[str(P/n)]=pin(P/n)
for n in ('report.json','input-pins.json'):closure[str(A/n)]=pin(A/n);closure[str(C/n)]=pin(C/n)
pr=load(P/'pilot-preregistration.json');pr['schema']='DECLARED_OUTPUT_ROLE_RETAINED6_PLUS_REMAINING34/v1';pr['entries']=[e for e in load(B/'preregistration.json')['entries']if e['workload']not in ('crc32','slre')]
assert len(pr['entries'])==17 and len({e['workload']for e in pr['entries']})==17
observer=P/'run-outputs/observer.bin';pr['producer']={'path':str(observer),**pin(observer)};pr['retainedObserverContainer']={'path':str(P/'run-outputs/observer.kseed'),**pin(P/'run-outputs/observer.kseed')}
pr['proofs'].extend([{'path':str(A/'report.json'),**pin(A/'report.json'),'status':load(A/'report.json')['status']},{'path':str(C/'report.json'),**pin(C/'report.json'),'status':load(C/'report.json')['status']}])
for p,v in closure.items():assert pin(Path(p))==v,p
save(D/'origin-pins.json',closure)
pr.update(maximumChildCalls=34,compilerBuildCalls=0,workloadCompileExtractCalls=34,rootGOStatus='AUTHORIZE_DECLARED_OUTPUT_ROLE_REMAINING17_CONTINUATION34_ONLY',sourceReviewStatus='PASS_SOURCE_ONLY_DECLARED_OUTPUT_ROLE_CONTINUATION34',freshOutputDirectory=str(D/'run-outputs'),inputClosureFiles=len(closure),inputClosureBytes=sum(v['bytes']for v in closure.values()),inputClosureSHA256=pin(D/'origin-pins.json')['sha256'],retainedChildCalls=6,retainedWorkloadCompileExtractCalls=4,joinedMaximumCalls=40,joinedOriginalWorkloads=19,existingCasesMustNotRepeat=['crc32','slre'],observerBuildMustNotRepeat=True,original19Qualified=False,decodedFrequencyBytes=67108864)
save(D/'preregistration.json',pr)
for n in ('decode.py','census.py','artifact.py','capture-schema.json','request-key-contract.json','write-role-inventory.json'):(D/n).write_bytes((P/n).read_bytes())
base=(P/'run6.py').read_text();lines=base.splitlines(keepends=True);starts=[];n=0
for line in lines:starts.append(n);n+=len(line)
edits=[]
for node in ast.walk(ast.parse(base)):
 if isinstance(node,ast.Constant)and type(node.value)is int and node.value==6:edits.append((starts[node.lineno-1]+node.col_offset,starts[node.end_lineno-1]+node.end_col_offset,'34'))
driver=base
for a,b,t in sorted(edits,reverse=True):driver=driver[:a]+t+driver[b:]
driver=driver.replace('pilot-preregistration.json','preregistration.json').replace('6hardcap','34hardcap').replace('exact6/2','exact34/17').replace('len(images)==2','len(images)==17').replace("'images':2","'images':17").replace('PASS_ACTUAL_DECLARED_OUTPUT_ROLE_CRC32_SLRE_PILOT6_BYTE_IDENTITY_ONLY','PASS_ACTUAL_DECLARED_OUTPUT_ROLE_REMAINING17_CONTINUATION34_BYTE_IDENTITY_ONLY')
line=[s for s in driver.splitlines()if "guard();(root/'sources/unity-result.kotoba')"in s];assert len(line)==1
driver=driver.replace(line[0],"  guard();nb=Path(pr['producer']['path']);ex,payload=container(Path(pr['retainedObserverContainer']['path']).read_bytes());need(ex==[{'name':'main','offset':0,'arity':0}] and payload==nb.read_bytes(),'retained exact observer main0/payload')")
# Final metadata explicitly joins retained pilot identity without re-running any child.
needle="'calls':34,'images':17,'queryCalls':"
assert driver.count(needle)==1
driver=driver.replace(needle,"'calls':34,'images':17,'retainedCalls':6,'joinedCalls':40,'retainedWorkloads':['crc32','slre'],'joinedWorkloads':19,'queryCalls':")
driver=driver.replace('def capture(p):','def capture(p,limit=None):').replace("p.stat().st_size<=pr['nativeArtifactBytes']","p.stat().st_size<=(pr['nativeArtifactBytes'] if limit is None else limit)").replace("capture(p/'frequency.json');","capture(p/'frequency.json',pr['decodedFrequencyBytes']);")
assert "call('observer-build'"not in driver and "extract('observer-extract'"not in driver
ast.parse(driver);(D/'run34.py').write_text(driver)
save(D/'authoring-controls.json',{'status':'PASS_PURE_CONTINUATION_SEQUENCE_SOURCE_CONTROLS_ONLY','nativeCalls':0,'SSHCalls':0,'retainedExactObserver':pr['producer'],'retainedCompilerBuildExtract':2,'retainedWorkloadCompileExtract':4,'newCompilerBuildExtract':0,'remainingWorkloads':[e['workload']for e in pr['entries']],'newMaximumCalls':34,'joinedCalls':40,'ASTConstantCountChanges':len(edits),'decoderByteExactPilot':True,'sourceDriverExecuted':False,'typedDecodedFrequencyLimit':67108864,'nativeArtifactLimitUnchanged':4194560,'limitReason':'Decoded CR metadata can exceed the native image limit; separate bounded metadata cap, no raw/native cap change'})
save(D/'input-pins.json',{str(P/'source-pins.json'):pin(P/'source-pins.json'),str(P/'run6.py'):pin(P/'run6.py'),str(A/'report.json'):pin(A/'report.json'),str(A/'input-pins.json'):pin(A/'input-pins.json'),str(C/'report.json'):pin(C/'report.json')})
print(json.dumps({'closureFiles':len(closure),'closureBytes':pr['inputClosureBytes'],'remaining':[e['workload']for e in pr['entries']]}))
