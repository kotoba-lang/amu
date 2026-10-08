"""Offline finite prereg/driver authoring. No operational invocation."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;W=D.parent
OLD=W/'crc-table-decision-collapse-native-component-v4-portable-env-20261008'
H=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=H(b))
def save(n,q):(D/n).write_text(json.dumps(q,indent=2)+'\n')
proof=W/'crc-table-decision-collapse-native-component-v4-portable-actual-review-independent-20261008/report.json'
q=json.loads(proof.read_bytes());assert H(proof.read_bytes())=='71c2a49c36a353a83f5df816193e9b128555b5ac9c7220d2a75b7d7b4f156096'
completion=OLD/'run-outputs/completion.json';co=json.loads(completion.read_bytes());assert H(completion.read_bytes())==q['completionSHA256']
producer=co['images'][0]['native'];assert producer['sha256']==q['wholeBaselineNative']['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'
p=json.loads((OLD/'preregistration.json').read_bytes())
p.update(status='SOURCE_DRAFT_TC_CURRENT_EMITTED_BUILD8_PENDING_TWO_REVIEWS',producer=producer,
 actualProducerProof=str(proof),actualProducerProofStatus=q['status'],currentProducerCompletion=pin(completion),
 currentTypedBinding=pin(OLD/'run-outputs/typed-binding.json'),currentOriginalNative=pin(OLD/'run-outputs/ordinary-input.bin'),
 baselineUnitySHA256='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418',
 candidateUnitySHA256=H((D/'unity-candidate.kotoba').read_bytes()),observerUnitySHA256=H((D/'unity-emitter-observer.kotoba').read_bytes()),
 lineage='audited d3 stage0 built exact current16 source953f -> current7618 builds TC3d7 current16 and diagnostic emitter observer. Measured LC5f is distinct and unused.',
 TCEmitterExecutionAuthorized=True,generatedWorkloadExecutionAuthorized=False,timingAuthorized=False,
 freshOutputRoot=str(D/'run-outputs'),sourceBaselineWorkspace=str(OLD),currentProducerBindingQualified=True,
 currentProducerBindingScope='originalCRC readonly current typed/output identity only, not candidate/runtime/fixedpoint/performance',
 gateScope='eight compiler/extract calls; candidate build and original CRC physical emitter certificate only; no generated guest execution',
 runtimeSuiteGO=False,maximumGateLoaderCPUSeconds=8*1800,maximumGateKernelCPUHardSeconds=8*1801,
 maximumGateWallPlusReapSeconds=8*(1810+30),maximumGateRawPrefixBytes=8*(8388608+1048576),
 maximumGateMemoryReceiptBytes=8*16777216)
p.pop('fixtureFailurePolicy',None);p.pop('orderedChildren',None)
p['environment']=dict(p['environment']);p['environment']['TMPDIR']=str(D/'run-outputs');p['environment']['KEXE_CAP_RESOURCES_35']=str(D/'run-outputs')
p['orderedChildren']=[]
O=D/'run-outputs';loader=p['loader']['path'];interp=p['interpreter']['path']
for role,src,prod in [('candidate','unity-candidate.kotoba',producer['path']),('emitter-observer','unity-emitter-observer.kotoba',producer['path']),('on-input','original-input.kotoba',str(O/'candidate.bin')),('observed-on-input','original-input.kotoba',str(O/'emitter-observer.bin'))]:
 for mode in ['compile','extract']:
  args=['compile',str(O/src),'--target','aarch64-macos','--output',str(O/(role+'.kseed'))]if mode=='compile'else['extract-native',str(O/(role+'.kseed')),'--symbol','main'if role in ['candidate','emitter-observer']else'bench','--output',str(O/(role+'.bin'))]
  argv=[loader,prod,'0','0','aarch64','35,37,38,39','--',*args]
  p['orderedChildren'].append({'index':len(p['orderedChildren'])+1,'label':role+'-'+mode,'nativeArgv':argv,'wrapperArgvTemplate':[interp,str(D/'launch-wrapper.py'),'--journal-fd','<actual inherited journal fd>','--',*argv]})
s=(OLD/'run.py').read_text().replace('Exactly8 current-source readonly binding children','Exactly8 current-source TC build/emission children')
s=s.replace('ROOT_GO_READONLY_TC_CURRENT_BIND8_PORTABLE_MEMORY_ONLY','ROOT_GO_TC_CURRENT_EMITTED_BUILD8_ONLY').replace("g['TCEmitterExecutionAuthorized']is False","g['TCEmitterExecutionAuthorized']is True").replace('exact bind8 GO','exact emitted build8 GO')
s=s.replace('d3a0e2ffe5887a1b77ace0e0a366dd8bda180f3e9ef2f7067a1e3436f9c3d15a','761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93').replace('explicit distinct stage0/current source','explicit audited current producer/source')
s=s.replace('PASS_SOURCE_ONLY_READONLY_TC_CURRENT_BIND8_PORTABLE_MEMORY','PASS_SOURCE_ONLY_TC_CURRENT_EMITTED_BUILD8')
old="""  ons=[r for r in pp['images'] if r.get('arm')=='ON'];need(len(ons)==1
      and ons[0]['native']==pr['producer'],'actual stage0 identity; no variant stitching')"""
new="""  need(pp['wholeBaselineNative']=={k:pr['producer'][k]for k in ['bytes','sha256']} and pp['currentProducerBindingQualified']is True and pp['TCEmitterExecuted']is False,'accepted current producer binding; no prior TC claim')
  pc=load(pin(pr['currentProducerCompletion']['path'],pr['currentProducerCompletion']))
  need(pc['status']=='COMPLETE_CURRENT_TYPED_BIND8_READONLY_IDENTITY_ONLY' and pc['images'][0]['native']==pr['producer'] and pc['sourcePinsSHA256']==pp['sourcePinsSHA256'],'current native/source completion')
  pin(pr['currentTypedBinding']['path'],pr['currentTypedBinding']);pin(pr['currentOriginalNative']['path'],pr['currentOriginalNative'])"""
assert old in s;s=s.replace(old,new)
s=s.replace("['unity-baseline.kotoba','unity-observer.kotoba','original-input.kotoba']","['unity-candidate.kotoba','unity-emitter-observer.kotoba','original-input.kotoba']")
s=s.replace("baseline=build('current-baseline',copies['unity-baseline.kotoba'],stage0)","candidate=build('candidate',copies['unity-candidate.kotoba'],stage0)")
s=s.replace("observer=build('readonly-observer',copies['unity-observer.kotoba'],stage0)","observer=build('emitter-observer',copies['unity-emitter-observer.kotoba'],stage0)")
s=s.replace("[('ordinary-input',baseline),('observed-input',observer)]","[('on-input',candidate),('observed-on-input',observer)]")
s=s.replace("ns['verify'](raw,payload,ex,copies['original-input.kotoba'].read_bytes())","ns['verify'](raw,payload,ex,copies['original-input.kotoba'].read_bytes(),load(pr['currentTypedBinding']['path']))")
s=s.replace('whole observed == fresh current ordinary before extract','whole observed == unobserved TC artifact before extract').replace('whole fresh current native identity','whole observed/unobserved TC native identity')
s=s.replace('COMPLETE_CURRENT_TYPED_BIND8_READONLY_IDENTITY_ONLY\',\n       \'images\'', 'COMPLETE_CURRENT_ORIGINAL_TC_EMITTED_BUILD8_ARTIFACT_IDENTITY_ONLY\',\n       \'images\'')
s=s.replace("'TCEmitterExecuted':False,'generatedWorkloadExecuted':False,","'TCEmitterExecuted':True,'generatedWorkloadExecuted':False,")
s=s.replace("'rootGOSHA256':gh['sha256'],","'rootGOSHA256':gh['sha256'],'currentProducer':pr['producer'],'currentProducerProof':pr['actualProducerProof'],'emissionCertificate':binding['actualEmission'],")
(D/'run.py').write_text(s)
ip=json.loads((OLD/'input-pins.json').read_bytes())
for n,v in json.loads((OLD/'source-pins.json').read_bytes()).items():ip[str(OLD/n)]=v
for path,v in q['evidence'].items():ip[path]=v
for f in [proof,completion,OLD/'input-pins.json',OLD/'source-pins.json',W/'crc-table-decision-collapse-v2-20261008/41-a64gen-candidate.kotoba']:
 z=pin(f);ip[z['path']]={k:z[k]for k in ['bytes','sha256']}
for n in ['current-baseline.bin','current-baseline.kseed','typed-binding.json','ordinary-input.bin','ordinary-input.kseed']:
 z=pin(OLD/'run-outputs'/n);ip[z['path']]={k:z[k]for k in ['bytes','sha256']}
save('input-pins.json',ip);p.update(inputCount=len(ip),inputLogicalBytes=sum(v['bytes']for v in ip.values()),inputRegistrySHA256=H((D/'input-pins.json').read_bytes()))
assert p['inputLogicalBytes']<=p['maximumInputLogicalBytes'];save('preregistration.json',p)
gs=json.loads((OLD/'go-schema.json').read_bytes());txt=json.dumps(gs).replace('ROOT_GO_READONLY_TC_CURRENT_BIND8_PORTABLE_MEMORY_ONLY','ROOT_GO_TC_CURRENT_EMITTED_BUILD8_ONLY');gs=json.loads(txt)
# Source schema is advisory; driver rejects unknown fields and exact booleans itself.
if 'properties'in gs:gs['properties']['TCEmitterExecutionAuthorized']={'const':True}
save('go-schema.json',gs)
