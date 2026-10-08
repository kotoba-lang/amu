"""Source authoring only. Does not execute native/compiler/SSH."""
from pathlib import Path
import json,hashlib,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');R=Path('/Users/junkawasaki/github/wt/amu-seed17');D=Path(__file__).resolve().parent
P=W/'vector-leaf-straight-read-cache-owner-observer10-source-v2-native-controls';L=W/'vector-leaf-straight-read-cache-source-v1-native-controls';A=W/'vector-leaf-straight-read-cache-owner10-actual-review-v2-controls'
def receipt(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size<=402653184
 return dict(bytes=s.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
old=load(P/'preregistration.json');ip=load(P/'input-pins.json');ip[str(P/'input-pins.json')]=receipt(P/'input-pins.json')
for parent in [A,W/'vector-leaf-straight-read-cache-build4-actual-review-v2-controls',W/'vector-masked32-source-bound-loader-actual-review-v2-width']:
 for name in ['report.json','input-pins.json']:
  p=parent/name;ip[str(p)]=receipt(p)
 for p,z in load(parent/'input-pins.json').items():
  assert p not in ip or ip[p]=={k:z[k] for k in ['bytes','sha256']}
  ip[p]={k:z[k] for k in ['bytes','sha256']}
for name in ['report.json','terminal.json','attempts.json','generated-pins.json','images.json']:
 p=P/'run-outputs'/name;ip[str(p)]=receipt(p)
for p,z in load(P/'run-outputs/generated-pins.json').items():ip[p]=z
matrix=R/'bench/embench/comparison-matrix.json';m=load(matrix);ip[str(matrix)]=receipt(matrix)
assert m['format']=='amu.embench-comparison-matrix-spec/v1' and m['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70' and len(m['entries'])==19
entries=[]
for e in m['entries']:
 p=R/e['source'];z=receipt(p);assert z['sha256']==e['expectedSourceSha256'];ip[str(p)]=z
 q=dict(workload=e['workload'],source=dict(path=str(p),**z),symbol=e['symbol'],iterations=e['iterations'])
 if e['workload'] in ['md5sum','nettle-sha256']:
  q['retained']=dict(container=dict(path=str(P/'run-outputs'/('ordinary-'+e['workload']+'.kseed')),**receipt(P/'run-outputs'/('ordinary-'+e['workload']+'.kseed'))),native=dict(path=str(P/'run-outputs'/('ordinary-'+e['workload']+'.bin')),**receipt(P/'run-outputs'/('ordinary-'+e['workload']+'.bin'))))
 entries.append(q)
assert len(ip)<=2048 and sum(z['bytes'] for z in ip.values())<=402653184
save(D/'input-pins.json',dict(sorted(ip.items())))
pr={k:old[k] for k in ['producer','producerSHA256','loader','actualProducerProof','actualProducerProofStatus','actualLoaderProof','actualLoaderProofStatus','parentSource','parentSourcePinsSHA256','stdoutBytesMaximum','stderrBytesMaximum','fileHardLimitBytes','wallSeconds','reapSeconds','compileResources']}
pr.update(status='PROSPECTIVE_LC_FULL19_SELFBUILD40_BEFORE_DRIVER_AUTHORING',schema='LC_FULL19_SELFBUILD40/v1',maximumLoaderCalls=40,remainingWorkloadCalls=34,retainedOrdinaryWorkloadCalls=4,joinedOriginal19CompileExtractCalls=38,selfbuildCalls=6,stageOrder=['canonical-order17-complement-md5-sha compile/extract34','G0-to-G1 compile/extract2','G1-to-G2 compile/extract2','G2-to-G3 compile/extract2'],generationNames=['G0','G1','G2','G3'],equalityRequired=['G1=G2=G3 whole KSEED/native/export/main0'],G0ToG1='Record exact hashes/sizes/first difference; difference allowed, no performance or unsafe semantic equivalence claim',actualOwnerProof=str(A/'report.json'),actualOwnerProofStatus='PASS_INDEPENDENT_ACTUAL_READONLY_LC_OWNER_OBSERVER10_IDENTITY_LAYOUT_ONLY',actualOwnerInputPins=str(A/'input-pins.json'),canonicalMatrix=str(matrix),entries=entries,freshOutputRoot=str(D/'run-outputs'),rootGOStatus='ROOT_AUTHORIZED_LC_FULL19_SELFBUILD40_COMPILE_ONLY',sourceReviewStatus='PASS_SOURCE_ONLY_LC_FULL19_SELFBUILD40',inputPinsSHA256=receipt(D/'input-pins.json')['sha256'],exactInputFiles=len(ip),exactInputLogicalBytes=sum(z['bytes'] for z in ip.values()),maximumInputFiles=2048,maximumInputLogicalBytes=402653184,nativeBytesMaximum=4194304,containerBytesMaximum=4194560,noRetry=True,firstFailureStop=True,timingAuthorized=False,workloadGuestAuthorized=False,maximumChildWallAndReapSeconds=73600,maximumOutputDiskBytes=2147483648,qualification='Original19 compilation and repeated LC source selfbuild only; no generated workload execution, ABI/trap/fuel/frame correctness, full selfhost goal, C runtime or official score qualification',LCFrameScope='Existing observed two owners frame112 plus16 FP/LR=128 only; no new universal frame/stack/resource theorem',authoring='Isolated diagnostic driver authoring; no product mutation or optimizer changes',callLedgerOrigin=dict(path=str(P/'run.py'),**receipt(P/'run.py')))
save(D/'preregistration.json',pr)
# Preregistration is now written BEFORE driver authoring below.
s=(P/'run.py').read_text();prefix=s[:s.index('def main(')];call=s[s.index(' def call('):s.index('\n try:\n  decoderPath')].replace('len(rows)<10','len(rows)<40').replace('finite18 no retry','finite40 no retry')
main='''def parse_container(b):
 need(0<len(b)<=4194560,'bounded container');m=re.match(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)\\n',b);need(m is not None,'KSEED header');n=int(m[2]);need(n<=128,'export cap');cut=b.find(b'\\n\\n',m.end());need(cut>=m.end(),'export separator');lines=b[m.end():cut].splitlines();need(len(lines)==n,'export count');exports=[]
 for line in lines:
  q=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',line);need(q is not None,'export schema');exports.append((q[1].decode(),int(q[2]),int(q[3])))
 payload=b[cut+2:];need(0<len(payload)<=4194304 and len(payload)==int(m[1]),'whole declared payload');need(len({z[0]for z in exports})==n,'unique names');need(all(z[1]%4==0 and z[1]+4<=len(payload)and z[2]<=32 for z in exports),'bounded aligned entries');return payload,exports
def main(gopath):
 gp=Path(gopath);g=load(gp);gh=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);L=Path(pr['parentSource']).parent
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==40 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['workloadGuestAuthorized']is False,'exact40 GO')
 need(g['sourcePinsSHA256']==receipt(D/'source-pins.json')['sha256']and g['driverSHA256']==receipt(D/'run.py')['sha256']and g['preregistrationSHA256']==receipt(D/'preregistration.json')['sha256']and g['inputPinsSHA256']==pr['inputPinsSHA256']==receipt(D/'input-pins.json')['sha256'],'exact registries')
 need(len(g['sourceReviews'])==2 and len({z['path']for z in g['sourceReviews']})==2,'two specific SOURCE reviews');extra={}
 def guard():
  need(receipt(gp)==gh and receipt(D/'source-pins.json')['sha256']==g['sourcePinsSHA256']and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256']and receipt(D/'preregistration.json')['sha256']==g['preregistrationSHA256'],'immutable registries')
  for n,z in sp.items():pin(D/n,z)
  need(len(ip)==pr['exactInputFiles']<=2048 and sum(z['bytes']for z in ip.values())==pr['exactInputLogicalBytes']<=402653184,'closure cap');total=0
  for p,z in ip.items():
   q=Path(p);st=q.lstat();need(stat.S_ISREG(st.st_mode)and not q.is_symlink()and st.st_size==z['bytes'],'stat before read');total+=st.st_size;need(total<=402653184,'aggregate before hash')
  for p,z in ip.items():pin(p,z)
  need(receipt(L/'source-pins.json')['sha256']==pr['parentSourcePinsSHA256'],'structured parent pins');em=load(L/'source-pins.json');need(set(em)=={'format','files'}and em['format']=='isolated-source-pins/v1'and type(em['files'])is list and len({z['path']for z in em['files']})==len(em['files']),'structured exact schema')
  for z in em['files']:need(set(z)=={'path','bytes','sha256'}and Path(z['path']).is_relative_to(L)and str(z['path'])in ip,'owned source receipt');pin(z['path'],z)
  for p,z in extra.items():pin(p,z)
  need(ip[pr['producer']]['sha256']==pr['producerSHA256']=='258670d2371f3c03167fb02f574c6597479a1ce3e0af9a42cac8e41499d56931'and ip[pr['loader']]['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f','producer/loader')
  for k in ['actualProducerProof','actualLoaderProof','actualOwnerProof']:need(load(pr[k])['status']==pr[k+'Status'],'exact actual prerequisite')
  ar=load(pr['actualProducerProof']);need(ar['counts']['closedLoaderCalls']==4 and next(z for z in ar['images']if z['arm']=='ON')['native']==dict(path=pr['producer'],**ip[pr['producer']]),'producer actual correspondence')
  owner=load(pr['actualOwnerProof']);need(owner['inputPinsSHA256']==receipt(pr['actualOwnerInputPins'])['sha256']and owner['counts']['closedLoaderCalls']==10 and owner['counts']['ordinaryWorkloads']==2 and owner['checks']['wholeOrdinaryObservedContainersNativeExportsOffsetsIdentical']is True,'actual owner10 join')
  mat=load(pr['canonicalMatrix']);need(mat['format']=='amu.embench-comparison-matrix-spec/v1'and mat['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'and len(mat['entries'])==19,'canonical19')
  need(len(pr['entries'])==19 and len({e['workload']for e in pr['entries']})==19,'all19 unique')
  for e,me in zip(pr['entries'],mat['entries']):need(e['workload']==me['workload']and e['symbol']==me['symbol']and e['iterations']==me['iterations']and e['source']['sha256']==me['expectedSourceSha256']and e['source']['path'].endswith('/'+me['source']),'matrix exact whole-source binding');pin(e['source']['path'],e['source'])
  need([e['workload']for e in pr['entries']if 'retained'in e]==['md5sum','nettle-sha256'],'exact retained complement')
  for z in g['sourceReviews']:
   r=load(pin(z['path'],z));need(r['status']==pr['sourceReviewStatus']and r['sourcePinsSHA256']==g['sourcePinsSHA256']and r['driverSHA256']==g['driverSHA256']and r['preregistrationSHA256']==g['preregistrationSHA256'],'specific complete reviews')
 guard();need(not O.exists(),'fresh namespace');O.mkdir();rows=[];images=[];generations=[];ok=False;save(O/'attempts.json',rows)
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1'}
 save(O/'effective-environment.json',env)
 def capture(p,maximum):
  need(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=maximum,'bounded artifact');extra[str(p)]=receipt(p);save(O/'generated-pins.json',extra);return dict(path=str(p),**extra[str(p)])
'''
ending='''
 try:
  def build(label,src,symbol,arity,producer):
   k=O/(label+'.kseed');b=O/(label+'.bin');raw=call(label+'-compile',['compile',str(src),'--target','aarch64-macos','--output',str(k)],producer);need(b':ok true'in raw and b':ok false'not in raw,'compile success');kr=capture(k,pr['containerBytesMaximum']);payload,exports=parse_container(k.read_bytes());entry=[z for z in exports if z[0]==symbol];need(len(entry)==1 and entry[0][2]==arity,'exact selected export ABI')
   if arity==0:need(exports==[('main',0,0)],'sole main0 compiler')
   raw2=call(label+'-extract',['extract-native',str(k),'--symbol',symbol,'--output',str(b)],producer);br=capture(b,pr['nativeBytesMaximum']);need(b':ok true'in raw2 and b':ok false'not in raw2,'extract success');offsets=re.findall(rb':offset ([0-9]+)\\b',raw2);need(len(offsets)==1 and int(offsets[0])==entry[0][1],'exact extract offset');need(b.read_bytes()==payload,'whole native payload');return dict(label=label,container=kr,native=br,exports=exports,offset=entry[0][1])
  owner=load(pr['actualOwnerProof'])
  for e in pr['entries']:
   n=e['workload']
   if 'retained'in e:
    z=e['retained'];k=pin(z['container']['path'],z['container']);b=pin(z['native']['path'],z['native']);payload,exports=parse_container(k.read_bytes());need(payload==b.read_bytes(),'retained whole payload');entry=[q for q in exports if q[0]==e['symbol']];need(len(entry)==1 and entry[0][2]==1,'retained ABI');w=next(q for q in owner['workloads']if q['workload']==n);need(receipt(b)=={k:w['native'][k]for k in ['bytes','sha256']}and entry[0][1]==w['offset'],'actual retained identity');image=dict(workload=n,retained=True,container=z['container'],native=z['native'],exports=exports,offset=entry[0][1]);images.append(image)
   else:
    src=O/(n+'.kotoba');src.write_bytes(Path(e['source']['path']).read_bytes());src.chmod(0o444);need(receipt(src)=={k:e['source'][k]for k in ['bytes','sha256']},'exact source copy');capture(src,4194304);image=build(n,src,e['symbol'],1,pr['producer']);image.update(workload=n,retained=False);images.append(image)
   save(O/'images.json',images)
  need(len(rows)==34 and len(images)==19,'original19 joined38 phase boundary');save(O/'original19-boundary.json',dict(newClosedCalls=34,retainedClosedCalls=4,joinedClosedCompileExtractCalls=38,workloads=19,generatedWorkloadExecution=False))
  source=O/'unity-lc-on.kotoba';source.write_bytes(Path(pr['parentSource']).read_bytes());source.chmod(0o444);need(receipt(source)==ip[pr['parentSource']],'immutable exact selfbuild source');capture(source,4194304);producer=pr['producer'];previous=None
  for generation in [1,2,3]:
   image=build('G'+str(generation),source,'main',0,producer);image['generation']=generation
   if previous is not None:need(Path(image['container']['path']).read_bytes()==Path(previous['container']['path']).read_bytes()and Path(image['native']['path']).read_bytes()==Path(previous['native']['path']).read_bytes(),'G1 G2 G3 fixed point whole artifact')
   else:
    old=Path(pr['producer']).read_bytes();new=Path(image['native']['path']).read_bytes();image['G0ToG1NativeEquality']=old==new;image['G0ToG1FirstDifferentByte']=next((i for i,(a,b)in enumerate(zip(old,new))if a!=b),None if len(old)==len(new)else min(len(old),len(new)));image['G0ToG1EqualityRequired']=False
   generations.append(image);save(O/'generations.json',generations);previous=image;producer=image['native']['path']
  guard();need(len(rows)==40 and len(generations)==3,'exact40');save(O/'report.json',dict(status='COMPLETE_LC_ORIGINAL19_COMPILATION_G1_G2_G3_FIXEDPOINT_ONLY',closedLoaderCalls=40,original19JoinedCompileExtractCalls=38,retainedOrdinaryCalls=4,selfbuildCalls=6,images=images,generations=generations,sourcePinsSHA256=g['sourcePinsSHA256'],rootGOSHA256=gh['sha256'],runtimeWorkloadExecution=False,runtimeABITrapFuelQualified=False,performanceQualified=False,officialScore=False,fullSelfhostGoalAchieved=False));ok=True
 except BaseException as ex:save(O/'failure.json',dict(error=type(ex).__name__+': '+str(ex),loaderCalls=len(rows),firstFailureStop=True,noRetry=True));raise
 finally:save(O/'terminal.json',dict(loaderCalls=len(rows),allChildrenClosed=all(r['state']=='terminal'for r in rows),failure=not ok))
if __name__=='__main__':need(len(sys.argv)==2,'root GO only');main(sys.argv[1])
'''
ending=ending.replace("image['G0ToG1EqualityRequired']=False", "image['G0ToG1EqualityRequired']=False;oldContainer=next(z for z in load(pr['actualProducerProof'])['images']if z['arm']=='ON')['container'];image['G0Container']=oldContainer;image['G0Native']=dict(path=pr['producer'],**ip[pr['producer']]);image['G0ToG1ContainerEquality']=Path(oldContainer['path']).read_bytes()==Path(image['container']['path']).read_bytes()")
(D/'run.py').write_text(prefix+main+call+ending)
save(D/'ledger-origin.json',dict(origin=pr['callLedgerOrigin'],changes=['cap10 to40','finite label message18 to40'],sourceGuardStructured=True,nativeCalls=0))
print(json.dumps(dict(inputFiles=len(ip),logicalBytes=sum(z['bytes']for z in ip.values()),driver=receipt(D/'run.py'),prereg=receipt(D/'preregistration.json'))))
