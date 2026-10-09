from pathlib import Path
import sys,json,hashlib,stat,runpy,contextlib,io,ast
sys.dont_write_bytecode=True
D=Path('/Users/junkawasaki/github/workspaces/codex/tc-homogeneous-tail-frame-compose10-native4-source-v1-20261009')
O=Path(__file__).resolve().parent
H=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();assert s==p.lstat();return {'bytes':len(b),'sha256':H(b)}
def load(p):return json.loads(Path(p).read_bytes())
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json')
assert rec(D/'source-pins.json')['sha256']=='aa820b0462c4de717f21c1f26283899719acefc7f1920edc85f1512eb50d5b6b'
assert rec(D/'input-pins.json')['sha256']=='1b90050c602e348c84c26043c1ea5aad524c756416cbbefc96f441455a3c53a9'
def pins():
 assert len(sp)==24 and len(ip)==81 and sum(v['bytes']for v in ip.values())==7864331
 for n,r in sp.items():assert rec(D/n)==r,n
 for n,r in ip.items():assert rec(n)==r,n
pins()
bind=load(D/'component-binding.json')
for n,r in bind['components'].items():assert rec(r['path'])=={k:r[k]for k in ('bytes','sha256')}==rec(D/n)
assert len(bind['components'])==8
for p in D.glob('*.py'):ast.parse(p.read_bytes())
a=load(D/'source-assembly.json')
assert len(a['modules'])==len(a['modulePins'])==16
for key,out in [('candidate41','candidate-current16.kotoba'),('ordinaryCandidate41','ordinary-current16.kotoba')]:
 b=b''.join(Path(a[key]['path']if n=='seed/41-a64gen.kotoba'else r['path']).read_bytes()+b'\n'for n,r in zip(a['modules'],a['modulePins']))
 assert b==(D/out).read_bytes()
sys.path.insert(0,str(D))
# Author controls may only write their two declared JSON results; intercept them.
oldwrite=Path.write_text;captures={};stdout=io.StringIO()
allowed={str(D/'source-controls.json'),str(D/'producer-controls-result.json')}
def capture(p,text,*args,**kwargs):
 assert str(p)in allowed,'unexpected SOURCE write '+str(p)
 captures[str(p)]=text.encode();return len(text)
Path.write_text=capture
try:
 with contextlib.redirect_stdout(stdout):
  for n in ['source-controls.py','producer-controls.py']:runpy.run_path(str(D/n),run_name='__main__')
finally:Path.write_text=oldwrite
assert set(captures)==allowed
controls=[]
for p,b in captures.items():
 assert b==Path(p).read_bytes(),p
 q=json.loads(b);assert q['nativeCalls']==0;controls+=q['controls']
assert len(controls)==68
(O/'pure-controls-output.txt').write_text(stdout.getvalue())
pins()
q={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':rec(D/'source-pins.json')['sha256'],'inputPinsSHA256':rec(D/'input-pins.json')['sha256'],'driverSHA256':rec(D/'run.py')['sha256'],'preregistrationSHA256':rec(D/'preregistration.json')['sha256'],'subject':str(D),'sourceFiles':24,'inputFiles':81,'inputLogicalBytes':7864331,'recomputedPureControls':68,'qualifiedComponentsByteIdentical':8,'nativeCalls':0,'GOIssued':False,'frozenSubjectEdited':False,'authorshipDisclosure':'Reviewer authored the copied compose10 Kotoba rule; independent review here covers dense-authored new registration/harness and bindings. Rule architecture relies on separate root and dense conditional SOURCE reviews.','checks':['Exact four ordered build/extract commands and main0 loader -- grammar; fifth invocation refused before callback by qualified caller ceiling and exact finite schedule.','Full current MANIFEST16 assembly reconstructed; only41 replacement, original nsichneu unchanged; expanded rem and267 typed FN evidence retained.','Current7618 whole sole-main0 baseline and its actual binding proof; newly generated G1 requires current GO-owned two admitted closed compile/extract receipt before execution.','Strict GO fields/two SOURCE reviews/fixture bindings; immutable full81 input and24 source pins rechecked before/after pure controls.','40-word prospective full native/container certificate independently reconstructed by recomputed controls; public exports and every unlisted byte preserved; actual new emission remains pending.','Exact17 supplied env with narrow CF metadata admission and explicit native exec17; named finite FSIZE64MiB CPU1800/1801, sampled physical-footprint policy,7500campaign/1840remaining; no resource relaxation/no retry.','Whole container/extract ABI and strict compiler raw reports; durable terminal and fresh complete report valid-last; no guests or performance claims.'],'nonBlockingNotes':['README says sampled RSS; operative adapter metric remains sum ri_phys_footprint, not RSS or a hard peak bound.','Private compiler frame nonalias/helper ABI and actual syntax/type/emission remain conditional prerequisites; this report does not independently certify the reviewer-authored optimizer rule.'],'scope':'SOURCE registration only; no native/guest, general ABI, speed, full19 semantics or adoption qualification.'}
(O/'report.json').write_text(json.dumps(q,indent=2)+'\n')
print(json.dumps(rec(O/'report.json')))
