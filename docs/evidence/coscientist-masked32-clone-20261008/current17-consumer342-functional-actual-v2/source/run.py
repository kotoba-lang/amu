"""Inert SOURCE. Current HFT G4 with qualified heldV6 original19 runtime190 only after exact two reviews and GO."""
from pathlib import Path
import json,hashlib,stat,importlib.util,re,os
D=Path(__file__).resolve().parent

def need(v,m):
 if not v:raise AssertionError(m)
def unique_object(pairs):
 d={}
 for k,v in pairs:
  need(k not in d,"duplicate key");d[k]=v
 return d
def load(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and 0<s.st_size<=16777216,'bounded metadata input');return json.loads(p.read_bytes(),object_pairs_hook=unique_object)
def receipt(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=469762048,'bounded regular pin');b=p.read_bytes();s2=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(s2.st_dev,s2.st_ino,s2.st_size,s2.st_mtime_ns),'immutable bytes');return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def pin(p,r):need(receipt(p)=={k:r[k]for k in ['bytes','sha256']},'exact pin:'+str(p));return Path(p)
def save(p,v):
 
 if Path(p).name=='attempts.json':need(all(len(json.dumps(r).encode())<=65536 for r in v),'bounded per-case metadata before publication')
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


def consumer_proofs(root,rows,g):
 from prepare import c_proofs,pin as owned_pin
 from header import header
 cp=c_proofs(root,rows,g['C19Proofs']);ds=g['consumerProofs'];need(len(ds)==19 and len({d['path']for d in ds})==19,'19 distinct audited consumers');result={}
 for d in ds:
  q=load(pin(d['path'],d));need(q['status']=='PASS_INDEPENDENT_FRESH_CURRENT17_CONSUMER_BUILD_SOURCE_IDENTITY_ONLY','independent actual consumer artifact proof')
  w=q['workload'];row=next(r for r in rows if r['workload']==w);need(w not in result and q['symbol']==row['symbol'] and q['consumerABI']=='ARM_n_calls_warmup_5ARGV_V1','own symbol/consumer ABI')
  need(q['consumerBuildSourcePinsSHA256']=='514bbfffffb4718e3a175989001ece4e9da39ad3770c6424347ebe252f71a6ba','exact audited build SOURCE')
  need(q['compileArgv']==['/Library/Developer/CommandLineTools/usr/bin/clang','-std=c11','-O2','-DKEXE_OWNERSHIP_DIAGNOSTIC_V3','-I',str(root/'build'/w),str(root/'source/consumer/timing-loader.c'),'-o',str(root/'consumer-build-outputs'/w/'consumer'),'-lproc'],'unchanged actual consumer compile argv')
  a=q['artifact'];need(Path(a['path'])==root/'consumer-build-outputs'/w/'consumer','exact fresh consumer path');pin(a['path'],a)
  need(q['consumerSourcePinsSHA256']=='a0d2bed0535e7cf2e9fd6d277303ba99ff1664aff83466989a3c124626ff7699'and q['CProof']==next(x for x in g['C19Proofs']if load(x['path'])['workload']==w),'same C and frozenconsumer source')
  c=owned_pin(cp[w]['artifact']['path'],cp[w]['artifact']);h=header(row,owned_pin(row['OFF']['native']['path'],row['OFF']['native']),owned_pin(row['ON']['native']['path'],row['ON']['native']),c,cp[w])
  hp=root/'build'/w/'timing-packet-generated.h';need(q['generatedHeader']['path']==str(hp) and pin(hp,q['generatedHeader']).read_bytes()==h,'actual audited header reconstruction');need((root/'inputs'/w/'C.dylib').read_bytes()==c,'same complete C materialization');result[w]=a
 need(set(result)=={r['workload']for r in rows},'all19 actualconsumer coverage');return result

def runtime_registration(g,pr,root):
 from prepare import packet,qualification_cases
 rows=packet(root);artifacts=consumer_proofs(root,rows,g);q=dict(pr)
 q.update(qualificationSourcePinsSHA256=g['sourcePinsSHA256'],taskRoot=str(root),freshOutputRoot=str(root/pr['qualificationOutputsRelative']),interpreter=g['hostBinding']['interpreter'],cases=qualification_cases(root,rows,artifacts),environment=pr['environmentBase']|{'TMPDIR':str(root/pr['qualificationOutputsRelative'])},maximumLoaderCalls=342,rootGOStatus=pr['qualifyGOStatus'],invocationSealVersion='current17-consumer342-held-v6-invocation/v2')
 return q

