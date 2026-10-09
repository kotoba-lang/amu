from pathlib import Path
import json,hashlib,sys
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-original19-functional-remaining50-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent
sys.path.insert(0,str(S));import run
pr=run.load(S/'preregistration.json');sp=run.load(S/'source-pins.json');ip=run.load(S/'input-pins.json')
for n,r in sp.items():run.pin(S/n,r)
for p,r in ip.items():run.pin(p,r)
q=run.load(O/'report.json');t=run.load(O/'terminal.json');a=run.load(O/'attempts.json');rr=run.load(O/'results.json')
assert t=={'loaderCalls':50,'allChildrenClosed':True,'failure':False}
assert q['status']=='COMPLETE_NEW_REMAINING50_RUNTIME_ADMISSION_ONLY'and len(a)==len(rr)==50
for r in q['evidence'].values():run.pin(r['path'],r)
for p,r in run.load(O/'generated-pins.json').items():run.pin(p,r)
for c,x,y in zip(pr['cases'],a,rr):
 assert x['label']==y['label']==c['label'] and x['nativeArgv']==c['nativeArgv'] and y['case']==c
 assert x['returncode']==y['returncode']==0 and x['state']=='terminal'and x['waitEntered']and not x['waitUncertain']
 v=x['controllerObservation'];assert v['semanticQualification']and not v['memoryAdmissionRecord']['otherRefusals']
 z=run.qualify((O/(c['label']+'.stdout')).read_bytes(),(O/(c['label']+'.stderr')).read_bytes(),c['expectedResult']);assert z==y['report']==x['structuredReportObservation']
 for n in ['stdout','stderr']:
  b=(O/(c['label']+'.'+n)).read_bytes();assert {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}==v['capture']['hashes'][n]
 assert y['strictOldMemoryPolicyPassed']==v['strictOldMemoryPolicyPassed']
prefix=run.prefix_raw(pr);joined=run.load(O/'joined-conditional-raw.json');assert len(joined)==190 and len(prefix)==140
for i in range(0,190,2):
 assert all(joined[i]['report'][k]==joined[i+1]['report'][k]for k in ['result','fuelInitial','fuelRemaining','fuelConsumed','arena17'])
assert q['joinedAdmittedCalls']==189 and q['joinedFullyAdmittedPairs']==94 and q['SLRETC32StillRefused']and not q['fullFunctionalAdmissionPassed']and not q['performanceQualified']
r={'status':'PASS_ROOT_SAVED_REMAINING50_AND_CONDITIONAL95_RAW_ONLY','sourcePinsSHA256':hashlib.sha256((S/'source-pins.json').read_bytes()).hexdigest(),'sourceFiles':len(sp),'inputFiles':len(ip),'newClosedWait0':50,'newAdmittedResults':50,'newStrictSampled':sum(x['strictOldMemoryPolicyPassed']for x in rr),'joinedRawPairs':95,'fullyAdmittedPairs':94,'retainedConditionalSLREPair':True,'originalV3Status':'FAIL','priorInvocationsRepeated':0,'performanceQualified':False,'C2':False}
(D/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
