"""Offline one-child SOURCE authoring. No native/setter/process APIs."""
from pathlib import Path
import json,hashlib,ast
D=Path(__file__).resolve().parent;W=D.parent
B=W/'crc-table-decision-collapse-tc-emitted-build8-source-v1-20261008';S=W/'crc-table-decision-collapse-tc-saved-emission-source-repair-v1-20261008';C=W/'crc-table-decision-collapse-native-component-v4-portable-env-20261008'
A=W/'crc-table-decision-collapse-tc-saved-emission-actual-review-independent-20261008/report.json';F=W/'crc-table-decision-collapse-tc-emitted-build8-saved-failure-review-independent-20261008/report.json'
H=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=H(b))
def save(n,q):(D/n).write_text(json.dumps(q,indent=2)+'\n')
assert pin(A)['sha256']=='98416905a0b6afad3a7cd04e1e73d50c04e10b9f667aac70a710f3271801c693';ap=json.loads(A.read_bytes());assert ap['status']=='PASS_INDEPENDENT_SAVED_RAW_TC_EMISSION_REPAIR_ONLY'
pr=json.loads((B/'preregistration.json').read_bytes());O=D/'run-outputs'
observer=pin(B/'run-outputs/emitter-observer.bin');container=pin(B/'run-outputs/observed-on-input.kseed');native=pin(B/'run-outputs/on-input.bin')
assert observer['sha256']=='f5bce9fe13a9a11a602be4d2272a053c5ce9e6eb96849ebd97b2d10eb4b75ecc'
assert container['sha256']=='c7b2b04eed1c0e5b07b4ac9d217c5f27c96b81b86b9003dc8767ea90312a68d3'
assert native['sha256']=='5187d8338730957bf4611f294117c811099af65c9d1117492dd57430e8fa8999'
pr.update(status='SOURCE_HOLD_TC_SAVED_OBSERVER_EXTRACT1_PENDING_TWO_REVIEWS',gateScope='one extract-native bench using exact saved observer/container only, no compilation/TC emitter/guest/timing',
 maximumLoaderCalls=1,maximumPythonWrapperStarts=1,maximumNativeCompilerChildStarts=1,maximumDistinctProcessStarts=2,
 maximumGateLoaderCPUSeconds=1800,maximumGateKernelCPUHardSeconds=1801,maximumGateWallPlusReapSeconds=1840,
 maximumGateRawPrefixBytes=8388608+1048576,maximumGateMemoryReceiptBytes=16777216,
 extractProducer=observer,savedContainer=container,expectedNative=native,expectedExports=[['bench',1264,1],['prefix-crc',1392,1],['prefix-seed',1420,1],['table-entry',1600,1]],
 actualEmissionProof=pin(A),actualEmissionProofStatus=ap['status'],offlineRepairReport=ap['offlineReport'],savedFailureProof=pin(F),
 savedFailureProofStatus='PASS_INDEPENDENT_SAVED_FAILURE_TC_CURRENT_EMITTED_CALLS7_ONLY',savedOutputRoot=str(B/'run-outputs'),savedImages=pin(B/'run-outputs/images.json'),
 freshOutputRoot=str(O),TCEmitterExecutionAuthorized=False,generatedWorkloadExecutionAuthorized=False,timingAuthorized=False,
 repeatedOriginalCalls=0,originalFailedBuild8RemainsFailed=True,remainingExtractQualified=False,guestRuntimeQualified=False,
 sourceBaselineWorkspace=str(B),lineage='audited current7618 -> saved emitter observer f5bc/current16 TC3d7 unity -> saved observedKSEEDc7b2; independent saved repair9841 certifies actual emission. This one extraction uses only saved f5bc image; no current/d3/LC variant substitution.')
