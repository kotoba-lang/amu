"""Finite SOURCE-only17 protocol. Inert import; two reviewed sources+rootGO required."""
from pathlib import Path
import os,json,sys,hashlib,subprocess,signal,time,stat,re
from validate import validate
D=Path(__file__).resolve().parent;O=D/'run-outputs';H=lambda b:hashlib.sha256(b).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def load(p):return json.loads(Path(p).read_bytes())
def pin(p,v):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size==v['bytes'];assert H(p.read_bytes())==v['sha256'];return p

def kseed(b):
 assert len(b)<=4194560;h,p=b.split(b'\n\n',1);ls=h.decode('ascii').splitlines();assert ls==['KSEED1 '+str(len(p))+' 1','main 0 0']and 0<len(p)<=4194304;return p

def main():
 assert len(sys.argv)==2;gp=Path(sys.argv[1]);gb=gp.read_bytes();g=json.loads(gb);sp=load(D/'source-pins.json');pr=load(D/'preregistration.json');ip=load(D/'input-pins.json')
 assert g['status']=='ROOT_GO_COMPUTE_SEMANTIC_SHADOW17_ONLY'and g['sourcePinsSHA256']==H((D/'source-pins.json').read_bytes())and type(g['maximumLoaderCalls'])is int and g['maximumLoaderCalls']==17 and g['noRetry']is True and g['nativeAuthorized']is True and g['outerExecution']=='require_escalated'and g['timingAuthorized']is False and g['persistentReuseAuthorized']is False and g['keyExclusionsApproved']==[]
 assert len(g['sourceReviews'])==2 and len({e['path']for e in g['sourceReviews']})==2
 producer=g['producer'];loader=g['loader'];assert producer['sha256']=='76e9f9825f1b1e38b2749575cbb4e80a21ad27abb906b97f9f048e7cd631c207'and loader['sha256']=='8fc787ca556773b6991b44f51e0d4fdec52cf93ef37673cb289eb726c98dff64'
 assert len(ip)<=8192 and sum(v['bytes']for v in ip.values())<=402653184
 extra={};rows=[];results=[];ok=False
 def guard():
  assert gp.read_bytes()==gb and H((D/'source-pins.json').read_bytes())==g['sourcePinsSHA256']
  for n,v in sp.items():pin(D/n,v)
  for p,v in {**ip,**extra}.items():pin(p,v)
  pin(producer['path'],producer);pin(loader['path'],loader)
  for e in g['sourceReviews']:
   q=load(pin(e['path'],e));assert q['status']=='PASS_SOURCE_ONLY_COMPUTE_SEMANTIC_SHADOW17'and q['sourcePinsSHA256']==g['sourcePinsSHA256']
 guard();assert not O.exists();O.mkdir()
 def capture(p):extra[str(p)]={'bytes':p.stat().st_size,'sha256':H(p.read_bytes())}
 def call(label,image,wires,args):
  guard();assert len(rows)<17;argv=[loader['path'],str(image),'0','0','aarch64',wires,'--',*args]
  env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(Path.home()),'TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800'}
  row={'index':len(rows)+1,'label':label,'argv':argv,'effectiveEnvironment':env,'state':'started','timeoutSeconds':1810};rows.append(row);save(O/'attempts.json',rows);p=None;failure=cleanup=None;out=O/(label+'.stdout');err=O/(label+'.stderr')
  with out.open('xb')as of,err.open('xb')as ef:
   try:
    p=subprocess.Popen(argv,cwd=O,env=env,stdout=of,stderr=ef,start_new_session=True);deadline=time.monotonic()+1810
    while p.poll()is None:
     assert time.monotonic()<deadline and out.stat().st_size<=1048576 and err.stat().st_size<=1048576;time.sleep(.05)
    p.wait(timeout=30)
   except BaseException as ex:
    failure=repr(ex)
    if p is not None:
     try:
      try:os.killpg(p.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      p.wait(timeout=30)
     except BaseException as ce:cleanup=repr(ce)
  closed=p is None or p.returncode is not None;capture(out);capture(err);row.update(state='terminal'if closed else'unclosed',spawned=p is not None,returncode=None if p is None else p.returncode,failure=failure,cleanupException=cleanup,stdout={'path':str(out),**extra[str(out)]},stderr={'path':str(err),**extra[str(err)]});save(O/'attempts.json',rows)
  assert closed and p is not None and failure is None and cleanup is None and p.returncode==0 and err.stat().st_size==0 and out.stat().st_size<=1048576;guard();return out.read_bytes()
 try:
  src=O/'shadow.kotoba';src.write_bytes((D/'unity-shadow.kotoba').read_bytes());src.chmod(0o444);capture(src);k=O/'shadow.kseed';b=O/'shadow.bin'
  raw=call('compile',producer['path'],'35,37,38,39',['compile',str(src),'--target','aarch64-macos','--output',str(k)]);assert b':ok true'in raw and k.stat().st_size<=4194560;capture(k);payload=kseed(k.read_bytes());guard()
  raw=call('extract',producer['path'],'35,37,38,39',['extract-native',str(k),'--symbol','main','--output',str(b)]);assert b.read_bytes()==payload and re.findall(rb':offset ([0-9]+)\b',raw)==[b'0'];capture(b);guard()
  for c in range(3):
   for family in range(5):
    raw=call('case-'+str(5*c+family),b,'3,37,38,39',['c1b',str(c),str(family)]);v=validate(raw,c,family);results.append(v);save(O/'comparisons.json',results);guard()
  assert len(rows)==17 and len(results)==15;ok=True
 except BaseException as ex:save(O/'failure.json',{'exception':repr(ex),'calls':len(rows),'completedCases':len(results),'noRetry':True});raise
 finally:
  save(O/'report.json',{'status':'COMPLETE_FINITE_SAME_TARGET_FIVE_FAMILY_SHADOW_ONLY'if ok else'FAIL_FINITE_SEMANTIC_SHADOW17','childCalls':len(rows),'cases':results,'directComputationsOmitted':0,'keyExclusionsApproved':[],'persistentReuse':False,'timingQualified':False,'fullOriginal19Qualified':False});save(O/'terminal.json',{'childCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok,'noRetry':True})
if __name__=='__main__':main()
