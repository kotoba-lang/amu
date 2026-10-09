from pathlib import Path
import json,hashlib,shutil,sys,runpy,contextlib,io,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'held-launch-v5-loader-build5-source-v2-20261009-independent';O=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_bytes())
def rec(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json')
assert len(sp)==9 and len(ip)==pr['exactInputFiles']==58 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']==406824755
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
C=O/'copied-source';C.mkdir(exist_ok=False)
for n in sp:shutil.copyfile(D/n,C/n)
sys.path.insert(0,str(C));import run
assert run.scope(pr,ip);assert not Path(pr['outputRoot']).exists()
s=io.StringIO()
with contextlib.redirect_stdout(s):runpy.run_path(str(C/'pure-controls.py'),run_name='__main__')
(O/'pure-controls.stdout').write_text(s.getvalue());ctrl=json.loads(s.getvalue())
assert ctrl['actualClangBuildCalls']==ctrl['actualFDProcessGuestCalls']==0 and len(ctrl['refusals'])==31
subject=load(Path(pr['subjectPreregistration']['path']));assert pr['cases'][3]['argv']==subject['prospectiveLoaderBuildArgv']
for n in ['run.py','limit-exec.py']:ast.parse((D/n).read_text())
for n,r in sp.items():assert rec(D/n)==r,n
for p,r in ip.items():assert rec(Path(p))=={k:r[k]for k in ['bytes','sha256']},p
q=dict(status=pr['sourceReviewStatus'],sourcePinsSHA256=rec(D/'source-pins.json')['sha256'],inputPinsSHA256=rec(D/'input-pins.json')['sha256'],driverSHA256=rec(D/'run.py')['sha256'],preregistrationSHA256=rec(D/'preregistration.json')['sha256'],sourceFilesVerified=9,inputFilesVerified=58,inputLogicalBytes=406824755,controls=ctrl,exactProspectiveV5BuildArgv=True,subjectSourcePinsSHA256=pr['subjectSourcePins']['sha256'],reviewScope='Exact one C loader bootstrap, five direct tool calls; guest0',sourceBoundDefaultSDKAndLibraryInputsGated=True,normalClosedCompilerDiagnosticEvidenceBounded=True,cleanBuildClaim=False,limitations=['No actual compiler/dependency/link-preview/build execution','No universal compiler descendant closure or wholeSDK qualifier','No guest/WNOWAIT/FD/channel/ownership lifecycle proof','No full19 functional/performance/adoption qualification'],ClangCalls=0,GO=False)
(O/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(status=q['status'],report=rec(O/'report.json'))))
