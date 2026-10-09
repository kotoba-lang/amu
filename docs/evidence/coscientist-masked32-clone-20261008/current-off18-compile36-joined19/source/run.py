"""Inert SOURCE. Current7618 OFF18 compile36 commands only after exact two reviews and GO."""
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
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);rows=[];images=[];generated={};ok=False
 need(set(g)=={'status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','integrationFixtureProof','baselineActualProof','TCActualProof'},'exact GO keys')
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==36 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is False and g['C2']is False,'exact36 scope')
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'GO identity')
 need(len(g['sourceReviews'])==2 and len(set(r['path']for r in g['sourceReviews']))==2,'two exact reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'specific reviews')
 need(g['integrationFixtureProof']==pr['qualifiedIntegrationFixtureProof'],'exact fixture');f=load(pin(g['integrationFixtureProof']['path'],g['integrationFixtureProof']));need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','qualified capture scope')
 for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'same actual fixture components')
 for n in ['baselineActualProof','TCActualProof']:need(g[n]==pr[n],'fixed proof');pin(g[n]['path'],g[n])
 baseline=load(pr['baselineActualProof']['path']);tc=load(pr['TCActualProof']['path']);need(baseline['status']==pr['baselineActualProofStatus']and baseline['currentProducerBindingQualified']is True and baseline['wholeBaselineNative']==ip[pr['producer']],'exact current7618 actual binding');need(tc['status']==pr['TCActualProofStatus']and tc['joinedOriginal19ArtifactWholePayloadIdentity']is True and tc['G0G1G2G3WholeNativeEqual']is True and tc['G0G1G2G3WholeContainerEqual']is True,'current TC comparative lineage only')
 def guard():
  need(receipt(gp)==gr and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256'],'immutable registries')
  need(len(ip)==pr['exactInputFiles']<=3072 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']<=469762048,'bounded full closure')
  for n,r in sp.items():pin(D/n,r)
  for p,r in ip.items():pin(p,r)
  for p,r in generated.items():pin(p,r)
  a=load(D/'source-assembly.json');need(len(a['modules'])==16 and len(a['modulePins'])==16,'current16 baseline closure');whole=b''.join(Path(r['path']).read_bytes()+b'\n'for r in a['modulePins']);need(whole==Path(pr['ownSource']).read_bytes()and receipt(pr['ownSource'])['sha256']=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418','unmodified baseline current16, noTC41')
  payload,exports=container(Path(pr['candidateContainer']).read_bytes());need(payload==Path(pr['producer']).read_bytes()and exports==[('main',0,0)]and ip[pr['producer']]['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93','full current7618 only')
  matrix=load(pr['canonicalMatrix']);need(len(matrix['entries'])==19 and matrix['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70','canonical19')
  for e,m in zip(pr['entries'],matrix['entries']):need(e['workload']==m['workload']and e['symbol']==m['symbol']and e['iterations']==m['iterations']and e['source']['sha256']==m['expectedSourceSha256']and e['source']['path'].endswith('/'+m['source']),'whole workloads/profiles unchanged')
 guard();need(not O.exists(),'fresh namespace');O.mkdir();save(O/'attempts.json',rows);save(O/'effective-environment.json',pr['environment'])
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 def artifact(p):
  r=receipt(p);need(r['bytes']<=4194560,'bounded artifact');generated[str(p)]=r;save(O/'generated-pins.json',generated);return dict(path=str(p),**r)
 def call(case):
  guard();inputPath=Path(case['nativeArgv'][8]);seal={'format':pr['invocationSealVersion'],'index':len(rows)+1,'label':case['label'],'nativeArgv':case['nativeArgv'],'producer':dict(path=pr['producer'],**ip[pr['producer']]),'producerContainer':dict(path=pr['candidateContainer'],**ip[pr['candidateContainer']]),'input':dict(path=str(inputPath),**receipt(inputPath)),'outputPath':case['outputPath'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256']};sealPath=O/(case['label']+'.admission.json');need(not sealPath.exists()and not Path(case['outputPath']).exists()and not Path(case['outputPath']).is_symlink(),'fresh outputs');save(sealPath,seal);sealPath.chmod(0o444);sr=artifact(sealPath);return mod.call(D,O,pr,case,rows,save,sr['sha256'])
 try:
  retained=pr['retainedCRC'];need(baseline['wholeOriginalCRCNative']==ip[retained['native']['path']]and baseline['wholeOriginalCRCContainer']==ip[retained['container']['path']]and baseline['benchOffset']==1224,'retained original CRC proof');payload,exports=container(pin(retained['container']['path'],retained['container']).read_bytes());need(payload==pin(retained['native']['path'],retained['native']).read_bytes()and ('bench',1224,1)in exports,'retained CRC full payload ABI');crc=next(e for e in pr['entries']if e['workload']=='crc32');need({k:pr['retainedCRCOriginalSource'][k]for k in ['bytes','sha256']}=={k:crc['source'][k]for k in ['bytes','sha256']},'retained CRC original source exact');images.append(dict(retained,source=crc['source'],iterations=crc['iterations'],exports=exports,retained=True));save(O/'images.json',images)
  for e in pr['entries']:
   if e['workload']=='crc32':continue
   n=e['workload'];src=O/(n+'.kotoba');src.write_bytes(Path(e['source']['path']).read_bytes());src.chmod(0o444);need(receipt(src)=={k:e['source'][k]for k in ['bytes','sha256']},'whole source');artifact(src);c=pr['cases'][len(rows)];need(c['label']==n+'-compile','fixed compile order');r=call(c);kr=artifact(Path(c['outputPath']));need(r['report']['containerBytes']==kr['bytes'],'whole stdout size');payload,exports=container(Path(c['outputPath']).read_bytes());entry=[x for x in exports if x[0]==e['symbol']];need(len(entry)==1 and entry[0][2]==1,'selected export ABI');c=pr['cases'][len(rows)];need(c['label']==n+'-extract','fixed extract order');r=call(c);nr=artifact(Path(c['outputPath']));need(Path(c['outputPath']).read_bytes()==payload and r['report']=={'kind':'extract','offset':entry[0][1],'nativeBytes':len(payload),'arity':1},'whole native payload/offset');images.append(dict(workload=n,source=e['source'],iterations=e['iterations'],container=kr,native=nr,offset=entry[0][1],exports=exports,retained=False));save(O/'images.json',images)
  guard();need(len(rows)==36 and len(images)==19,'18fresh1retained');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed']is True and terminal['failure']is False,'durable closed terminal');evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['terminal.json','attempts.json','generated-pins.json','images.json','effective-environment.json']};save(O/'report.json',{'status':'COMPLETE_CURRENT7618_OFF_JOINED_ORIGINAL19_ARTIFACT_IDENTITY_ONLY','newClosedCompilerCalls':36,'retainedClosedCompilerCalls':2,'joinedOriginal19CompileExtractCalls':38,'images':images,'baselineActualProof':g['baselineActualProof'],'TCActualProof':g['TCActualProof'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'evidence':evidence,'runtimeGuestExecuted':False,'performanceQualified':False,'hardPeakQualified':False,'strictPhysicalMemoryQualified':False,'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact GO');main(sys.argv[1])
