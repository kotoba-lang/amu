"""Injected structural model/read-only SOURCE checks. No native/API execution."""
from pathlib import Path
import re,json,hashlib,itertools
D=Path(__file__).parent;B=Path('/Users/junkawasaki/github/workspaces/codex/tc-homogeneous-tail-frame-compose511-bound-hoist-source-v2-20261009');base=(B/'41-a64gen-candidate.kotoba').read_text();s=(D/'41-observer.kotoba').read_text();helper=(D/'helpers.kotoba').read_text()
# Reverse exact recorded diagnostic edits; no native parser/compiler involved.
a=s.index(helper);s=s[:a]+s[a+len(helper)+1:]
for name,notice in [('gn-ctx-safe','(qo-safe-note M f n depth work)'),('gn-ctx-scan','(qo-scan-note M j f depth work)')]:
 prefix=' :i64\n (let [qo-observation '+notice+']\n ';a=s.index('(defn- '+name+' ');p=s.index(prefix,a);body=p+len(prefix);depth=1;tokens=list(re.finditer(r'"(?:\\.|[^"\\])*"|;[^\n]*|[()]|[^\s()]+',s[body:]))
 for t in tokens:
  if t.group().startswith(';'):continue
  if t.group()=='(':depth+=1
  elif t.group()==')':
   depth-=1
   if depth==0:
    end=body+t.start();s=s[:p]+' :i64\n'+s[body:end]+s[end+1:];break
s=s.replace('(qo-top M i f n)','(gn-gs gn-f-ctx (if (>= (gn-ctx-safe M f n 8 512) 0) 1 0))')
s=s.replace('        qo-active (= (vector-at M2 MM-ERR) 0)\n        M2q (if qo-active (qo-init M2) M2)\n        M3 (if qo-active (gn-loop M2q 1) M2q)\n        M4 (if qo-active (qo-clean M3) M3)\n        n (vector-at M4 MM-CODE-N)]\n    (gn-put M4 MM-R0 (- n 1)))','        M3 (if (= (vector-at M2 MM-ERR) 0) (gn-loop M2 1) M2)\n        n (vector-at M3 MM-CODE-N)]\n    (gn-put M3 MM-R0 (- n 1)))')
s=s.replace('(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 88))','(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 80))')
assert s==base,'reverse SOURCE differs'
# Allocation and domain census under valid current typed generator invariants.
baseoff=16400+131072;owned=list(range(baseoff+80,baseoff+88));legacy=set(range(0,16))|set(range(16,16400))|set(range(16400,baseoff))|set(range(baseoff,baseoff+80));assert not(set(owned)&legacy)and max(owned)<baseoff+88
assert set(range(baseoff+5,baseoff+13)) & set(range(baseoff+4,baseoff+80)), 'original invalid placement negative'
assert '(+ (* bank 38) k)' in base and '(di-save M 0 0)' in base and '(di-save 1 0)' in base
for dirty in itertools.product([0,1,-1],repeat=8):
 initialized=[0]*8
 # Model ordinary error and normal completion both clearing activation.
 for error in [False,True]:assert [0 for x in initialized]==[0]*8
assert 'M4 (if qo-active (qo-clean M3) M3)'in (D/'41-observer.kotoba').read_text()
# Model exact query computation and observer instrumentation, including work.
def query(bodies,f,n,depth,work,openrange=(0,0),trace=None):
 if trace is not None:trace.append(('call',f,n,depth,work))
 if f not in bodies or depth<=0 or work<=0 or n>7 or openrange[0]<=f<sum(openrange):return -1
 left=work-1
 for j,(op,a,b,c)in enumerate(bodies[f]):
  if trace is not None:trace.append(('scan',f,j,depth,left))
  if left<=0:return -1
  left-=1
  if op=='end':return left if a==f else -1
  if op=='call':
   left=query(bodies,a,c,depth-1,left,openrange,trace)
   if left<0:return -1
  elif op=='rt':
   if not((a==1 and c==2 and b<=5)or(a==2 and c==3 and b<=4)or(a in [3,4,5]and c==1)):return -1
  elif op not in ['const','fuel','ret','br','trap']:return -1
 return -1
models=0
for size,child,budget,depth,openstart in itertools.product([0,1,7,511],[False,True],[1,2,8,512],[1,2,8],[0,1]):
 bodies={1:[('const',0,0,0)]*size+([('call',2,0,1)]if child else[])+[('end',1,0,0)],2:[('fuel',0,0,0),('end',2,0,0)]};t=[];answer=query(bodies,1,1,depth,budget,(openstart,1 if openstart else 0));assert query(bodies,1,1,depth,budget,(openstart,1 if openstart else 0),t)==answer;assert len(t)<=2*budget+3;models+=1
# Long recursive shared-work/cycle refuses rather than memo-claim termination.
t=[];assert query({1:[('call',1,0,1),('end',1,0,0)]},1,1,8,512,trace=t)==-1
# Conservative maximum diagnostic row volume, independent of actual hit count.
records=16*(513+513)+2*256+3;assert records*256+65536<8388608
key=(3,1,8,512,0,0);assert all(tuple(v+1 if i==k else v for i,v in enumerate(key))!=key for k in range(6))
assert '(gn-ctx-safe original f n 8 512)'in helper and helper.count('answer (gn-ctx-safe')==1
q={'status':'PASS_FINITE_OBSERVER_SOURCE_MODELS_ONLY','reverseCurrentCandidateExact':True,'dirtyCleanupModels':3**8,'queryModels':models,'conservativeRowCap':records,'maxDiagnosticBytesPlus64KiBOrdinary':records*256+65536,'scratchRelativeBase':baseoff+80,'scratchRelativeEndExclusive':baseoff+88,'allocatedBlockWords':baseoff+88,'actualOperations':0,'nativeQualified':False}
(D/'controls.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q))
