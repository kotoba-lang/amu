"""Inert SOURCE. Remaining10 native compiler commands only after exact two reviews and GO."""
from pathlib import Path
import json,hashlib,stat,importlib.util,re,os
D=Path(__file__).resolve().parent

def need(v,m):
 if not v:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def receipt(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=469762048,'bounded regular pin');b=p.read_bytes();s2=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(s2.st_dev,s2.st_ino,s2.st_size,s2.st_mtime_ns),'immutable bytes');return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def pin(p,r):need(receipt(p)=={k:r[k]for k in ['bytes','sha256']},'exact pin:'+str(p));return Path(p)
def save(p,v):
 b=(json.dumps(v,indent=2)+'\n').encode();need(len(b)<=16777216,'bounded valid-last metadata');q=Path(str(p)+'.pending')
 with q.open('wb',buffering=0)as f:
  view=memoryview(b)
  while view:
   n=f.write(view);need(type(n)is int and 0<n<=len(view),'metadata write');view=view[n:]
  os.fsync(f.fileno())
 os.replace(q,p);fd=os.open(str(Path(p).parent),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def container(raw):
 need(0<len(raw)<=4194560,'bounded KSEED');m=re.match(rb'KSEED1 ([1-9][0-9]{0,9}) ([1-9][0-9]{0,2})\n',raw);need(m is not None,'header');cut=raw.find(b'\n\n',m.end());need(cut>=m.end(),'separator');lines=raw[m.end():cut].splitlines();n=int(m[2]);need(1<=n<=128 and len(lines)==n,'exports');exports=[]
 for line in lines:
  q=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]{1,10}) ([0-9]{1,2})',line);need(q is not None,'export line');exports.append((q[1].decode(),int(q[2]),int(q[3])))
 payload=raw[cut+2:];need(0<len(payload)<=4194304 and len(payload)==int(m[1]) and len(set(x[0]for x in exports))==n,'whole payload/unique');need(all(x[1]%4==0 and x[1]+4<=len(payload)and x[2]<=32 for x in exports),'entry ABI');return payload,exports

