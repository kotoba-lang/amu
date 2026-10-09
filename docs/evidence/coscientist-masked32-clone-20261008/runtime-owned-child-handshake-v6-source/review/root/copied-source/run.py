"""Diagnostic-only fresh paired2; native entry only after exact SOURCE and actual loader/fixture proofs."""
from pathlib import Path
import json,hashlib,stat,os,re,importlib.util,time
D=Path(__file__).resolve().parent
def need(v,m):
 if not v:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def receipt(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=33554432,'bounded regular');b=p.read_bytes();need(s==p.lstat(),'stable pin');return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def pin(p,r):need(receipt(p)=={k:r[k]for k in ['bytes','sha256']},'exact pin');return Path(p)
def save(p,v):
 b=(json.dumps(v,indent=2)+'\n').encode();need(len(b)<=16777216,'bounded metadata');q=Path(str(p)+'.pending')
 with q.open('xb',buffering=0)as f:
  view=memoryview(b)
  while view:n=f.write(view);need(type(n)is int and 0<n<=len(view),'complete write');view=view[n:]
  os.fsync(f.fileno())
 os.replace(q,p);fd=os.open(str(Path(p).parent),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def container(raw):
 m=re.match(rb'KSEED1 ([1-9][0-9]{0,9}) ([1-9][0-9]{0,2})\n',raw);need(m is not None,'header');cut=raw.find(b'\n\n',m.end());need(cut>=m.end(),'split');lines=raw[m.end():cut].splitlines();need(len(lines)==int(m[2])<=128,'exports');e=[]
 for line in lines:
  q=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]{1,10}) ([0-9]{1,2})',line);need(q is not None,'export');e.append((q[1].decode(),int(q[2]),int(q[3])))
 b=raw[cut+2:];need(len(b)==int(m[1])<=4194304 and len({x[0]for x in e})==len(e)and all(x[1]%4==0 and x[1]+4<=len(b)and x[2]<=32 for x in e),'whole payload');return b,e
def diagnostic_loader(g,pr):
 proof=load(pin(g['diagnosticLoaderBuildProof']['path'],g['diagnosticLoaderBuildProof']));a=g['diagnosticLoaderArtifact'];pin(a['path'],a)
 need(proof['status']=='PASS_INDEPENDENT_ACTUAL_DIAGNOSTIC_HELD_OWNERSHIP_LOADER_V6_BUILD_IDENTITY_ONLY'and proof['artifact']==a and a['path']==pr['loader'],'fresh diagnostic loader')
 need(proof['copiedCSource']==dict(path=str(D/'kexe_loader_diagnostic.c'),**receipt(D/'kexe_loader_diagnostic.c'))and proof['originalCSource']==pr['originalLoaderCSource'],'exact copied primarysource')
 need(proof['compileArgv']==pr['prospectiveLoaderBuildArgv']and proof['compileFlag']=='KEXE_OWNERSHIP_DIAGNOSTIC_V3'and proof['closedBuildCalls']==1 and proof['noRetry']is True,'exact fresh build identity')
 return True
def main(goPath):
 pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');gp=Path(goPath);g=load(gp);gr=receipt(gp);O=Path(pr['freshOutputRoot']);rows=[];results=[];ok=False
 expected={'status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','diagnosticLoaderArtifact','diagnosticLoaderBuildProof','ownershipIntegrationFixtureProof'}
 need(set(g)==expected and g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==2 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is True and g['C2']is False and g['outerHostLaunchRequiresEscalation']is True,'exact new paired2 GO')
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'GO pin')
 need(len(g['sourceReviews'])==2 and len({q['path']for q in g['sourceReviews']})==2,'two SOURCEreviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'exact source review')
 fixture=load(pin(g['ownershipIntegrationFixtureProof']['path'],g['ownershipIntegrationFixtureProof']));need(fixture['status']=='PASS_INDEPENDENT_ACTUAL_DIAGNOSTIC_HELD_LAUNCH_CHANNEL_FD_AND_OWNERSHIP_V6_ONLY'and fixture['sourcePinsSHA256']==g['sourcePinsSHA256'],'new actual FD ownership qualification')
 def guard():
  need(receipt(gp)==gr,'immutable GO')
  for n,r in sp.items():pin(D/n,r)
  need(len(ip)<=256 and sum(r['bytes']for r in ip.values())<=33554432,'finite source closure')
  for n,r in ip.items():pin(n,r)
  diagnostic_loader(g,pr)
  for c in pr['cases']:
   b,e=container(pin(c['container']['path'],c['container']).read_bytes());need(b==pin(c['native']['path'],c['native']).read_bytes()and(c['symbol'],c['offset'],1)in e,'full own ABI');pin(c['source']['path'],c['source'])
 guard();need(not O.exists(),'fresh namespace no retry');O.mkdir();save(O/'attempts.json',rows);save(O/'results.json',results)
 spec=importlib.util.spec_from_file_location('bounded_call',D/'native-call.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);campaign=time.monotonic()+pr['maximumCampaignSeconds']
 try:
  for i,c in enumerate(pr['cases']):
   guard();need(time.monotonic()+60<=campaign,'bounded campaign before new child');need(i==len(rows)<2,'fixed order before API');seal={k:c[k]for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};seal.update(format=pr['invocationSealVersion'],index=i+1,rootGO=dict(path=str(gp),**gr),sourcePinsSHA256=g['sourcePinsSHA256'],preregistrationSHA256=g['preregistrationSHA256']);p=O/(c['label']+'.admission.json');save(p,seal);p.chmod(0o444)
   r=m.call(D,O,pr,c,rows,save,receipt(p)['sha256']);results.append(r);save(O/'results.json',results)
  need(results[0]['report']==results[1]['report'],'raw fuel/all17 OFFON parity');guard();need(len(rows)==len(results)==2,'exact2');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'calls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'calls':len(rows),'closed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();need(ok and load(O/'terminal.json')['closed'],'valid-last');save(O/'report.json',{'status':'COMPLETE_DIAGNOSTIC_HELD_OWNERSHIP_PAIRED2_ONLY','calls':2,'results':results,'rootGO':dict(path=str(gp),**gr),'full19Qualified':False,'performanceQualified':False,'hardPeakQualified':False,'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one fixed GO');main(sys.argv[1])
