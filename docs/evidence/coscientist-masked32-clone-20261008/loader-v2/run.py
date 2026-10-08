"""Source-bound diagnostic C loader build16 only. Import inert."""
from pathlib import Path
import json,hashlib,os,sys,subprocess,signal,struct
D=Path(__file__).resolve().parent;ROOT=D/'run-outputs';H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def receipt(p):p=Path(p);return {'bytes':p.stat().st_size,'sha256':H(p.read_bytes())}
def pin(p,v):
 p=Path(p);need(p.is_file()and not p.is_symlink()and p.stat().st_size==v['bytes'],'regular exact bounded size');need(receipt(p)==v,'regular exact pin');return p
class Ledger:
 def __init__(self,folder,cap):self.folder=folder;self.cap=cap;self.rows=[];folder.mkdir()
 def call(self,label,argv,env,timeout):
  need(len(self.rows)<self.cap and label not in [r['label'] for r in self.rows],'finite/no retry');r={'index':len(self.rows)+1,'label':label,'argv':argv,'environment':env.copy(),'timeoutSeconds':timeout,'state':'started'};self.rows.append(r);save(self.folder/'attempts.json',self.rows)
  p=None;o=e=b'';timed=False;error=None;cleanupError=None;rc=None
  try:
   p=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
   try:o,e=p.communicate(timeout=timeout)
   except subprocess.TimeoutExpired:
    timed=True
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    o,e=p.communicate(timeout=30)
   rc=p.returncode
  except BaseException as ex:
   error=ex
   if p is not None:
    try:
     try:os.killpg(p.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     o,e=p.communicate(timeout=30);rc=p.returncode
    except BaseException as cleanup:
     cleanupError=repr(cleanup)
     try:rc=p.wait(timeout=30)
     except BaseException as reap:cleanupError+=';reap='+repr(reap)
  # Every post-spawn error attempts group kill, raw drain and reap before STOP.
  # A spawn error has no child; failed cleanup remains explicitly unclosed.
  closed=p is None or p.returncode is not None
  (self.folder/(label+'.stdout')).write_bytes(o);(self.folder/(label+'.stderr')).write_bytes(e)
  r.update(state='terminal' if closed else 'unclosed',spawned=p is not None,returncode=rc,timeout=timed,exception=None if error is None else repr(error),cleanupException=cleanupError,stdoutSHA256=H(o),stderrSHA256=H(e));save(self.folder/'attempts.json',self.rows)
  if error is not None:raise error
  need(closed and cleanupError is None and not timed and rc==0 and e==b'','first process failure/diagnostic STOP');return o

def main():
 need(len(sys.argv)==2,'rootGO');gp=Path(sys.argv[1]);gb=gp.read_bytes();g=json.loads(gb);pr=load(D/'preregistration.json');sph=H((D/'source-pins.json').read_bytes());sp=load(D/'source-pins.json');deps={}
 need(g['status']=='ROOT_GO_SOURCE_BOUND_DIAGNOSTIC_C_LOADER16_ONLY' and g['sourcePinsSHA256']==sph and g['maximumChildCalls']==16 and g['guestAuthorized'] is False and g['noRetry'] is True and g['outerExecution']=='require_escalated','finiteCbootstrapGO')
 need(len(g['sourceReviews'])==2 and len({e['path']for e in g['sourceReviews']})==2,'two independentreviews')
 for e in g['sourceReviews']:
  q=load(pin(e['path'],{'bytes':e['bytes'],'sha256':e['sha256']}));need(q['status']=='PASS_SOURCE_ONLY_MASKED32_SOURCE_BOUND_DIAGNOSTIC_LOADER16'and q['sourcePinsSHA256']==sph,'specificreviews')
 def guard():
  need(gp.read_bytes()==gb and H((D/'source-pins.json').read_bytes())==sph,'GOregistryimmutable')
  for n,v in sp.items():pin(D/n,v)
  for p,v in pr['inputs'].items():pin(p,v)
  for p,v in deps.items():pin(p,v)
  for e in g['sourceReviews']:pin(e['path'],{'bytes':e['bytes'],'sha256':e['sha256']})
 guard();need(not ROOT.exists(),'freshoutput');ROOT.mkdir();folder=ROOT/'ledger';ledger=Ledger(folder,16);ok=False
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(Path.home()),'TMPDIR':str(ROOT),'LANG':'C','LC_ALL':'C','TZ':'UTC','DEVELOPER_DIR':'/Library/Developer/CommandLineTools'}
 def call(label,argv,t):guard();raw=ledger.call(label,argv,env,t);guard();return raw
 def identity(when):
  def q(k,a):return call(when+'-'+k,a,30).decode().strip()
  compiler=Path(q('clang',['/usr/bin/xcrun','--find','clang'])).resolve(strict=True);sdk=Path(q('sdk',['/usr/bin/xcrun','--sdk','macosx','--show-sdk-path'])).resolve(strict=True);sdkv=q('sdkversion',['/usr/bin/xcrun','--sdk','macosx','--show-sdk-version']);version=q('version',[str(compiler),'--version']);target=q('target',[str(compiler),'-dumpmachine']);osv=q('OS',['/usr/bin/sw_vers','-productVersion']);osb=q('OSbuild',['/usr/bin/sw_vers','-buildVersion'])
  return {'compiler':str(compiler),'compilerSHA256':receipt(compiler)['sha256'],'usrBinClangSHA256':receipt('/usr/bin/clang')['sha256'],'SDK':str(sdk),'SDKSettings':{str(p):receipt(p)['sha256'] for p in sorted(sdk.glob('SDKSettings.*'))if p.is_file()and not p.is_symlink()},'SDKVersion':sdkv,'version':version,'target':target,'OS':osv,'OSBuild':osb}
 try:
  before=identity('before');need(before==pr['expectedToolchainIdentity'],'exactcurrenttoolchain');save(ROOT/'identity-before.json',before)
  src=D/'kexe_loader.c';argv=[before['compiler'],*pr['compileFlags']];raw=call('dependencies',argv+['-M',str(src)],60);need(len(raw)<=1048576,'bounddepstdout');deptext=raw.decode().replace(chr(92)+chr(10),' ');need(':'in deptext,'make dependencyrecord');paths=deptext.split(':',1)[1].split();need(0<len(paths)<=4096 and len(set(paths))==len(paths),'finiteuniquedependencyset')
  dependencyBytes=0
  for name in paths:
   p=Path(name);need(p.is_absolute(),'absolutedeps');p=p.resolve(strict=True);need(p==src.resolve()or p.is_relative_to(Path(before['SDK']))or p.is_relative_to(Path('/Library/Developer/CommandLineTools/usr/lib/clang')),'registeredsystemCdependencydomain');need(p.is_file()and not p.is_symlink(),'regular resolved dependency');size=p.stat().st_size;need(0<=size<=67108864 and size<=67108864-dependencyBytes,'dependency bound BEFORE read');dependencyBytes+=size;deps[str(p)]=receipt(p);need(deps[str(p)]['bytes']==size,'dependency size stable after read');pin(p,deps[str(p)])
  need(sum(v['bytes']for v in deps.values())<=67108864,'64MiBheaders');save(ROOT/'dependency-input-pins.json',deps);guard();loader=ROOT/'kexe-loader';call('build-loader',argv+[str(src),'-o',str(loader)],180);b=loader.read_bytes();need(32<=len(b)<=4194304 and b[:4]==b'\xcf\xfa\xed\xfe'and struct.unpack_from('<I',b,4)[0]==0x100000c and struct.unpack_from('<I',b,12)[0]==2,'arm64executable');captured=receipt(loader);save(ROOT/'loader.json',{'path':str(loader),**captured});after=identity('after');save(ROOT/'identity-after.json',after);need(after==before and receipt(loader)==captured and len(ledger.rows)==16,'all16stable');guard()
  save(ROOT/'report.json',{'status':'COMPLETE_SOURCE_BOUND_DIAGNOSTIC_LOADER16_BUILD_IDENTITY_ONLY','childCalls':16,'identityQueries':14,'clangInvocations':6,'dependencyCalls':1,'buildCalls':1,'sourceSHA256':receipt(src)['sha256'],'dependencyPinsSHA256':H((ROOT/'dependency-input-pins.json').read_bytes()),'loader':{'path':str(loader),**captured},'guestCalls':0,'SDKWholeTreeQualified':False,'functionalQualified':False,'performanceQualified':False});ok=True
 except BaseException as e:save(ROOT/'failure.json',{'exception':repr(e),'childCalls':len(ledger.rows),'noRetry':True});raise
 finally:save(ROOT/'terminal.json',{'childCalls':len(ledger.rows),'allChildrenClosed':all(r['state']=='terminal'for r in ledger.rows),'failure':not ok})
if __name__=='__main__':main()
