from pathlib import Path
import hashlib,json,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-table-decision-collapse-tc-saved-emission-source-repair-v1-20261008';R=W/'crc-table-decision-collapse-tc-saved-emission-actual-review-independent-20261008';G=W/'crc-table-decision-collapse-tc-saved-emission-repair-go-root-20261008/root-go.json';H=lambda b:hashlib.sha256(b).hexdigest();L=lambda p:json.loads(Path(p).read_bytes())
def pin(p,v):b=Path(p).read_bytes();assert len(b)==v['bytes']and H(b)==v['sha256'];return b
counts=[]
for n,rel in [('source-pins.json',True),('input-pins.json',False)]:
 reg=L(D/n);total=0
 for p,v in reg.items():pin(D/p if rel else p,v);total+=v['bytes']
 counts.append({'registry':n,'files':len(reg),'bytes':total,'sha256':H((D/n).read_bytes())})
g=L(G);assert g['status']=='ROOT_GO_SAVED_RAW_OFFLINE_REPAIR_ONLY'and g['maximumNativeCalls']==g['maximumProcessAPIReads']==0 and g['remainingExtractionAuthorized']is False and g['timingAuthorized']is False and g['oldBuild8StillFailed']is True
for k,n in [('sourcePinsSHA256','source-pins.json'),('inputPinsSHA256','input-pins.json'),('driverSHA256','verify-saved.py')]:assert g[k]==H((D/n).read_bytes())
assert len(g['sourceReviews'])==2
for x in g['sourceReviews']:
 rr=json.loads(pin(x['path'],x));assert rr['status']=='PASS_SOURCE_ONLY_SAVED_RAW_TC_EMISSION_REPAIR'and rr['sourcePinsSHA256']==g['sourcePinsSHA256']and rr['driverSHA256']==g['driverSHA256']
pr=L(D/'preregistration.json');O=Path(pr['savedOutputs']);p=D/'offline-outputs/report.json';saved=L(p);assert saved['status']=='PASS_SAVED_RAW_TC_EMISSION_REPAIR_ONLY'
blob=(O/'observed-on-input.kseed').read_bytes();assert blob==(O/'on-input.kseed').read_bytes();end=blob.index(b'\n\n');head=blob[:end].splitlines();payload=blob[end+2:];exports=[(r.split()[0].decode(),int(r.split()[1]),int(r.split()[2]))for r in head[1:]];assert payload==(O/'on-input.bin').read_bytes();assert len(payload)==int(head[0].split()[1])and len(exports)==int(head[0].split()[2])
ns={'__name__':'independent_saved_raw_only','__file__':str(D/'validate.py')};exec(compile((D/'validate.py').read_bytes(),str(D/'validate.py'),'exec'),ns);base=L(pr['currentTypedBinding']);result=ns['verify']((O/'observed-on-input-compile.stdout').read_bytes(),payload,exports,Path(pr['originalSource']).read_bytes(),base)
assert saved['selectedEmission']==result['actualEmission']and saved['wholeCodeWords']==result['wholeCodeWords']==407
for k,n in [('sourcePinsSHA256','source-pins.json'),('inputPinsSHA256','input-pins.json'),('preregistrationSHA256','preregistration.json')]:assert saved[k]==H((D/n).read_bytes())
assert saved['savedCalls']==7 and saved['repeatedNativeCalls']==0 and saved['remainingExtractionExecuted']is False and saved['oldBuild8StillFailed']is True and saved['wholeObservedUnobservedContainerIdentity']is True and saved['existingUnobservedNativeEqualsBothPayloads']is True
for k in ['guestRuntimeQualified','fixedPointQualified','performanceQualified','OSStackLimitProof']:assert saved[k]is False
assert L(O/'terminal.json')=={'attemptedCalls':7,'allChildrenClosed':True,'failure':True,'noRetry':True};assert len(L(O/'attempts.json'))==7 and not (O/'observed-on-input.bin').exists()and not (O/'completion.json').exists()
rr=result['allRawRecords'];site=result['eligibleSite'];cs,ce=site[6:8];cw=dict(rr['FCODE']);span=[cw[i]for i in range(cs,ce)];assert span==list(struct.unpack_from('<13I',payload,(cs-1)*4))
a={(x[1],x[2]):x[3]for x in rr['TCG']if x[0]==220};b={(x[1],x[2]):x[3]for x in base['allRawRecords']['TCG']if x[0]==220};assert len(a)==len(b)==76 and a==b;assert a[0,24]==3 and a[0,31]==7 and a[0,23]-1==24
assert span[0]&0xffe0ffe0==0xaa0003e0 and ((span[0]>>16)&31)==24 and (span[0]&31)==0;assert span[-1]&0xffe0ffe0==0xaa0003e0 and ((span[-1]>>16)&31)==0 and(span[-1]&31)==9
literal=[x for x in rr['FFIX']if cs<=x[1]<ce];assert literal==[[49,252,5,1,0]]
# Direct generic-reader normalization, independent from verifier helper.
def body(z):
 fields={(x[1],x[2]):x[3]for x in z['FF']if x[0]==1};lo=fields[1,13];hi=min(v for (fn,k),v in fields.items()if k==13 and v>lo);words=dict(z['FCODE']);seq=[words[i]for i in range(lo,hi)]
 for idx,at,kind,target,aux in z['FFIX']:
  if lo<=at<hi and kind==5:seq[at-lo]&=~0x1fffe0;seq[at+1-lo]&=~0x1fffe0
 return seq
