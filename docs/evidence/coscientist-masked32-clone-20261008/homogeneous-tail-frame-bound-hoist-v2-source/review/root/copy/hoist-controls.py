"""Pure in-pass invariant/read-write/cost law; no compiler/native execution."""
from pathlib import Path
import json,re,copy,importlib.util,hashlib
D=Path(__file__).parent;W=D.parent;R=Path('/Users/junkawasaki/github/wt/amu-seed17')
B=W/'tc-homogeneous-tail-frame-compose511-source-v1-20261009'
old=(B/'41-a64gen-candidate.kotoba').read_text();new=(D/'41-a64gen-candidate.kotoba').read_text();delta=json.loads((D/'source-delta.json').read_bytes());check=old
for a,b in delta['substitutions']:assert check.count(a)==1;check=check.replace(a,b)
assert check==new
# Extract exact forms, no textual prefix ambiguity.
spec=importlib.util.spec_from_file_location('scan',W/'shared-frame-currenttyped-observer3-library-closure-author-v1-20261009/diagnose.py');scan=importlib.util.module_from_spec(spec);spec.loader.exec_module(scan)
assert scan.form(new,'sf-codeend')==scan.form(old,'sf-codeend')
for n in ['sf-body','sf-frame','sf-clearlabels','sf-clearfix','sf-old-fix','sf-collapse']:assert scan.form(new,n)==scan.form(old,n).replace('Existing FN capacity bounds scans, work and additional labels to at most 511.','Existing FN-N<=512 admission bounds scans, work and additional labels to at most 511 (physical MM-FN-CAP8192).')
assert scan.form(new,'sf-tailfix').count('(sf-codeend ')==0 and scan.form(new,'sf-pair').count('(sf-codeend ')==1
assert new.count('(sf-tailfix M f g (inc k) k stop)')==1 and new.count('(sf-tailfix M f g (inc k) found stop)')==1
# Complete exact current geometry; mutable M writer effects must be disjoint.
ns=(R/'seed/00-ns.kotoba').read_text();const={n:int(v,0)for n,v in re.findall(r'\(def (MM-[A-Z0-9-]+|FF-CODE) (0x[0-9a-fA-F]+|[0-9]+)\)',ns)}
expected={'MM-FN-N':20,'MM-CODE-N':24,'MM-LABEL-N':23,'MM-FN-BASE':3277056,'MM-FN-W':16,'MM-FN-CAP':8192,'FF-CODE':13,'MM-LABEL-BASE':4325632,'MM-LABEL-CAP':131072,'MM-CODE-BASE':4456704,'MM-CODE-CAP':524288,'MM-FIX-BASE':4980992,'MM-FIX-W':4,'MM-FIX-CAP':65536}
assert all(const[k]==v for k,v in expected.items())
FN=set([20,24]+[3277056+16*k+13 for k in range(512)])
# All possible legal writes of sf-collapse: CODE3,LABELcell/count,FIXkind/target.
# Interval proof includes every entire writer region, stronger than exact7 writes.
ranges=[(4325632,4325632+131072),(4456704,4456704+524288),(4980992,4980992+4*65536)]
assert 23 not in FN and all(not(a<=p<b)for p in FN for a,b in ranges)
collapse=scan.form(new,'sf-collapse');assert collapse.count('(gn-put ')==7 and 'MM-FN-N'not in collapse[collapse.index('changed (->'): ]and 'MM-CODE-N'not in collapse[collapse.index('changed (->'):]
assert '(vector-assoc! M a w)'in(R/'seed/41-a64gen.kotoba').read_text()
def codeend(fn,f,cn):
 start=fn[f];out=cn
 for k in range(1,len(fn)):
  p=fn[k]
  if p>start and p<out:out=p
 return out
def tail_old(fn,f,g,cn,fix,words):
 start=fn[f];found=0;visits=0
 for k,x in enumerate(fix[1:],1):
  at,kind,t,aux=x;stop=codeend(fn,f,cn);visits+=len(fn)-1
  if at>=start+6 and at<stop and kind==4 and t==g:
   if found or aux or at<4 or [words.get(at+i)for i in [-4,-3,-2,-1,0,1]]!=[0xaa0903e0,0xf94003f3,0x910003bf,0xa8c17bfd,0x14000000,0xd4200020]or at+2!=stop:return -1,visits
   found=k
 return found,visits
