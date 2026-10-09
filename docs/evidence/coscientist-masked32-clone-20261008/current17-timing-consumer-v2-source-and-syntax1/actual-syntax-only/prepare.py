from pathlib import Path
import json,hashlib,importlib.util,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-hft-current17-timing-consumer-source-v1-20261009-crc';O=Path(__file__).parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json')
for n,r in sp.items():assert {k:rec(D/n)[k]for k in ['bytes','sha256']}==r
for n,r in ip.items():assert {k:rec(Path(n))[k]for k in ['bytes','sha256']}=={k:r[k]for k in ['bytes','sha256']}
C=O/'copied-source';C.mkdir();origins=[]
for n in ['timing-loader.c','timing-extension.h','timing-frontend.h','header.py']:
 b=(D/n).read_bytes();(C/n).write_bytes(b);origins.append(rec(D/n))
spec=importlib.util.spec_from_file_location('header_model',C/'header.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
r=load(D/'packet.json')['entries'][0];off=Path(r['OFF']['native']['path']).read_bytes();on=Path(r['ON']['native']['path']).read_bytes()
# Explicit synthetic data operand only. Never a real fresh-C proof or runnable dylib.
c=struct.pack('<8I',0xfeedfacf,0x100000c,0,6,0,0,0,0);cr=dict(bytes=len(c),sha256=hashlib.sha256(c).hexdigest());model=dict(status='PASS_INDEPENDENT_FRESH_CURRENT19_C_BUILD_SOURCE_IDENTITY_ONLY',workload=r['workload'],symbol=r['symbol'],bridgeABI='I64_8ARGS',artifact=cr)
(C/'timing-packet-generated.h').write_bytes(h.header(r,off,on,c,model))
q=dict(status='PREPARED_LOCAL_C_SYNTAX_ONLY_DIAGNOSTIC',sourcePins=rec(D/'source-pins.json'),origins=origins,syntheticHeader=rec(C/'timing-packet-generated.h'),syntheticDylibBytes=32,syntheticModelIsProof=False,guestCallsAuthorized=0,objectOrExecutableOutputAuthorized=False,maximumClangTopLevelCalls=1,CPUsoftSeconds=30,CPUhardSeconds=31,regularFileLimitBytes=16777216,argv=['/usr/bin/clang','-std=c11','-DKEXE_OWNERSHIP_DIAGNOSTIC_V3','-fsyntax-only','-I',str(C),str(C/'timing-loader.c')],productCompilerLLVMFallback=False,performanceQualified=False)
(O/'preregistration.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(sources=len(origins),syntaxOnly=True,syntheticHeader=True,argv=q['argv'])))
