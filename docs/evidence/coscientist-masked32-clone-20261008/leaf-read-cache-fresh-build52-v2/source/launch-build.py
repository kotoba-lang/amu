"""One bounded SSH build launch outside52; author never executes this file."""
from common import *
import sys,copy,base64,shlex
def main():
 need(len(sys.argv)==2,'buildGO');gp=Path(sys.argv[1]);g=authorize('build',gp);gh=sha(gp)
 need(g.get('maximumChildren')==52 and g.get('CBuilds')==19 and g.get('consumerBuilds')==19 and g.get('identityQueries')==14 and g.get('maximumLaunchTransportChildren')==1,'finite build and launch caps')
 tr=pin(g['transferAcceptance'],1048576);ta=load(tr);need(str(ta.get('status','')).startswith('PASS') and ta.get('archiveSHA256')==g['archiveSHA256'],'transfer accepted samearchive')
 O=D/'build-launch-outputs';need(not O.exists(),'freshlaunch no retry');O.mkdir();remote=copy.deepcopy(g);files={}
 for i,r in enumerate(g['sourceReviews']):
  name='review'+str(i)+'.json';b=pin(r,1048576).read_bytes();files[name]=base64.b64encode(b).decode();remote['sourceReviews'][i]=dict(path=str(ROOT/'control'/name),bytes=len(b),sha256=H(b))
 b=tr.read_bytes();files['transfer-acceptance.json']=base64.b64encode(b).decode();remote['transferAcceptance']=dict(path=str(ROOT/'control/transfer-acceptance.json'),bytes=len(b),sha256=H(b));remote['originalLocalGOSHA256']=sha(gp)
 rb=json.dumps(remote,indent=2).encode()+b'\n';files['build-go.json']=base64.b64encode(rb).decode();save(O/'derived-remote-go.json',remote)
 req=dict(files=files,remoteGOSHA256=H(rb),sourcePinsSHA256=g['sourcePinsSHA256']);payload=json.dumps(req,separators=(',',':')).encode();need(len(payload)<=4194304,'launchpayload4MiB')
 encoded=base64.b64encode(payload).decode()
 wrapper="""import os,pathlib,sys,json,hashlib,base64,signal,runpy
signal.alarm(7920)
root=pathlib.Path(%r)
assert pathlib.Path.home()==pathlib.Path('/Users/zebulun') and root.is_dir() and not root.is_symlink()
req=json.loads(base64.b64decode(%r))
assert hashlib.sha256((root/'package/source-pins.json').read_bytes()).hexdigest()==req['sourcePinsSHA256']
bank=json.loads((root/'package/source-pins.json').read_text())
for n,r in bank.items():
 p=root/'package'/n
 assert p.is_file() and not p.is_symlink() and p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
c=root/'control';assert not c.exists();c.mkdir()
for n,t in req['files'].items():
 assert n in ['review0.json','review1.json','transfer-acceptance.json','build-go.json']
 p=c/n;b=base64.b64decode(t)
 with p.open('xb') as f:f.write(b)
 p.chmod(0o444)
assert hashlib.sha256((c/'build-go.json').read_bytes()).hexdigest()==req['remoteGOSHA256']
sys.dont_write_bytecode=True
sys.path.insert(0,str(root/'package'))
sys.argv=[str(root/'package/build52.py'),str(c/'build-go.json')]
runpy.run_path(sys.argv[0],run_name='__main__')
print('LC_BUILD52_REMOTE_TERMINAL',flush=True)
"""%(str(ROOT),encoded)
 need(len(wrapper.encode())<=131072,'bounded SSH command131072 bytes; no OS argv overflow fallback')
 env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/junkawasaki',TMPDIR='/private/tmp')
 led=Ledger(O/'children',1,env);argv=['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',HOST,'python3 -c '+shlex.quote(wrapper)]
 try:
  need(sha(gp)==gh,'buildGO stable prelaunch');authorize('build',gp)
  out,err,_=led.call('build-launch',argv,7980);need(not err and out.strip()==b'LC_BUILD52_REMOTE_TERMINAL','explicit closed buildlaunch seal')
  need(sha(gp)==gh,'buildGO stable postlaunch');authorize('build',gp)
  save(O/'report.json',dict(status='PASS_BUILD52_LAUNCH_CLOSED_ONLY_ACTUAL_BUILD_AUDIT_PENDING',launchChildren=1,innerExpectedChildren=52,remoteGOSHA256=H(rb),sourcePinsSHA256=g['sourcePinsSHA256'],archiveSHA256=g['archiveSHA256'],actualBuildAcceptance=False))
 except BaseException as ex:save(O/'failure.json',dict(exception=repr(ex),noRetry=True,remoteClosureOnTransportFailure='UNKNOWN; remote alarm7920'));raise
 finally:save(O/'terminal.json',dict(**led.terminal(),failure=(O/'failure.json').exists()))
if __name__=='__main__':main()