pr['environment']=dict(pr['environment']);pr['environment']['TMPDIR']=str(O);pr['environment']['KEXE_CAP_RESOURCES_35']=str(O)
# Guest filesystem35 is restricted to fresh output; parent copies exact saved container.
pr['savedInputCopyPath']=str(O/'saved-observed-input.kseed')
args=['extract-native',pr['savedInputCopyPath'],'--symbol','bench','--output',str(O/'observed-on-input.bin')]
argv=[pr['loader']['path'],observer['path'],'0','0','aarch64','35,37,38,39','--',*args]
pr['orderedChildren']=[{'index':1,'label':'saved-observed-input-extract','nativeArgv':argv,'wrapperArgvTemplate':[pr['interpreter']['path'],str(D/'launch-wrapper.py'),'--journal-fd','<actual inherited journal fd>','--',*argv]}]
for n in ['adapter.py','launch-wrapper.py']:(D/n).write_bytes((B/n).read_bytes())
wp=D/'launch-wrapper.py';s=wp.read_text();old=""" if producer==pr['producer']['path']:checked(producer,pr['producer'])
 else:
  generated=json.loads((D/'run-outputs/generated-pins.json').read_bytes());checked(producer,generated[producer])""";new=""" assert producer==pr['extractProducer']['path'],'only saved observer image'
 checked(producer,pr['extractProducer'])
 checked(pr['savedContainer']['path'],pr['savedContainer'])
 checked(pr['savedInputCopyPath'],pr['savedContainer'])""";assert old in s;wp.write_text(s.replace(old,new))
