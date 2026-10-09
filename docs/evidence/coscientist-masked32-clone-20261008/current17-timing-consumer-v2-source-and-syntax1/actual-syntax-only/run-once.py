from pathlib import Path
import hashlib,json,subprocess,resource
D=Path(__file__).parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
p=load(D/'preregistration.json');assert p['maximumClangTopLevelCalls']==1 and p['guestCallsAuthorized']==0 and not p['objectOrExecutableOutputAuthorized'];assert not (D/'attempt.json').exists()
for r in p['origins']:
 assert rec(Path(r['path']))==r;assert (D/'copied-source'/Path(r['path']).name).read_bytes()==Path(r['path']).read_bytes()
assert rec(Path(p['syntheticHeader']['path']))==p['syntheticHeader']
(D/'attempt.json').write_text(json.dumps(dict(state='STARTED_ONCE_SYNTAX_ONLY',argv=p['argv'],guestCalls=0))+'\n')
def caps():resource.setrlimit(resource.RLIMIT_CPU,(30,31));resource.setrlimit(resource.RLIMIT_FSIZE,(16777216,16777216))
with (D/'stdout.raw').open('xb')as out,(D/'stderr.raw').open('xb')as err:
 q=subprocess.run(p['argv'],cwd=D,env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(D),'LANG':'C','LC_ALL':'C','TZ':'UTC'},stdout=out,stderr=err,preexec_fn=caps,timeout=30,start_new_session=True)
r=dict(status='PASS_LOCAL_C_SYNTAX_ONLY_SYNTHETIC_HEADER'if q.returncode==0 else'FAIL_LOCAL_C_SYNTAX_ONLY_SYNTHETIC_HEADER',returncode=q.returncode,closedTopLevelClangCalls=1,guestCalls=0,nativeProductCompilation=False,objectOrExecutableProduced=False,syntheticHeaderIsRuntimeProof=False,stdout=rec(D/'stdout.raw'),stderr=rec(D/'stderr.raw'),preregistration=rec(D/'preregistration.json'),performanceQualified=False,descendantClosureQualified=False)
(D/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));print((D/'stderr.raw').read_text()[:4000])
