"""Stdlib offline evidence replay only. Never executes retained native/compiler/solver/timing tools."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,re,sys
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ld=lambda p:json.loads(p.read_text())
assert sha(D/'directreg-negative-manifest.json')=='9a4ffac74182c4730996fab0d55a2ccd19b474ed0f4be187586295047984adbc'
m=ld(D/'directreg-negative-manifest.json');archive=D/m['archive']
assert archive.stat().st_size==m['archiveBytes'] and sha(archive)==m['archiveSHA256']
rows={r['member']:r for r in m['members']};assert len(rows)==m['memberCount']
W=Path(tempfile.mkdtemp(prefix='directreg-negative-offline-'))
with tarfile.open(archive,'r:gz')as tf:
 ms=tf.getmembers();assert len(ms)==len(rows) and {q.name for q in ms}==set(rows)
 for q in ms:
  p=PurePosixPath(q.name);assert q.isfile() and not p.is_absolute() and '..' not in p.parts
  data=tf.extractfile(q).read();r=rows[q.name];assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256']
  out=W/q.name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
E=W/'team-directreg-aes-remote-prep-v2/package';B=W/'root/directreg-aes-built-v2/built';S=W/'root/directreg-aes-semantic3-v2/semantic';Q=W/'root/directreg-aes-driver-v2/driver'
for base in [E,B,S,Q]:
 pin=base/('package-input-pins.json'if base in [E,Q]else'pins.json')
 for n,h in ld(pin).items():assert sha(base/n)==h
header=(E/'nettle-aes/immutable-header.h').read_text()
def arr(name):
 x=re.search(r'\b'+name+r'\[\]\s*=\s*\{([^}]*)\}',header,re.S);assert x
 return [int(v.strip()) for v in x.group(1).split(',')if v.strip()]
for name,file in [('known_baseline','baseline.bin'),('known_candidate','candidate.bin'),('timing_known_c_bytes','c.dylib')]:assert bytes(arr(name))==(E/'nettle-aes'/file).read_bytes()
assert arr('timing_known_sizes')==[40232,40120] and arr('timing_known_offsets')==[12800,12688]
assert '#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES 6ULL' in header and '#define KEXE_EMBEDDED_ISA "aarch64"'in header
built=ld(B/'report.json');entry=ld(E/'manifest.json')['entries'][0];assert built['status']=='PASS1build only'and built['builds']==1 and built['guestCalls']==0
assert built['entries']==[dict(entry,runnerSHA256=sha(B/'nettle-aes/runner'))]
attempt=ld(B/'attempts.json');assert len(attempt)==1 and attempt[0]['returncode']==0 and attempt[0]['runnerSHA256']==sha(B/'nettle-aes/runner')
assert attempt[0]['headerSHA256']==sha(E/'nettle-aes/immutable-header.h') and attempt[0]['hostSourceSHA256']==sha(E/'timing-host.c')
remote=ld(E/'preregistration.json')['remotePackage']
assert attempt[0]['argv']==['clang','-O2','-std=c11','-include',remote+'/nettle-aes/immutable-header.h',remote+'/timing-host.c','-o',remote+'/built/nettle-aes/runner']
feature=ld(S/'feature.json')
for k,v in [('arch','arm64'),('AES','1'),('CRC32','1'),('model','Mac16,10'),('host','zebulunnoMac-mini.local')]:assert feature[k]=={'exit':0,'stdout':v+'\n','stderr':''}
sem=ld(S/'report.json');assert sem['status']=='PASS3semantic only'and sem['calls']==3 and not sem['performanceAuthorized']
sa=ld(S/'attempts.json');assert len(sa)==3
for arm,kind,file,offset in [('baseline','raw','baseline.bin','12800'),('candidate','raw','candidate.bin','12688'),('C','dylib','c.dylib','batch')]:
 p=S/('nettle-aes-'+arm+'.json');raw=ld(p);row=next(x for x in sa if x['arm']==arm);assert row['receiptSHA256']==sha(p) and row['state']=='terminal' and raw['exit']==0 and raw['stderr']==''
 assert raw['argv']==[remote+'/built/nettle-aes/runner',kind,remote+'/nettle-aes/'+file,offset,'aarch64','32','1','0','16777216']
 o=json.loads(raw['stdout']);cons=0 if arm=='C'else 427363
 assert o['result']==1 and o['calls']==1 and o['warmupCalls']==0 and o['contextFuelBefore']==16777216 and o['contextFuelConsumed']==cons and o['contextFuelAfter']==16777216-cons
R=W/'team-directreg-aes-timing-independent';before=(R/'report.json').read_bytes();code=(R/'review.py').read_text()
old='sha(Path(p))';assert code.count(old)==1
code=code.replace(old,"sha(W / Path(p).relative_to('/private/tmp/amu-aes-resident-fuel-20261007'))")
# Only remaps the retained preregistration's absolute input roots. All raw checks/oracles remain byte-exact.
exec(compile(code,str(R/'review.py'),'exec'),{'__file__':str(R/'review.py'),'__name__':'__offline_evidence_review__'})
assert (R/'report.json').read_bytes()==before
r=ld(R/'report.json');assert r['runnerProcesses']==169 and r['acceptedTriples']==30 and r['attemptedTriples']==54 and r['rejectedTriples']==24 and r['calibrationProcesses']==7
assert r['qualifiedGains']==r['qualifiedRegressions']==r['qualifiedCOrBetter']==[]
print(json.dumps({'status':'PASS offline current negative directreg timing','members':len(rows),'semantics':3,'runnerPackets':169,'acceptedTriples':30,'attemptedTriples':54,'qualifiedGain':False,'qualifiedCWin':False,'recomputedIndependentReportSHA256':sha(R/'report.json'),'noNativeSolverNetworkTimingRuns':True,'prior566FourgenReplay':False},indent=2))
