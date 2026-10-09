"""One-off diagnostic SOURCE authoring adaptation; no product edit or driver execution."""
from pathlib import Path
import json,hashlib,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');R=Path('/Users/junkawasaki/github/wt/amu-seed17');D=Path(__file__).resolve().parent
LC=W/'vector-leaf-straight-read-cache-full19-selfbuild40-plan-v1-native-controls'
S=W/'vector-fuel-scalar-dag-source-v1-width';B=W/'vector-fuel-scalar-dag-compiler-build4-plan-v2-width'
A=W/'vector-fuel-scalar-dag-compiler-build4-actual-review-v2-census-review'
G=W/'vector-fuel-scalar-dag-emitted-guest10-actual-review-v1-receipt-closeout'
def load(p):return json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);assert p.is_file() and not p.is_symlink();b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
# The complete inherited registries are retained; no provenance pruning.
ip={}
for p in [B/'input-pins.json',A/'input-pins.json',W/'vector-fuel-scalar-dag-emitted-guest10-go-v1-root/final-runtime-input-pins.json',LC/'input-pins.json']:
 for name,z in load(p).items():
  z={k:z[k] for k in ['bytes','sha256']};assert name not in ip or ip[name]==z;ip[name]=z
 ip[str(p)]=rec(p)
for folder,names in [(B,['preregistration.json','source-pins.json','run.py','run-outputs/report.json','run-outputs/terminal.json','run-outputs/attempts.json','run-outputs/generated-pins.json']), (A,['report.json']), (G,['receipt.json']), (LC,['run.py','ledger-origin.json']), (W/'vector-leaf-straight-read-cache-full19-selfbuild40-source-review-v1-width',['report.json']), (W/'vector-masked32-source-bound-loader-actual-review-v2-width',['report.json'])]:
 for name in names:
  p=folder/name;ip[str(p)]=rec(p)
for name,z in load(B/'run-outputs/generated-pins.json').items():ip[name]={k:z[k]for k in ['bytes','sha256']}
ip[str(S/'source-pins.json')]=rec(S/'source-pins.json')
for n,z in load(S/'source-pins.json').items():ip[str(S/n)]={k:z[k] for k in ['bytes','sha256']}
matrix=R/'bench/embench/comparison-matrix.json';m=load(matrix);ip[str(matrix)]=rec(matrix)
assert m['format']=='amu.embench-comparison-matrix-spec/v1' and len(m['entries'])==19
entries=[]
for e in m['entries']:
 p=R/e['source'];z=rec(p);assert z['sha256']==e['expectedSourceSha256'] and len(e['iterations'])==5;ip[str(p)]=z
 entries.append(dict(workload=e['workload'],source=dict(path=str(p),**z),symbol=e['symbol'],iterations=e['iterations']))
