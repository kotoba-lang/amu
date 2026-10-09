from pathlib import Path
import json,hashlib,subprocess,sys,os
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-hft-current17-timing-consumer-source-v2-20261009-crc';O=Path(__file__).parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def guard():
 sp=load(D/'source-pins.json');ip=load(D/'input-pins.json')
 for n,r in sp.items():assert rec(D/n)=={k:r[k]for k in ['bytes','sha256']},n
 for n,r in ip.items():assert rec(Path(n))=={k:r[k]for k in ['bytes','sha256']},n
 return sp,ip
sp,ip=guard();C=O/'copied-source';C.mkdir()
for n in sp:(C/n).write_bytes((D/n).read_bytes())
q=subprocess.run([sys.executable,str(C/'source-controls.py')],cwd=C,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=30);(O/'controls.stdout').write_bytes(q.stdout);(O/'controls.stderr').write_bytes(q.stderr);assert q.returncode==0,q.stderr;controls=json.loads(q.stdout);assert controls==load(D/'source-controls.json');assert controls['nativeRawPositives']==190
p=load(D/'preregistration.json');assert p['measurement']['resetIncluded']is False and p['functionalQualification']['maximumConsumerChildren']==342
extension=(D/'timing-extension.h').read_text();loop=extension[extension.index('static int64_t timing_loop'):extension.index('static void timing_parent_report')];assert loop.index('timing_reset(s);')<loop.index('begin=timing_now();')<loop.index('result=fn(')<loop.index('end=timing_now();')<loop.index('timing_snapshot(s,last);')
for n in ['timing-loader.c','timing-extension.h','timing-frontend.h']:
 assert (D/n).read_bytes()==(W/'current17-consumer-syntax1-root-20261009/copied-source'/n).read_bytes()
assert load(W/'current17-consumer-syntax1-root-20261009/report.json')['status']=='PASS_LOCAL_C_SYNTAX_ONLY_SYNTHETIC_HEADER'
assert guard()==(sp,ip)
r=dict(status=p['sourceReviewStatus'],sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],inputPinsSHA256=rec(D/'input-pins.json')['sha256'],preregistrationSHA256=rec(D/'preregistration.json')['sha256'],verifiedSourceFiles=len(sp),verifiedInputFiles=len(ip),verifiedInputBytes=sum(r['bytes']for r in ip.values()),controls=controls,CBytesEqualToSyntaxOnlyDiagnostic=True,resetOutsideElapsed=True,nativeOperationsByReview=0,limitations=['SOURCE only, full342 remains unexecuted','Synthetic header syntax is not freshC or runtime proof','Fresh Cbuild then independent audit then headers then consumers','Held execution adapter and additional dlopen/FD inventory still unqualified','No performance, official score, persistentCID cache or adoption claim'])
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],report=rec(O/'report.json'),inputs=len(ip))))
