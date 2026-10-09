"""Exactly3transport children, pinned archive/extractor; no compiler/native."""
from common import *
import shlex,sys
def main():
 need(len(sys.argv)==2,'transfer GO');gp=Path(sys.argv[1]);g=authorize('transfer',gp);gh=sha(gp)
 need(g.get('maximumChildren')==3 and g.get('extractorSHA256')==sha(D/'extract.py'),'exact3/pinned extractor')
 a=pin(g['archive'],268435456);mi=pin(g['manifest'],16777216)
 need(a.name=='package.tgz' and g['manifestBytesSHA256']==sha(mi),'exact archive/manifest')
 ar=load(pin(g['assemblyAcceptance'],1048576));need(str(ar.get('status','')).startswith('PASS') and ar.get('archiveSHA256')==g['archive']['sha256'],'independent actual archive acceptance')
 O=D/'transfer-outputs';need(not O.exists(),'fresh transfer no retry');O.mkdir()
 # SCP carries a typed extractor and concrete GO only; source-only evidence is inside archive.
 (O/'transfer-go.json').write_bytes(gp.read_bytes())
 env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/junkawasaki',TMPDIR='/private/tmp')
 led=Ledger(O/'children',3,env);opts=['-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1']
 init="from pathlib import Path;import os;p=Path("+repr(str(STAGE))+");r=Path("+repr(str(ROOT))+");assert Path.home()==Path('/Users/zebulun');assert not p.exists() and not r.exists();assert all(not q.is_symlink() for q in p.parents if q.exists());p.mkdir();print('FRESH_STAGE_ONLY',flush=True)"
 wrap="import pathlib,hashlib,sys,signal;signal.alarm(250);p=pathlib.Path("+repr(str(STAGE/'extract.py'))+");assert hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(g['extractorSHA256'])+";gp=pathlib.Path("+repr(str(STAGE/'transfer-go.json'))+");assert hashlib.sha256(gp.read_bytes()).hexdigest()=="+repr(gh)+";sys.argv=[str(p),str(gp)];exec(compile(p.read_bytes(),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})"
 cmds=[['/usr/bin/ssh',*opts,HOST,'python3 -c '+shlex.quote(init)],['/usr/bin/scp',*opts,str(a),str(D/'extract.py'),str(O/'transfer-go.json'),HOST+':'+str(STAGE)+'/'],['/usr/bin/ssh',*opts,HOST,'python3 -c '+shlex.quote(wrap)]]
 def guard():
  need(sha(gp)==gh and sha(O/'transfer-go.json')==gh,'transferGO original/typedcopy immutable');authorize('transfer',gp);pin(g['archive'],268435456);pin(g['manifest'],16777216);pin(g['assemblyAcceptance'],1048576)
 try:
  for i,argv in enumerate(cmds):
   guard();out,err,_=led.call(str(i+1),argv,[30,300,300][i]);guard();need(not err,'transportstderr')
   if i==2:
    seal=json.loads(out.decode().strip());need(seal.get('status')=='PASS_REMOTE_EXTRACT_ONLY' and seal.get('archiveSHA256')==g['archive']['sha256'] and seal.get('manifestSHA256')==g['manifestBytesSHA256'] and seal.get('sourcePinsSHA256')==g['sourcePinsSHA256'] and seal.get('rootFunctional285AcceptanceSHA256')==g['rootFunctional285AcceptanceSHA256'],'explicit remote extraction terminal receipt')
    save(O/'remote-extract-terminal.json',seal)
  save(O/'report.json',dict(status='PASS_TRANSFER_AND_EXTRACT_ONLY',children=3,archiveSHA256=g['archive']['sha256'],manifestSHA256=g['manifestBytesSHA256'],sourcePinsSHA256=g['sourcePinsSHA256'],compilerCalls=0,nativeCalls=0))
 except BaseException as ex:save(O/'failure.json',dict(exception=repr(ex),noRetry=True,remoteClosureOnTransportFailure='UNKNOWN; extractor selfalarm240 and wrapper250'));raise
 finally:save(O/'terminal.json',dict(**led.terminal(),failure=(O/'failure.json').exists()))
if __name__=='__main__':main()