s=(B/'run.py').read_text().replace('Exactly8 current-source TC build/emission children','Exactly1 saved observer extraction child')
s=s.replace('ROOT_GO_TC_CURRENT_EMITTED_BUILD8_ONLY','ROOT_GO_TC_SAVED_OBSERVER_EXTRACT1_ONLY').replace("g['maximumLoaderCalls']==8","g['maximumLoaderCalls']==1").replace("g['TCEmitterExecutionAuthorized']is True","g['TCEmitterExecutionAuthorized']is False")
s=s.replace('PASS_SOURCE_ONLY_TC_CURRENT_EMITTED_BUILD8','PASS_SOURCE_ONLY_TC_SAVED_OBSERVER_EXTRACT1').replace("pr['maximumPythonWrapperStarts']==8 and pr['maximumNativeCompilerChildStarts']==8","pr['maximumPythonWrapperStarts']==1 and pr['maximumNativeCompilerChildStarts']==1").replace('finite8 no retry','finite1 no retry').replace('len(rows)<8','len(rows)<1')
marker="  pin(pr['currentTypedBinding']['path'],pr['currentTypedBinding']);pin(pr['currentOriginalNative']['path'],pr['currentOriginalNative'])"
assert marker in s
s=s.replace(marker,marker+"\n  ep=load(pin(pr['actualEmissionProof']['path'],pr['actualEmissionProof']));need(ep['status']==pr['actualEmissionProofStatus'] and ep['savedCalls']==7 and ep['oldBuild8StillFailed']is True and ep['remainingExtractionAbsent']is True and ep['completeTypedAnd256DomainVerifierPassed']is True,'accepted saved emission repair, not old8 completion')\n  rp=load(pin(pr['offlineRepairReport']['path'],pr['offlineRepairReport']));need(ep['offlineReport']==pr['offlineRepairReport']and rp['status']=='PASS_SAVED_RAW_TC_EMISSION_REPAIR_ONLY'and rp['remainingExtractionExecuted']is False and rp['selectedEmission']==ep['recomputedSelectedEmission'],'exact accepted offline report')\n  fp=load(pin(pr['savedFailureProof']['path'],pr['savedFailureProof']));need(fp['status']==pr['savedFailureProofStatus']and fp['call8NotAttempted']is True and fp['completionAbsent']is True,'saved7 failure proof')\n  for name in ['extractProducer','savedContainer','expectedNative','savedImages']:pin(pr[name]['path'],pr[name])\n  si=load(pr['savedImages']['path']);need([r['native']for r in si if r['role']=='emitter-observer']==[pr['extractProducer']],'saved observer identity from current native build lineage')\n  so=Path(pr['savedOutputRoot']);need(not(so/'observed-on-input.bin').exists()and not(so/'completion.json').exists(),'preserved child8/completion absence in old namespace')\n  at=load(so/'attempts.json');tt=load(so/'terminal.json');need(len(at)==7 and all(r['state']=='terminal'and r['reaped']is True and r['returncode']==0 for r in at)and tt['attemptedCalls']==7 and tt['failure']is True and tt['allChildrenClosed']is True,'exact preserved seven closed and still failed')")
a=s.index(" env={'PATH':");z=s.index(" save(O/'effective-environment.json'",a);s=s[:a]+" env=dict(pr['environment']);need(len(env)==17,'exact extraction17 env')\n"+s[z:]
a=s.index(' def build(label,src,producer):');z=s.index(" finally:\n  save(O/'terminal.json'",a)
new=""" try:
  payload,exports=kseed(Path(pr['savedContainer']['path']).read_bytes());need(exports==[tuple(r)for r in pr['expectedExports']],'all saved source exports/offset/arity')
  need(payload==Path(pr['expectedNative']['path']).read_bytes(),'saved full native equality before extraction')
  copy=Path(pr['savedInputCopyPath']);copy.write_bytes(Path(pr['savedContainer']['path']).read_bytes());copy.chmod(0o444);capture(copy,4194560)
  target=O/'observed-on-input.bin';raw=call('saved-observed-input-extract',['extract-native',str(copy),'--symbol','bench','--output',str(target)],pr['extractProducer']['path'])
  expected=('{:ok true, :output "'+str(target)+'", :offset 1264, :length 3680, :arity 1}\\n').encode();need(raw==expected,'exact extract success stdout/source-export witness')
  nr=capture(target,4194304);need(target.read_bytes()==payload and {k:nr[k]for k in ['bytes','sha256']}=={k:pr['expectedNative'][k]for k in ['bytes','sha256']},'whole new observed extraction equals saved candidate native and both container payloads')
  guard();need(len(rows)==1 and rows[0]['state']=='terminal','one fresh extraction closed')
  completion={'status':'COMPLETE_TC_SAVED_OBSERVER_EXTRACT1_IDENTITY_ONLY','sourcePinsSHA256':g['sha256']['source-pins.json'],'rootGOSHA256':gh['sha256'],'native':nr,'savedContainer':pr['savedContainer'],'savedObserver':pr['extractProducer'],'expectedCandidateNative':pr['expectedNative'],'acceptedEmissionProof':pr['actualEmissionProof'],'exports':exports,'benchOffset':1264,'oldBuild8StillFailed':True,'oldCallsRepeated':0,'freshExtractionCalls':1,'TCEmitterExecuted':False,'generatedWorkloadExecuted':False,'guestRuntimeQualified':False,'performanceQualified':False,'selfhostFixedPointQualified':False,'OSStackLimitProof':False,'hardMemoryCapEstablished':False,'memoryMetric':'sum-ri_phys_footprint'}
  ok=True
 except BaseException as ex:
  save(O/'failure.json',{'status':'FAIL_FIRST_FAILURE_NO_RETRY','exception':repr(ex),'attemptedCalls':len(rows)});raise
"""
s=s[:a]+new+s[z:];s=s.replace("len(rows)==8 and all(r['state']=='terminal'for r in rows)","len(rows)==1 and all(r['state']=='terminal'for r in rows)").replace('valid-last all eight closed','valid-last one fresh extraction closed')
ast.parse(s);(D/'run.py').write_text(s)
ip=json.loads((S/'input-pins.json').read_bytes())
for name,v in json.loads((S/'source-pins.json').read_bytes()).items():ip[str(S/name)]=v
paths=[A,F,S/'source-pins.json',S/'input-pins.json',S/'freeze.json',Path(ap['offlineReport']['path'])]
paths.extend(Path(r['path'])for r in ap['sourceReviews'])
for p in paths:
 v=pin(p);ip[v['path']]={k:v[k]for k in ['bytes','sha256']}
save('input-pins.json',ip);pr.update(inputCount=len(ip),inputLogicalBytes=sum(v['bytes']for v in ip.values()),inputRegistrySHA256=pin(D/'input-pins.json')['sha256']);save('preregistration.json',pr)
gs=json.loads((B/'go-schema.json').read_bytes());gs['properties']['status']['const']='ROOT_GO_TC_SAVED_OBSERVER_EXTRACT1_ONLY';gs['properties']['maximumLoaderCalls']['const']=1;gs['properties']['TCEmitterExecutionAuthorized']['const']=False;gs['properties']['outputRoot']['const']=str(O);save('go-schema.json',gs)
