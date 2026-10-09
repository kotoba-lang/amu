from pathlib import Path
import json,hashlib,subprocess,os,sys
W=Path('/Users/junkawasaki/github/workspaces/codex'); D=W/'tc-hft-g4-held-v6-original19-runtime190-source-v1-20261009-dense'; O=Path(__file__).parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def verify():
 sp=load(D/'source-pins.json');ip=load(D/'input-pins.json')
 for n,r in sp.items():assert rec(D/n)==r,n
 for n,r in ip.items():assert rec(Path(n))=={k:r[k] for k in ('bytes','sha256')},n
 return sp,ip
sp,ip=verify();pr=load(D/'preregistration.json')
q=subprocess.run([sys.executable,str(D/'pure-controls.py')],cwd=D,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=60)
(O/'pure.stdout').write_bytes(q.stdout);(O/'pure.stderr').write_bytes(q.stderr);assert q.returncode==0,q.stderr.decode()
pure=json.loads(q.stdout);assert pure['positiveRuntimeGrammarCases']==190 and len(pure['refusals'])==29 and pure['nativeCalls']==pure['actualFDThreadProcessCalls']==0
assert verify()==(sp,ip)
report=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],inputPinsSHA256=rec(D/'input-pins.json')['sha256'],driverSHA256=rec(D/'run.py')['sha256'],preregistrationSHA256=rec(D/'preregistration.json')['sha256'],verifiedSourceFiles=len(sp),verifiedInputFiles=len(ip),verifiedInputBytes=sum(x['bytes'] for x in ip.values()),pure=pure,nativeOperations=0,author=False,limitations=['SOURCE only; no runtime190 credit','C oracle Boolean result only; no C fuel or arena','Held fixture limited lifecycle checks; no universal race or syscall proof','4GiB accounting reservation not enforced filesystem quota','No timing, native shared CID cache or general candidate adoption qualification'])
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(report=rec(O/'report.json'),status=report['status'],inputs=len(ip),refusals=len(pure['refusals']))))
