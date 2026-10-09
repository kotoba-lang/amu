"""Pure saved342 consumer verifier; requires external independent child proofs."""
from pathlib import Path
from run import load,pin,need
from qualification import parse
def verify_saved(collectedRoot,runtimeRegistration,independentProofs):
 root=Path(collectedRoot);cases=runtimeRegistration['cases'];need(len(cases)==342 and len(independentProofs)==342,'complete independently audited342')
 results=[]
 for c,d in zip(cases,independentProofs):
  q=load(pin(d['path'],d));need(q['status']=='PASS_INDEPENDENT_CURRENT17_CONSUMER_QUALIFICATION_CHILD_CLOSURE_ONLY' and q['index']==c['index']and q['nativeArgv']==c['nativeArgv']and q['directWaitCount']==1 and q['reaped']is True and q['returncode']==0,'independent exact command closure')
  need(q['label']==c['label']and q['sourcePinsSHA256']==runtimeRegistration['qualificationSourcePinsSHA256'],'current qualifier source identity')
  for k in ['stdout','stderr']:pin(q[k]['path'],q[k])
  results.append(parse(Path(q['stdout']['path']).read_bytes(),Path(q['stderr']['path']).read_bytes(),c,c['expected'],0))
 return {'status':'PASS_SAVED_CURRENT17_CONSUMER_RESULT_FUEL_COUNTER_REPEAT_RESET_ONLY','closedConsumerCalls':342,'freshCalls':285,'repeatResetCalls':57,'elapsedPerformanceQualified':False,'officialEmbenchQualified':False,'answers':results}