assert len(ip)<=3072 and sum(z['bytes']for z in ip.values())<=448*1024**2
for p,z in ip.items():assert rec(p)==z,p
save('input-pins.json',dict(sorted(ip.items())))
pr=load(LC/'preregistration.json')
for k in ['actualOwnerProof','actualOwnerProofStatus','actualOwnerInputPins','LCFrameScope']:pr.pop(k,None)
pr.update(status='PROSPECTIVE_SOURCE_ONLY_FUEL_DAG_ORIGINAL19_SELFBUILD44_BEFORE_DRIVER_AUTHORING',schema='FUEL_DAG_ORIGINAL19_SELFBUILD44/v1',producer=str(B/'run-outputs/ON.bin'),producerSHA256='d3a0e2ffe5887a1b77ace0e0a366dd8bda180f3e9ef2f7067a1e3436f9c3d15a',parentSource=str(S/'unity-df-on.kotoba'),parentSourcePinsSHA256='fbdd649d3964b76d3d91b915065c6133f137954557d60b54df4e47b85ce6a7ba',actualProducerProof=str(A/'report.json'),actualProducerProofStatus='PASS_INDEPENDENT_SAVED_RAW_FUEL_DAG_BUILD4_IDENTITY_ONLY',guestReceipt=dict(path=str(G/'receipt.json'),**rec(G/'receipt.json')),guestReceiptScope=load(G/'receipt.json')['scope'],maximumLoaderCalls=44,remainingWorkloadCalls=38,retainedOrdinaryWorkloadCalls=0,joinedOriginal19CompileExtractCalls=38,selfbuildCalls=6,stageOrder=['canonical original19 compile/extract38 under G0','G0-to-G1 compile/extract2','G1-to-G2 compile/extract2','G2-to-G3 compile/extract2'],entries=entries,rootGOStatus='ROOT_AUTHORIZED_FUEL_DAG_ORIGINAL19_SELFBUILD44_COMPILE_ONLY',sourceReviewStatus='PASS_SOURCE_ONLY_FUEL_DAG_ORIGINAL19_SELFBUILD44',freshOutputRoot=str(D/'run-outputs'),inputPinsSHA256=rec(D/'input-pins.json')['sha256'],exactInputFiles=len(ip),exactInputLogicalBytes=sum(z['bytes']for z in ip.values()),maximumInputFiles=3072,maximumInputLogicalBytes=448*1024**2,maximumChildWallAndReapSeconds=80960,callLedgerOrigin=dict(path=str(LC/'run.py'),**rec(LC/'run.py')),qualification='Compile/extract original19 and three selfbuild generations only; no workload runtime, ABI/trap/fuel qualification, C timing, official score or full selfhost claim',newWorkloadArtifactEquality='No SR/LC or OFF/ON byte equality required; parse whole container and require extracted whole payload identity',guestRootAcceptanceSchema=dict(status='ROOT_ACCEPTED_FUEL_DAG_GUEST10_CPU_CLOSED0_ONLY',receiptSHA256=rec(G/'receipt.json')['sha256'],scope=load(G/'receipt.json')['scope'],closedLoaderCalls=10,full19Qualified=False,performanceQualified=False),noRetry=True,firstFailureStop=True)
save('preregistration.json',pr) # Written before assembling run.py.
s=(LC/'run.py').read_text()
s=s.replace('Exactly10 compile/extract children','Exactly44 compile/extract children').replace('384*1024**2','448*1024**2').replace('<=2048','<=3072').replace('<=402653184','<=469762048').replace('==40','==44').replace('<40','<44').replace('finite40','finite44').replace('exact40','exact44')
s=s.replace("'258670d2371f3c03167fb02f574c6597479a1ce3e0af9a42cac8e41499d56931'",repr(pr['producerSHA256']))
s=s.replace("['actualProducerProof','actualLoaderProof','actualOwnerProof']","['actualProducerProof','actualLoaderProof']").replace("ar['counts']['closedLoaderCalls']==4","ar['loaderCalls']==4 and ar['allChildrenClosed'] is True and ar['failure'] is False")
s=s.replace("'producer actual correspondence')", "'producer actual correspondence');need(ar['sourcePinsSHA256']==pr['parentSourcePinsSHA256'] and next(z for z in ar['images']if z['arm']=='ON')['source']['sha256']==ip[pr['parentSource']]['sha256'],'producer exact emitter source lineage')")
a=s.index("  need(receipt(L/'source-pins.json')");b=s.index("  for p,z in extra.items()",a)
s=s[:a]+'''  need(receipt(L/'source-pins.json')['sha256']==pr['parentSourcePinsSHA256'],'exact emitter source pins');em=load(L/'source-pins.json');need(type(em)is dict and 'unity-df-on.kotoba' in em,'flat fuel DAG registry schema')
  for n,z in em.items():need(set(z)=={'bytes','sha256'} and Path(n).name==n and str(L/n) in ip,'owned emitter source receipt');pin(L/n,z)
'''+s[b:]
a=s.index("  owner=load(pr['actualOwnerProof']);");b=s.index("  mat=load",a)
s=s[:a]+'''  guest=load(pin(pr['guestReceipt']['path'],pr['guestReceipt']));need(guest['status']=='PASS' and guest['scope']==pr['guestReceiptScope'] and guest['counts']['guestCalls']==10 and guest['counts']['pairs']==5 and guest['counts']['trapCalls']==2 and guest['pinMismatches']==[] and guest['failures']==[] and all(v is True for v in guest['checks'].values()) and guest['full19Qualified'] is False and guest['performanceQualified'] is False,'exact finite saved Guest10 receipt scope')
  acceptance=g['guest10RootAcceptance'];pin(acceptance['path'],acceptance);need(load(acceptance['path'])==pr['guestRootAcceptanceSchema'],'exact future root acceptance schema')
'''+s[b:]
s=s.replace("need([e['workload']for e in pr['entries']if 'retained'in e]==['md5sum','nettle-sha256'],'exact retained complement')","need(all('retained' not in e for e in pr['entries']),'no retained workloads')")
a=s.index("  owner=load(pr['actualOwnerProof'])\n");b=s.index("  source=O/",a)
s=s[:a]+'''  for e in pr['entries']:
   n=e['workload'];src=O/(n+'.kotoba');src.write_bytes(Path(e['source']['path']).read_bytes());src.chmod(0o444);need(receipt(src)=={k:e['source'][k]for k in ['bytes','sha256']},'exact whole original source copy');capture(src,4194304);image=build(n,src,e['symbol'],1,pr['producer']);image.update(workload=n,retained=False,iterations=e['iterations'],source=e['source']);images.append(image);save(O/'images.json',images)
  need(len(rows)==38 and len(images)==19,'original19 fresh38 phase boundary');save(O/'original19-boundary.json',dict(newClosedCalls=38,retainedClosedCalls=0,joinedClosedCompileExtractCalls=38,workloads=19,generatedWorkloadExecution=False))
'''+s[b:]
s=s.replace('unity-lc-on.kotoba','unity-df-on.kotoba').replace('COMPLETE_LC_ORIGINAL19_COMPILATION','COMPLETE_FUEL_DAG_ORIGINAL19_COMPILATION').replace('closedLoaderCalls=40','closedLoaderCalls=44').replace('retainedOrdinaryCalls=4','retainedOrdinaryCalls=0')
# Whole G0-to-G1 difference is recorded prospectively, including first container mismatch.
s=s.replace("generations.append(image);", "image['producer']=dict(path=producer,**receipt(producer));image['source']=dict(path=str(source),**receipt(source));generations.append(image);")
s=s.replace("image['G0ToG1ContainerEquality']=Path(oldContainer['path']).read_bytes()==Path(image['container']['path']).read_bytes()", "oldK=Path(oldContainer['path']).read_bytes();newK=Path(image['container']['path']).read_bytes();image['G0ToG1ContainerEquality']=oldK==newK;image['G0ToG1ContainerFirstDifferentByte']=next((i for i,(a,b)in enumerate(zip(oldK,newK))if a!=b),None if len(oldK)==len(newK)else min(len(oldK),len(newK)))")
ast.parse(s);(D/'run.py').write_text(s)
save('ledger-origin.json',dict(origin=pr['callLedgerOrigin'],changes=['call cap40 to44 and label only within call Ledger','prerequisite guards fuel DAG and exact Guest10 receipt/root acceptance','all19 fresh38; retained skip removed','G1/G2/G3 six calls preserved; lineage recorded'],nativeCalls=0))
print(json.dumps(dict(files=len(ip),bytes=sum(z['bytes']for z in ip.values()),driver=rec(D/'run.py'))))