def validate_scope(pr,ip):
 for k in ['qualificationChildCalls','freshQualificationCalls','repeatQualificationCalls','bodyInvocationsIncludingWarmup','qualificationCampaignSeconds','qualificationOutputReservationBytes','controlledFDLedgerMaximum','auxiliaryThreadsPerCall','maximumAuxiliaryThreadStarts','guestFuelPerCall']:need(type(pr[k])is int,'integer bounded scope')
 need(pr['captureStdoutMaximum']==8388608 and pr['captureStderrMaximum']==1048576 and pr['perCallMemoryJournalMaximum']==8388608 and pr['perCallOwnershipJournalMaximum']==65536 and pr['maximumSamplesPerCall']==2048 and pr['nativeWallSeconds']==30 and pr['nativeCPUSeconds']==30 and pr['nativeCPUHardSeconds']==31 and pr['cleanupSeconds']==30,'unchanged execution limits')
 need(pr['qualificationChildCalls']==342 and pr['freshQualificationCalls']==285 and pr['repeatQualificationCalls']==57 and pr['bodyInvocationsIncludingWarmup']==741,'fixed342/741 scope')
 need(pr['qualificationCampaignSeconds']==24000 and pr['qualificationOutputReservationBytes']==8589934592 and pr['controlledFDLedgerMaximum']==45 and pr['auxiliaryThreadsPerCall']==3 and pr['maximumAuxiliaryThreadStarts']==1026,'finite prospective host scope')
 need(len(ip)==108 and sum(x['bytes']for x in ip.values())==2931240,'exact source/native input closure')
 need(pr['guestFuelPerCall']==16777216 and pr['guestArenaCaps']=={'pairs':2097152,'string-pool-bytes':65536,'vectors':4096,'vector-items':65536} and pr['zeroCapabilityGrants']=='-' and pr['C2']is False and pr['noRetry']is True and pr['timingComparisonAuthorized']is False,'unchanged guest contracts; no comparison')
 return True

GO_KEYS={'status','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','taskRoot','hostBinding','maximumLoaderCalls','runtimeGuestAuthorized','timingAuthorized','noRetry','C2','C19Proofs','consumerProofs'}
def go_header(g,pr):
 need(set(g)==GO_KEYS and g['status']==pr['qualifyGOStatus'] and type(g['maximumLoaderCalls'])is int and g['maximumLoaderCalls']==342 and g['runtimeGuestAuthorized']is True and g['timingAuthorized']is False and g['noRetry']is True and g['C2']is False,'exact342 only GO')
 root=Path(g['taskRoot']);need(root.resolve()==root and D==root/'source/current17-qualification-v2','canonical installed qualifier')
 for name,key in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/name)['sha256']==g[key],'reviewed identities')
 need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two distinct SOURCE reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus'] and all(q[k]==g[k]for k in ['sourcePinsSHA256','preregistrationSHA256','driverSHA256']),'exact source review')
 pin(g['hostBinding']['interpreter']['path'],g['hostBinding']['interpreter']);return root

def main(goPath):
 import time,platform
 need(platform.system()=='Darwin'and platform.machine()=='arm64','actual host architecture')
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');validate_scope(pr,ip);root=go_header(g,pr);runtime=runtime_registration(g,pr,root);O=Path(runtime['freshOutputRoot']);rows=[];results=[];generated={};ok=False
 def guard():
  pin(gp,gr);validate_scope(pr,ip);go_header(g,pr)
  for n,r in sp.items():pin(D/n,r)
  for n,r in ip.items():pin(root/n,r)
  for n,r in generated.items():pin(n,r)
  need(runtime_registration(g,pr,root)==runtime,'immutable actualconsumer registration')
 guard();need(not O.exists(),'fresh noRetry namespace');O.mkdir();save(O/'runtime-preregistration.json',runtime);generated[str(O/'runtime-preregistration.json')]=receipt(O/'runtime-preregistration.json');save(O/'attempts.json',rows);save(O/'effective-environment.json',runtime['environment']);save(O/'generated-pins.json',generated)
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);deadline=time.monotonic()+24000
 try:
  for index,c in enumerate(runtime['cases'],1):
   guard();need(time.monotonic()+60<=deadline,'absolute remaining budget before child')
   seal={'format':runtime['invocationSealVersion'],'index':index,'case':c,'runtimeRegistration':dict(path=str(O/'runtime-preregistration.json'),**receipt(O/'runtime-preregistration.json')),'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256']};p=O/(c['label']+'.admission.json');save(p,seal);need(p.stat().st_size<=4096,'bounded invocation seal');p.chmod(0o444);sr=receipt(p);generated[str(p)]=sr;save(O/'generated-pins.json',generated)
   r=mod.call(D,O,runtime,c,rows,save,sr['sha256']);results.append(r);save(O/'results.json',results)
  guard();need(len(rows)==len(results)==342 and all(r['state']=='terminal' and r['returncode']==0 for r in rows),'342 actual normal closures');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'consumerCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'consumerCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();t=load(O/'terminal.json');need(ok and t['allChildrenClosed'] and not t['failure'],'valid-last closure')
 evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['runtime-preregistration.json','terminal.json','attempts.json','generated-pins.json','results.json','effective-environment.json']}
 save(O/'report.json',{'status':'COMPLETE_CURRENT17_CONSUMER342_V2_FUNCTIONAL_DIAGNOSTIC_ONLY','consumerCalls':342,'warmupAndBodyCalls':741,'results':results,'rootGO':dict(path=str(gp),**gr),'evidence':evidence,'independent342ClosureAdmission':'HOLD until external saved audit; driver never issues independent child proof','performanceQualified':False,'officialEmbenchQualified':False,'hardPeakQualified':False,'CfuelArenaAvailable':False,'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact GO');main(sys.argv[1])