assert body(rr)==body(base['allRawRecords'])
q={'status':'PASS_INDEPENDENT_SAVED_RAW_TC_EMISSION_REPAIR_ONLY','independent':True,'priorImplementationAuthorship':False,'scope':'Independent saved-output audit after independent SOURCE review and original saved seven-call failure audit. Pure frozen verifier recomputation plus separate word/role/generic-body checks; not driver rerun.','sourcePinsSHA256':g['sourcePinsSHA256'],'driverSHA256':g['driverSHA256'],'verifierSHA256':H((D/'validate.py').read_bytes()),'inputPinsSHA256':g['inputPinsSHA256'],'preregistrationSHA256':saved['preregistrationSHA256'],'rootGOSHA256':H(G.read_bytes()),'offlineReport':{'path':str(p),'bytes':p.stat().st_size,'sha256':H(p.read_bytes())},'freshHashClosure':counts,'sourceReviews':g['sourceReviews'],'recomputedSelectedEmission':result['actualEmission'],'selectedPhysicalWordsHex':[f'{x:08x}'for x in span],'selectedLiteralFixup':literal[0],'all76TCGPhasePairsEqualOFF':True,'genericReaderBodyIndependentlyNormalizedEqual':True,'wholeCodeWords':407,'completeTypedAnd256DomainVerifierPassed':True,'wholeObservedUnobservedKSEEDSHA256':H(blob),'existingUnobservedNativeEqualsBothPayloads':True,'oldBuild8StillFailed':True,'savedCalls':7,'remainingExtractionAbsent':True,'completionAbsent':True,'operationalCallsByReviewer':0,'driverRerunByReviewer':False,'limits':['Accepts the saved offline emission certificate only. Does not complete original build8; no observed native extraction receipt or guest runtime qualification.','Tool exit0 and exactly-once driver execution are root observations, not independently traced syscalls. Driver inspected as filesystem-only and saved report content independently reproduced.','No fixedpoint/performance/full19/cache reuse, OS stack/compile arena equivalence or hardpeak memory claim.'],'blockers':[]}
(R/'report.json').write_text(json.dumps(q,indent=2)+'\n');(R/'report.json').chmod(0o444);print(str(R/'report.json'),(R/'report.json').stat().st_size,H((R/'report.json').read_bytes()))