def tail_new(fn,f,g,cn,fix,words):
 stop=codeend(fn,f,cn)if len(fix)>1 else cn;start=fn[f];found=0;visits=len(fn)-1 if len(fix)>1 else 0
 for k,x in enumerate(fix[1:],1):
  at,kind,t,aux=x
  if at>=start+6 and at<stop and kind==4 and t==g:
   if found or aux or at<4 or [words.get(at+i)for i in [-4,-3,-2,-1,0,1]]!=[0xaa0903e0,0xf94003f3,0x910003bf,0xa8c17bfd,0x14000000,0xd4200020]or at+2!=stop:return -1,visits
   found=k
 return found,visits
# Finite malformed metadata/context corpus: same predicates/sentinel outcome,
# not fabricated validation of malformed external buffers or arbitrary aliasing.
controls=[];fn=[0,10,30,60];cn=80;fix=[[0,0,0,0],[28,4,2,0]];words={24:0xaa0903e0,25:0xf94003f3,26:0x910003bf,27:0xa8c17bfd,28:0x14000000,29:0xd4200020}
cases=[('positive',fn,fix,words),('zero-real-fix',fn,fix[:1],words),('duplicate',fn,fix+fix[1:],words),('wrong-target',fn,[fix[0],[28,4,3,0]],words),('wrong-kind',fn,[fix[0],[28,1,2,0]],words),('nonzero-AUX',fn,[fix[0],[28,4,2,1]],words),('negative-at',fn,[fix[0],[-1,4,2,0]],words),('high-at',fn,[fix[0],[2**63-1,4,2,0]],words),('zero-entry-field',[0,10,0,60],fix,words),('negative-entry-field',[0,10,-1,60],fix,words),('high-entry-field',[0,10,2**63-1,60],fix,words),('duplicate-entry',[0,10,10,60],fix,words),('wrong-restore',fn,fix,{**words,26:0})]
for name,a,x,w in cases:
 oldr,oldv=tail_old(a,1,2,cn,x,w);newr,newv=tail_new(a,1,2,cn,x,w);assert oldr==newr;assert newv<=oldv;controls.append(name)
assert tail_new(fn,1,2,cn,fix[:1],words)[1]==0
# Actual saved finite fields, across every owner eligible to reach sf-tailfix.
spec=importlib.util.spec_from_file_location('base',D/'saved-base.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
flat=[base.fn[k][13]for k in range(len(base.fn))];saved=[]
for f in range(1,len(flat)):
 j=base.v.shape([base.fn[k]for k in range(len(base.fn))],[base.sir[k]for k in range(len(base.sir))],f)
 if not j:continue
 g=j['tail'];gj=base.v.shape([base.fn[k]for k in range(len(base.fn))],[base.sir[k]for k in range(len(base.sir))],g)
 if not gj or base.fn[f][15]!=base.fn[g][15]:continue
 x=[base.fix[k]for k in range(len(base.fix))];oldr,oldv=tail_old(flat,f,g,max(base.code)+1,x,base.code);newr,newv=tail_new(flat,f,g,max(base.code)+1,x,base.code);assert oldr==newr;saved.append({'owner':f,'old':oldr,'new':newr,'oldFNVisits':oldv,'newFNVisits':newv})
F=511;X=65535
out={'status':'PASS_PURE_PARAMETERIZED_IN_PASS_BOUND_HOIST_ONLY','syntheticPredicateCases':controls,'savedTailPredicates':saved,'sfCodeendReadClosure':['MM-FN-N','MM-CODE-N(initial end)','FN[f].FF-CODE','FN[k].FF-CODE for1<=k<FN-N'],'moduleMutable':True,'writerRegionsDisjoint':True,'functionCountCodeCountWrites':False,'allSevenMutationWritesRemainOriginal':True,'worstCaseCodeendVisitsBefore':F*X*F,'worstCaseCodeendVisitsAfter':F*F,'actualSavedOldFNVisits':sum(q['oldFNVisits']for q in saved),'actualSavedNewFNVisits':sum(q['newFNVisits']for q in saved),'zeroFixDoesNotIntroduceRead':True,'C2':False,'keyExclusions':[],'newCIDQuerySkips':0,'nativeCalls':0,'claim':'Finite pure source/data law; source module buffers/slot geometry and no concurrent/external mutation are required. Not native syntax, stack, compiler-fuel/arena/wall-time or optimizer ABI qualification.'}
(D/'hoist-controls-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['status','worstCaseCodeendVisitsBefore','worstCaseCodeendVisitsAfter','actualSavedOldFNVisits','actualSavedNewFNVisits']}))
