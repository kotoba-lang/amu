from pathlib import Path
import json,hashlib,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent;F=W/'vector-leaf-straight-read-cache-functional30-plan-v2-controls';A=W/'vector-leaf-straight-read-cache-full19-selfbuild40-actual-review-v1-width';B=W/'vector-leaf-straight-read-cache-functional30-actual-review-v2-width';P=W/'vector-masked32-functional285-actual-review-v3-controls';H=lambda b:hashlib.sha256(b).hexdigest();J=lambda p:json.loads(Path(p).read_bytes())
def rc(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':H(b)}
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
old=J(F/'preregistration.json');ip=J(F/'input-closure.json');proofs=dict(old['proofs'])
for role,folder,status in [('LC40',A,'PASS_INDEPENDENT_ACTUAL_LC_FULL19_SELFBUILD40_IDENTITY_ONLY'),('LC30',B,'PASS_INDEPENDENT_ACTUAL_LC_MD5_SHA30_FUNCTIONAL_ONLY'),('resourceProfiles',P,'PASS_INDEPENDENT_FINITE_MASKED32_ORIGINAL19_285_FUNCTIONAL_ONLY')]:
 r=rc(folder/'report.json');p=rc(folder/'input-pins.json');assert J(r['path'])['status']==status;proofs[role]={'report':r,'inputPins':p,'status':status}
 for k,v in J(p['path']).items():
  assert k not in ip or ip[k]==v;ip[k]=v
 for z in [r,p]:ip[z['path']]={k:z[k]for k in ['bytes','sha256']}
accepted=rc(W/'vector-leaf-straight-read-cache-functional30-go-v2-root/root-acceptance.json');ip[accepted['path']]={k:accepted[k]for k in ['bytes','sha256']};profile=rc(P/'profiles.json');ip[profile['path']]={k:profile[k]for k in ['bytes','sha256']}
actual=J(A/'report.json');sr=J(old['proofs']['SR40']['report']['path']);sr4=J(old['proofs']['SR4']['report']['path']);cr=J(old['proofs']['C19']['report']['path']);rr=J(old['proofs']['CConsumer19']['report']['path']);matrix=rc(W.parent.parent/'wt/amu-seed17/bench/embench/comparison-matrix.json');ip[matrix['path']]={k:matrix[k]for k in ['bytes','sha256']};cases=[];profiles=J(profile['path'])
for e in J(matrix['path'])['entries']:
 n=e['workload']
 if n in ['md5sum','nettle-sha256']:continue
 on=next(z for z in actual['images']if z['workload']==n);off=next(z for z in(sr4['images']if n=='nettle-aes'else sr['remaining17'])if z.get('workload',z.get('label'))==n);c=next(z for z in cr['images']if z['workload']==n);r=next(z for z in rr['images']if z['workload']==n)
 src=rc(W.parent.parent/'wt/amu-seed17'/e['source']);assert src['sha256']==e['expectedSourceSha256'];ip[src['path']]={k:src[k]for k in ['bytes','sha256']}
 vals=[z for z in profiles if z['workload']==n];assert [v['n']for v in vals]==e['iterations']and all(v['nativeFuelConsumed']<16777216 for v in vals)
 cases.append({'workload':n,'source':src,'symbol':e['symbol'],'iterations':e['iterations'],'OFF':off['native'],'OFFContainer':off['container'],'OFFOffset':off['offset'],'ON':on['native'],'ONContainer':on['container'],'ONOffset':on['offset'],'C':rc(W/'vector-param-C-transfer-v1-root/collected-build'/n/'c.dylib'),'CRunner':rc(W/'vector-param-original19-transfer-v1-root/collected-runner-build'/n/'runner'),'CSymbol':c['cSymbolPlannedOnly'],'resourceReferenceProfiles':vals})
 for z in [cases[-1]['C'],cases[-1]['CRunner']]:ip[z['path']]={k:z[k]for k in ['bytes','sha256']}
assert len(cases)==17
save(D/'input-closure.json',dict(sorted(ip.items())))
pr={'status':'PROSPECTIVE_SOURCE_ONLY_LC_REMAINING17_FUNCTIONAL255_BEFORE_DRIVER_AUTHORING','maximumFutureChildCalls':255,'nativeCalls':170,'CCalls':85,'retainedAcceptedCalls':30,'joinedOriginal19Calls':285,'firstFailureStop':True,'noRetry':True,'sourceReviewStatus':'PASS_SOURCE_ONLY_LC_REMAINING17_FUNCTIONAL255','rootGOStatus':'ROOT_AUTHORIZED_LC_REMAINING17_FUNCTIONAL255_ONLY','root40AcceptanceRequired':'ROOT_ACCEPTED_INDEPENDENT_LC_FULL19_SELFBUILD40_IDENTITY_ONLY','proofs':proofs,'LC30Acceptance':accepted,'resourceProfiles':profile,'canonicalMatrix':matrix,'loader':old['loader'],'CConsumerSource':old['CConsumerSource'],'CConsumerRawReport':old['CConsumerRawReport'],'cases':cases,'nativeFuel':16777216,'nativeCaps':old['nativeCaps'],'maximumInputFiles':4096,'maximumInputLogicalBytes':402653184,'outputRoot':str(D/'run-outputs'),'parentProducerScope':'G0 LC2586 images; G1/G2/G3 fixedpoint does not establish recompiled G3-original19 correspondence','resourceScope':'Exact per-profile earlier full19 actual285 supports same16M and fixed arenas, including depthconv2000 and xgboost32; prospective OFF/ON still fail closed on exhaustion. Terminal used is not peak.','nativeCallsByAuthor':0,'timingAuthorized':False,'compilerSSHAuthorized':False}
save(D/'preregistration.json',pr);print('prereg frozen before driver',len(ip),sum(v['bytes']for v in ip.values()))
