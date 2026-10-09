from pathlib import Path
import json,hashlib,importlib.util,sys
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-original19-functional-remaining50-source-v1-20261009';D=Path(__file__).resolve().parent
sys.path.insert(0,str(S));import run
def h(p):
 b=Path(p).read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=run.load(S/'source-pins.json');ip=run.load(S/'input-pins.json');pr=run.load(S/'preregistration.json')
assert len(sp)==18 and len(ip)==3620
for n,r in sp.items():run.pin(S/n,r)
for p,r in ip.items():run.pin(p,r)
assert sum(r['bytes']for r in ip.values())==459212580
proofs=[run.load(pr[k]['path'])for k in ['OFFActualProof','TCActualProof','C95Oracle']]
assert run.selected_scope(pr,*proofs)
prefix=run.prefix_raw(pr);assert len(prefix)==140 and sum(r['admittedByOriginalCampaign']for r in prefix)==139
assert pr['cases']==pr['originalCases'][140:]and len(pr['originalCases'])==190
assert {c['workload']for c in pr['cases']}=={'statemate','tarfind','ud','wikisort','xgboost'}
spec=importlib.util.spec_from_file_location('pure_controls',S/'pure-controls.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
controls=mod.controls();assert controls==run.load(S/'pure-controls.json')
old=W/'tc-original19-functional190-source-v3-20261009'
for n in ['native-call.py','capture.py','controller.py','integration.py','typed-adapter.py','callback_contract.py','runtime.py','artifact_admission.py','loader_grammar.py']:assert (S/n).read_bytes()==(old/n).read_bytes()
from loader_grammar import interpretation
assert all(interpretation(c['nativeArgv'])=={'typedI64':[c['profile']],'guestArgv':None,'effectiveArgc':7}for c in pr['cases'])
source=Path(pr['loaderSourceGrammar']['path']).read_text()
main=source[source.index('int main(int argc, char **argv)'):];assert main.index('argc = i;')<main.index('argc != (int)(6 + arity)')<main.index('FILE *file = fopen(argv[1], "rb")')
driver=(S/'run.py').read_text();wrapper=(S/'launch-wrapper.py').read_text()
assert "g['maximumLoaderCalls']==50"in driver and "go['maximumLoaderCalls']==50"in wrapper
assert driver.index("save(O/'terminal.json'")<driver.index("save(O/'report.json'")
assert "'fullFunctionalAdmissionPassed':False"in driver and "'SLRETC32StillRefused':True"in driver
assert "'joinedAdmittedCalls':189"in driver and "'strictPhysicalMemoryQualified':False"in driver
assert "cases=pr['originalCases']"in driver and "pr['cases']==pr['originalCases'][140:]"in driver
report={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':h(S/'source-pins.json')['sha256'],'inputPinsSHA256':h(S/'input-pins.json')['sha256'],'driverSHA256':h(S/'run.py')['sha256'],'preregistrationSHA256':h(S/'preregistration.json')['sha256'],'sourceFiles':len(sp),'inputFiles':len(ip),'inputLogicalBytes':sum(r['bytes']for r in ip.values()),'fullPinsRehashed':True,'completeOriginal190ScopeBeforeExactRemaining50':True,'old140ClosedCallsRepeated':0,'savedPrefixRawRehashedAndDecoded':140,'retainedAdmittedRows':139,'retainedSLREREFUSE':True,'originalV3FAILPreserved':True,'qualifiedLifecycleAndDecodeComponentsUnchanged':True,'primaryLoaderGrammarChecked':True,'pureControls':controls,'reviewNotes':['new50 admission only; joined95 raw parity stays conditional; full190 admission false','original fuel/caps/ABI/source/profiles and unknown PID refusal unchanged','controlled1GiB reservation and finite callback/raw/resource bounds; not hard peak guarantee','exact seal/two SOURCE reviews/GO, fresh output/TMPDIR, no retry, valid-last terminal before completion'],'nativeCalls':0,'C2':False,'performanceQualified':False}
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({'status':report['status'],'report':h(D/'report.json')})
