from pathlib import Path
import sys,hashlib,json,stat,runpy,contextlib,io,ast
sys.dont_write_bytecode=True
D=Path('/Users/junkawasaki/github/workspaces/codex/tc-hft-compose10-original-ns-runtime10-source-v1-20261009');O=Path(__file__).resolve().parent
H=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();assert s==p.lstat();return dict(bytes=len(b),sha256=H(b))
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json')
assert rec(D/'source-pins.json')['sha256']=='9c601bd972c362120b6a767745ecf6c41ee9a5decd17927ac78e2791265e61b2'
assert rec(D/'input-pins.json')['sha256']=='e59d6811e7017486e340027fce08193aa214bbff97376829b1fd29b78d8d8ba6'
def pins():
 assert len(sp)==20 and len(ip)==155 and sum(r['bytes']for r in ip.values())==13280263
 for n,r in sp.items():assert rec(D/n)==r
 for n,r in ip.items():assert rec(n)==r
pins()
for n,r in load(D/'component-binding.json')['components'].items():assert rec(D/n)==rec(r['path'])=={k:r[k]for k in ['bytes','sha256']}
for p in D.glob('*.py'):ast.parse(p.read_bytes())
sys.path.insert(0,str(D));captured={}
for n,result in [('pure-controls.py','pure-controls.json'),('wrapper-seal-controls.py','wrapper-seal-controls-result.json')]:
 b=io.StringIO()
 with contextlib.redirect_stdout(b):runpy.run_path(str(D/n),run_name='__main__')
 q=json.loads(b.getvalue());assert q==load(D/result);captured[n]=q
 (O/(n+'.stdout')).write_text(b.getvalue())
import run
run.source_scope(pr)
# Independent primary grammar/physical certificate rederivation, not report-only.
cs=Path('/Users/junkawasaki/github/wt/amu-seed17/tools/kexe_loader.c').read_text();body=cs[cs.index('int main(int argc, char **argv) {'):];assert body.index('argc = i;')<body.index('if (argc < 6 || argc > 11)')<body.index('argc != (int)(6 + arity)) return 2;')<body.index('fopen(')
cert=load(pr['emissionCertificate']['path']);before=Path(pr['images']['OFF']['native']['path']).read_bytes();after=Path(pr['images']['ON']['native']['path']).read_bytes();assert len(before)==len(after)==37520
changes=[dict(wordIndex=1+i//4,physicalByteOffset=i,before=int.from_bytes(before[i:i+4],'little'),after=int.from_bytes(after[i:i+4],'little'))for i in range(0,len(before),4)if before[i:i+4]!=after[i:i+4]];assert changes==cert['changes']and len(changes)==40
for arm in ['OFF','ON']:
 im=pr['images'][arm];b,e=run.container(Path(im['container']['path']).read_bytes());assert b==Path(im['native']['path']).read_bytes()and('batch',36440,1)in e
# Distinguish exact schema from conditional guard.
schema=load(D/'go-schema.json');g={k:None for k in schema['exactKeys']};g.update(status=pr['rootGOStatus'],maximumLoaderCalls=10,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,C2=False,outerHostLaunchRequiresEscalation=True)
try:run.go_header(g,pr,Path(pr['freshOutputRoot']))
except (AssertionError,KeyError):schemaMismatch=True
else:schemaMismatch=False
assert schemaMismatch and schema['exactKeys'].count('runtimeGuestAuthorized')==1 and len(schema['exactKeys'])==len(set(schema['exactKeys']))
g['runtimeGuestAuthorized']=True;assert run.go_header(g,pr,Path(pr['freshOutputRoot']))
pins()
report={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':rec(D/'source-pins.json')['sha256'],'inputPinsSHA256':rec(D/'input-pins.json')['sha256'],'driverSHA256':rec(D/'run.py')['sha256'],'preregistrationSHA256':rec(D/'preregistration.json')['sha256'],'sourceFiles':20,'inputFiles':155,'inputLogicalBytes':13280263,'unchangedQualifiedComponents':10,'wholeNativeWordChanges':40,'profiles':[0,1,2,17,32],'callsScheduled':10,'pureControlsByteIdentity':True,'wrapperPositiveSeals':10,'wrapperNegativeSeals':len(captured['wrapper-seal-controls.py']['refusedMutants']),'exactGOKeysQualified':True,'reviewCorrection':'Initial reviewer warning that runtimeGuestAuthorized was missing was incorrect. Exact frozen V1 schema includes it once and all pins unchanged; its None value in reviewer model rightly refused until true. Initial primary grammar audit matched a comment instead of statement; corrected to exact argc conditional. Initial audit saved locally. No subject issue or changes.','checkedContracts':['OFF9a7f current7618/953f whole artifact owner','ON9fd four closed compiler calls current source8b1b90 and actual full producer/artifact/header/40word emission','Original source265 defs+sentinel+rem267/30443 expanded; ownbatch36440arity1 full container','Primary loader typed i64 no-- grammar verified from f44 main ordering','Original matrix5profiles/C95Boolean-only oracle/exact17environment/FUEL16777216/all17arenas/capzero','Ten prior-qualified component bytes identical, unknownPID refusal retained, no retry, strict resource/sample/raw/closure, new fresh namespace/valid-last','700s/60remaining campaign, original30s CPUhard31/outer30/reap30, soft sampled physicalFootprint4GiB; no hardpeak/reservationquota claim'],'nativeCalls':0,'operationalAPICalls':0,'GOIssued':False,'frozenEdits':False,'scope':'Independent dense harness SOURCE review; reviewer authored optimizer rule, so rule architecture relies separate architecture reviews. This report does not claim independent architecture review of own rule.'}
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rec(O/'report.json')))
