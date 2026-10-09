from pathlib import Path
import hashlib,json,sys,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'shared-frame-currenttyped-observer3-source-v1-20261009';D=Path(__file__).resolve().parent
sys.path.insert(0,str(S));import run
sp=run.load(S/'source-pins.json');ip=run.load(S/'input-pins.json');pr=run.load(S/'preregistration.json')
assert len(sp)==23 and len(ip)==2841 and sum(r['bytes']for r in ip.values())==449385544
for n,r in sp.items():run.pin(S/n,r)
for p,r in ip.items():run.pin(p,r)
spec=importlib.util.spec_from_file_location('controls',S/'source-controls.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);controls=m.controls();assert controls==run.load(S/'source-controls.json')
delta=run.load(S/'instrumentation-delta.json');ordinary=(S/'ordinary-current16.kotoba').read_text();observed=(S/'observer-current16.kotoba').read_text();helper=(S/'observer-helpers.kotoba').read_text()
assert observed.count(helper+'\n')==1
bare=observed.replace(helper+'\n','',1)
for kind in ['Loop','Driver','Layout']:
 assert bare.count(delta['new'+kind])==1;bare=bare.replace(delta['new'+kind],delta['old'+kind],1)
assert bare==ordinary and hashlib.sha256(ordinary.encode()).hexdigest()=='94fe39401f5f0a1120b12b2d17bf000d14a54c9c68e1f8976b8b0ced8794f199'
assert '(vector-assoc! M'not in helper and '(gn-put 'not in helper and '(gn-gs 'not in helper
assert delta['newLoop'].count('(gn-ins M i op)')==1 and helper.count('(gn-run M)')==2 and helper.count('(ly-run M)')==1
fixture=W/'crc-capture-popen-transfer-fixture-source-v3-20261009'
for n in ['capture.py','controller.py','integration.py']:assert(S/n).read_bytes()==(fixture/n).read_bytes()
assert pr['maximumLoaderCalls']==len(pr['cases'])==3 and not pr['runtimeGuestAuthorized']and not pr['timingAuthorized']and not pr['C2']
for c in pr['cases']:
 argv=c['nativeArgv'];assert argv[:7]==[pr['loader'],argv[1],'0','0','aarch64',pr['capabilities'],'--']
 assert argv[7]in ['compile','extract'];assert argv[8].startswith(pr['freshOutputRoot']+'/')
assert pr['cases'][-1]['ordinaryContainer'] and 'expectedFNCount'in pr['cases'][-1]
assert controls['actualNativeThreadProcessFDPipeCalls']==0 and len(controls['negativeControls'])==23
r={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':run.receipt(S/'source-pins.json')['sha256'],'inputPinsSHA256':run.receipt(S/'input-pins.json')['sha256'],'driverSHA256':run.receipt(S/'run.py')['sha256'],'preregistrationSHA256':run.receipt(S/'preregistration.json')['sha256'],'sourceFiles':len(sp),'inputFiles':len(ip),'inputLogicalBytes':449385544,'fullPinsRehashed':True,'exactSourceInverse':True,'originalGnInsGnRunLyRunPreserved':True,'helperWritesOnlyOwnedQ':True,'qualifiedLifecycleUnchanged':True,'primaryArity0GuestArgumentGrammarChecked':True,'controls':controls,'scope':'three compiler commands; whole ordinary container equality; no guest','limitations':['prospective native syntax/selector binding','read-only diagnostic resources differ from ordinary compilation','bounded12 owner observation does not prove rewrite or stack/trap equivalence','sampled memory only; unknown/unbound PID refuses'],'nativeCalls':0,'C2':False,'performanceQualified':False}
(D/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
