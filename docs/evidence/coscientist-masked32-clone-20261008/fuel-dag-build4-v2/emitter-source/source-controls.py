from pathlib import Path
import json,importlib.util,sys,hashlib
sys.dont_write_bytecode=True
D=Path(__file__).parent;W=D.parent
spec=importlib.util.spec_from_file_location('source_author',D/'author.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
s=(D/'helpers.kotoba').read_text();forms=a.forms(s);assert len(forms)==6;assert [x[2].split()[1]for x in forms[1:]]==['df-body','df-shape','df-admit','df-emit-body','df-call']
for x in ['gn-f-id','gn-rtcall','gn-op-rt','gn-fix','gn-call-generic','vector-assoc!','nettle','sha256','aes','bench']:
 assert x not in s,x
call=a.defn(s,'df-call')[2];assert call.index('(gn-op-fuel m1)')<call.index('(di-init m2 f)');assert '(gn-gs (di-init m2 f) gn-f-ctx 1)'in call
assert '(di-restore 1 0)'in call and '(gn-vclear)'in call and '(gn-take i t 0)'in call
for name,z in json.loads((D/'reversal.json').read_bytes()).items():
 src=(D/name).read_text();parent=Path(z['parent']).read_text();feature=1 if '-on.'in name else 0
 helper=s.replace('(def df-feature 0)','(def df-feature '+str(feature)+')');old=a.defn(parent,'gn-op-call')[2];new=a.defn(src,'gn-op-call')[2];assert src.replace(helper+'\n','',1).replace(new,old,1)==parent
# Genuine saved checked/lowered corpus, read-only SOURCE body screen; not runtime caller admission.
vp=W/'vector-masked32-on-clone-observer-offline-validator-v4-controls/validate.py';spec=importlib.util.spec_from_file_location('saved_parser',vp);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
raw=W/'vector-masked32-on-clone-observer-remaining3-plan-v2-width/run-outputs/nettle-sha256-compile.stdout';ph,_=v.parse(raw.read_bytes());fr={x[0]:x[1:]for x in ph[2]['FREC']};sir={x[0]:x[1:]for x in ph[2]['SIR']};base=json.loads((W/'vector-fuel-scalar-dag-implementation-contract-v2-width/census.json').read_bytes());weights={3:0,4:0,5:10,6:16,7:16,8:12,13:6,19:4}
records=[]
for c in base['bodyCandidates']:
 f=c['callee'];p=c['sirStart'];end=c['sirEnd'];body=[sir[j]for j in range(p+3,end)];cost=sum(weights[x[0]]for x in body);assert cost<=96 and end-p+1<=32 and fr[f][2]==2 and fr[f][14]==1
 inner=c['nestedMask'];mp=fr[inner][12];labels=[sir[p+2][1],sir[mp+1][1]];assert labels[0]!=labels[1]
 assert not any(x[0]==21 for x in sir.values()) # OP-TAB=21 from pinned source.
 for l in labels:
  assert sum(x[0]==9 and x[1]==l for x in sir.values())==1
  assert not any((x[0]==10 and x[1]==l)or(x[0]in(11,12)and x[2]==l)for x in sir.values())
 records.append({'f':f,'bodyRows':end-p+1,'weightedBodyWords':cost,'staticCalls':len(c['staticOuterCalls']),'physicalAdmissionQualified':False})
# Register materialization count and arithmetic of conservative resource bound.
assert 6+2*4+1<=16 and 6+2*4+2==16 and 6+4+1<=12 and 6+4==10
assert 96+6+5*4+1+5+6+1==135 and 135<192
out={'status':'PASS_PURE_SOURCE_REVERSAL_AND_CONSERVATIVE_BODY_SCREEN_ONLY','fourExactReversals':True,'typedFormBalance':True,'originalFuelBeforeFrameReset':True,'noGenericFallbackAfterMutation':True,'savedBodyCandidates':records,'bodyCandidates':len(records),'staticCallCandidates':sum(x['staticCalls']for x in records),'wordBound':135,'nativeCalls':0,'physicalCallerAdmissionQualified':False,'performanceClaim':False}
(D/'source-controls.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'status':out['status'],'bodies':len(records),'calls':out['staticCallCandidates']}))