def main(goPath):
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);rows=[];images=[];generations=[];generated={};ok=False
 need(set(g)=={'status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','integrationFixtureProof','retainedArtifactProof','retainedSuiteProof'},'exact GO keys');need(g['C2'] is False,'C2 OFF');need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==10 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is False,'fixed remaining10 GO scope')
 for name,key in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/name)['sha256']==g[key],'GO binding')
 need(g['retainedArtifactProof']==pr['retainedArtifactProof'],'exact prereg retained proof');retainedProof=load(pin(g['retainedArtifactProof']['path'],g['retainedArtifactProof']));need(retainedProof['status']==pr['retainedArtifactProofStatus'],'independent retained artifact identity only');rp=retainedProof['conditionalAhaArtifactIdentityOnly'];need(retainedProof['independent'] is True and retainedProof['closedCalls']==2 and retainedProof['remainingUnexecutedCalls']==42 and retainedProof['campaignQualified'] is False and retainedProof['strictMemoryQualification'] is False and rp['verified'] is True and rp['wholePayloadEqual'] is True and rp['container']==dict(path=pr['retainedContainer'],**ip[pr['retainedContainer']]) and rp['native']==dict(path=pr['retainedArtifact'],**ip[pr['retainedArtifact']]) and rp['originalSource']==pr['retainedWorkload']['source'] and rp['producer']==dict(path=pr['producer'],**ip[pr['producer']]) and rp['selectedExport']==['bench',3456,1],'exact retained aha identity scope')
 need(g['retainedSuiteProof']==pr['retainedSuiteProof'],'exact retained suite proof');suite=load(pin(g['retainedSuiteProof']['path'],g['retainedSuiteProof']));need(suite['status']==pr['retainedSuiteProofStatus'] and suite['independent'] is True and suite['newClosedCalls']==32 and suite['remainingUnexecutedCalls']==10 and suite['campaignQualified'] is False and suite['newGenerationsExecuted']==0 and suite['strictJoinedPhysicalMemoryQualified'] is False and suite['campaignAdmittedFreshWorkloadPairs']==15 and suite['conditionallyByteIdenticalJoinedPairsIncludingRetainedAha']==17 and suite['missingOriginalWorkloads']==['wikisort','xgboost'],'exact saved suite partial scope')
 need(g['integrationFixtureProof']==pr['qualifiedIntegrationFixtureProof'],'same exact qualified capture controller proof')
 need(len(g['sourceReviews'])==2 and len(set(x['path']for x in g['sourceReviews']))==2,'two reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'exact SOURCE reviews')
 fp=g['integrationFixtureProof'];f=load(pin(fp['path'],fp));need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','actual fixture scope')
 for name,key in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[key]==sp[name]['sha256'],'exact copied qualified capture components')
 def guard():
  need(receipt(gp)==gr,'immutable GO');need(receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256'],'input registry')
  need(len(ip)==pr['exactInputFiles']<=3072 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']<=469762048,'complete closure bounds')
  for n,r in sp.items():pin(D/n,r)
  for p,r in ip.items():pin(p,r)
  for p,r in generated.items():pin(p,r)
  a=load(pr['sourceAssembly']);parts=[]
  need(len(a['modules'])==16 and len(a['modulePins'])==16,'current16 exact closure')
  for name,r in zip(a['modules'],a['modulePins']):parts.append(Path(a['candidate41']['path']if name=='seed/41-a64gen.kotoba'else r['path']).read_bytes()+b'\n')
  need(b''.join(parts)==Path(pr['ownSource']).read_bytes(),'whole TC current16 source reproduction')
  need(a['candidate41']['sha256']=='3d7c169818cdf0fabc151da98017d3b28bbe38fc3407d9b42921b646520c2aba'and next(r for r in a['modulePins']if r['path'].endswith('/42-layout.kotoba'))['sha256']=='413c08728156173f162602f691a33fdca2ed0f4ae034063a85f546c9cfb11eb8','TC/layout lineage')
  saved=load(Path(pr['candidateContainer']).parent/'generated-pins.json');need(saved[pr['producer']]==ip[pr['producer']]and saved[pr['candidateContainer']]==ip[pr['candidateContainer']],'saved emission pins')
  payload,ex=container(Path(pr['candidateContainer']).read_bytes());need(payload==Path(pr['producer']).read_bytes()and ex==[('main',0,0)],'G0 full payload and sole main0')
  mat=load(pr['canonicalMatrix']);need(mat['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'and len(mat['entries'])==19,'canonical full19')
  for e,m in zip(pr['entries'],mat['entries']):need(e['workload']==m['workload']and e['symbol']==m['symbol']and e['iterations']==m['iterations']and e['source']['sha256']==m['expectedSourceSha256']and e['source']['path'].endswith('/'+m['source']),'unchanged workloads/profiles')
  for p in pr['lineageEvidence']:need(receipt(p)==ip[p],'conditional saved independent source/emission evidence')
 guard();need(not O.exists(),'fresh output namespace');O.mkdir();save(O/'attempts.json',rows);save(O/'effective-environment.json',pr['environment'])
 spec=importlib.util.spec_from_file_location('bounded_native_call',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 def artifact(p):
  r=receipt(p);need(r['bytes']<=4194560,'artifact cap');generated[str(p)]=r;save(O/'generated-pins.json',generated);return dict(path=str(p),**r)
 def call(case):
  guard();producer=Path(case['nativeArgv'][1]);producerContainer=Path(pr['candidateContainer'])if str(producer)==pr['producer']else producer.with_suffix('.kseed');inputPath=Path(case['nativeArgv'][8]);seal={'format':pr['invocationSealVersion'],'index':len(rows)+1,'label':case['label'],'nativeArgv':case['nativeArgv'],'producer':dict(path=str(producer),**receipt(producer)),'producerContainer':dict(path=str(producerContainer),**receipt(producerContainer)),'input':dict(path=str(inputPath),**receipt(inputPath)),'outputPath':case['outputPath'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256']};sealPath=O/(case['label']+'.admission.json');need(not sealPath.exists() and not Path(case['outputPath']).exists() and not Path(case['outputPath']).is_symlink(),'fresh invocation/output');save(sealPath,seal);sealPath.chmod(0o444);sr=artifact(sealPath);result=mod.call(D,O,pr,case,rows,save,sr['sha256']);need(result['returncode']==0,'complete semantic/artifact raw admission');return result
 def build(label,symbol,arity):
  compileCase=pr['cases'][len(rows)];need(compileCase['label']==label+'-compile','fixed order');c=call(compileCase);k=Path(compileCase['outputPath']);kr=artifact(k);need(c['report']['containerBytes']==kr['bytes'],'exact raw container size');payload,ex=container(k.read_bytes());entry=[x for x in ex if x[0]==symbol];need(len(entry)==1 and entry[0][2]==arity,'selected exact export')
  if arity==0:need(ex==[('main',0,0)],'whole compiler sole main0')
  extractCase=pr['cases'][len(rows)];need(extractCase['label']==label+'-extract','fixed order');e=call(extractCase);b=Path(extractCase['outputPath']);br=artifact(b);need(b.read_bytes()==payload and e['report']=={'kind':'extract','offset':entry[0][1],'nativeBytes':len(payload),'arity':arity},'whole extracted native payload/ABI');return {'label':label,'container':kr,'native':br,'exports':ex,'offset':entry[0][1]}
 try:
  retainedManifest=load(pr['retainedImages']);expected=[dict(workload='aha-mont64',source=rp['originalSource'],container=rp['container'],native=rp['native'],exports=rp['exports'],selectedExport=rp['selectedExport'],wholePayloadEqual=True,admittedByCampaign=False,conditionalArtifactIdentityOnly=True)]+suite['freshSavedArtifactIdentityObservations'];need(retainedManifest==expected and len(retainedManifest)==17,'exact seventeen independent artifact records')
  for e,retained in zip(pr['entries'][:17],retainedManifest):
   need(e['workload']==retained['workload'] and e['source']==retained['source'] and retained['wholePayloadEqual'] is True,'unchanged retained original source');payload,exports=container(pin(retained['container']['path'],retained['container']).read_bytes());need(payload==pin(retained['native']['path'],retained['native']).read_bytes() and [list(x)for x in exports]==retained['exports'],'retained whole native payload/exports');selected=[x for x in exports if x[0]==e['symbol']];need(len(selected)==1 and list(selected[0])==retained['selectedExport'] and selected[0][2]==1,'retained selected ABI');images.append(dict(retained,iterations=e['iterations'],offset=selected[0][1],retained=True));save(O/'images.json',images)
  for e in pr['entries'][17:]:
   n=e['workload'];src=O/(n+'.kotoba');src.write_bytes(Path(e['source']['path']).read_bytes());src.chmod(0o444);need(receipt(src)=={k:e['source'][k]for k in ['bytes','sha256']},'whole original source');artifact(src);im=build(n,e['symbol'],1);im.update(workload=n,source=e['source'],iterations=e['iterations']);images.append(im);save(O/'images.json',images)
  need(len(rows)==4 and len(images)==19,'joined full19 phase2fresh17retained');src=O/'unity-tc.kotoba';src.write_bytes(Path(pr['ownSource']).read_bytes());src.chmod(0o444);artifact(src)
  prior={'container':dict(path=pr['candidateContainer'],**ip[pr['candidateContainer']]),'native':dict(path=pr['producer'],**ip[pr['producer']])}
  for gen in [1,2,3]:
   im=build('G'+str(gen),'main',0);im.update(generation=gen,ownSource=artifact(src));im['previousContainerEqual']=Path(im['container']['path']).read_bytes()==Path(prior['container']['path']).read_bytes();im['previousNativeEqual']=Path(im['native']['path']).read_bytes()==Path(prior['native']['path']).read_bytes();im['equalityRequired']=gen>1
   if gen>1:need(im['previousContainerEqual']and im['previousNativeEqual'],'G1 G2 G3 whole byteidentity')
   generations.append(im);save(O/'generations.json',generations);prior=im
  guard();need(len(rows)==10 and len(images)==19 and len(generations)==3,'exact10new38joined');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed'] is True and terminal['failure'] is False,'durable terminal before COMPLETE');evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['terminal.json','attempts.json','generated-pins.json','images.json','generations.json','effective-environment.json']};save(O/'report.json',{'status':'COMPLETE_TC_JOINED_ORIGINAL19_ARTIFACT_IDENTITY_G1_G2_G3_FIXEDPOINT_MEMORY_PARTIAL_ONLY','newClosedLoaderCalls':10,'retainedClosedCompileExtractCalls':34,'joinedOriginal19CompileExtractCalls':38,'strictPhysicalMemoryQualified':False,'retainedArtifactProof':g['retainedArtifactProof'],'retainedSuiteProof':g['retainedSuiteProof'],'retainedUnadmittedUDRemainsRefused':True,'images':images,'generations':generations,'sourcePinsSHA256':g['sourcePinsSHA256'],'rootGO':dict(path=str(gp),**gr),'evidence':evidence,'runtimeGuestExecuted':False,'performanceQualified':False,'officialScore':False,'fullSelfhostGoalAchieved':False,'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact GO');main(sys.argv[1])
