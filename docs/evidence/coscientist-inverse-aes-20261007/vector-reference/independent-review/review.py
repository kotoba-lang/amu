import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib,importlib.util,collections
V=Path('/private/tmp/amu-aes-resident-fuel-20261007/team-general-vector-reference-v5');D=Path(__file__).parent
inputs={}
for f in ['artifact-pins.json','source-contract-input-pins.json']:
 for p,z in json.loads((V/f).read_text()).items():
  raw=Path(p).read_bytes();assert len(raw)==z['bytes']and hashlib.sha256(raw).hexdigest()==z['sha256'];inputs[p]=z
rs=json.loads((V/'reference-results.json').read_text());actual=[]
for r in rs:
 name=r['workload'];p=next(Path(p)for p in inputs if p.endswith('/'+name+'/observer-records.json'));recs=json.loads(p.read_text());ff={x['fields'][0]:x['fields'][1:]for x in recs if x['tag']=='FREC'};sir=[x['fields']for x in recs if x['tag']=='SIR'];body={};f=None
 for i,op,a,b,c in sir:
  if op==1:f=a;body[f]=[]
  if f is not None:body[f].append((i,op,a,b,c))
  if op==2:f=None
 graph={f:set(a for i,op,a,b,c in rows if op==13 and a in body)for f,rows in body.items()};addr={b for i,op,a,b,c in sir if op==22};roots={f for f in body if ff[f][2]!=2 or ff[f][11]!=0}|addr;reach=set();stack=list(roots)
 while stack:
  f=stack.pop()
  if f in reach:continue
  reach.add(f);stack.extend(graph.get(f,()))
 s=r.get('summaries',{}); domainRefused=r['status'].startswith('REFUSED')
 if not domainRefused:
  assert sorted(roots)==s['publicAddressedRoots'];assert sorted(addr)==s['FADDRTargets'];assert sorted(reach)==s['reachableFunctions']
  assert s['aliasSummariesConverged'] and s['rootedBoundsConverged']
  declared={(f,i,a,b,c)for f,rows in body.items()for i,op,a,b,c in rows if op==13}
  assert declared==set(map(tuple,s['allDeclaredDirectEdges']))
  assert all(f not in reach for f,i,a,b,c in s['certifiedUnreachableCallerEdges'])
  assert all(q['fn']in reach for q in r['reads']if q['admittedReference'])
 actual.append({'workload':name,'FRECrows':len(ff),'bodyFN':len(body),'directEdges':sum(map(len,graph.values())),'declaredCallSites':sum(op==13 for i,op,a,b,c in sir),'addressedTargets':sorted(addr),'independentRoots':sorted(roots),'unreachablePrivateBodies':sorted(set(body)-reach),'referenceSites':r['admittedCount'],'wholeModuleDomainRefused':domainRefused})
# Import exact frozen class without writing pycache or running owner main/fault writers.
sys.path.insert(0,str(V));from analyze import Module
# Synthetic model records retain same schema; full indexed-domain checks are intentionally not simulated.
def records(bodies):
 out=[];i=1
 for f,np,priv,ops in bodies:
  start=i;out.append({'tag':'SIR','fields':[i,1,f,np,4]});i+=1
  for op,a,b,c in ops:out.append({'tag':'SIR','fields':[i,op,a,b,c]});i+=1
  out.append({'tag':'SIR','fields':[i,2,f,0,0]});i+=1
  ff=[0]*16;ff[2]=2 if priv else 1;ff[3]=np;ff[5]=4 if np else 0;ff[10]=4;ff[11]=0 if priv else 1;ff[12]=start;ff[15]=4;out.append({'tag':'FREC','fields':[f,*ff]})
 for q in list(out):
  if q['tag']=='SIR'and q['fields'][1:3]==[14,176]:out.append({'tag':'CACHE','fields':[q['fields'][0],0,0,0,0]})
 return out
base=[(1,0,False,[(3,0,4,0),(14,200,0,1),(13,2,0,1),(19,0,0,0)]),(2,1,True,[(4,0,1,0),(3,1,2,0),(14,176,0,2),(19,0,0,0)])]
for f in range(3,13):base.append((f,1,True,[(4,0,1,0)]+([(13,f+1,0,1)]if f<12 else[])+[(19,0,0,0)]))
model=Module(records(base)).solve();sites=[q for q in model['reads']if q['admittedReference']]
(D/'mixed-nonconvergence-diagnostic.json').write_text(json.dumps({'scope':'finite synthetic SIR policy test only, not native/value failure','records':records(base),'aliasConverged':model['summaries']['aliasSummariesConverged'],'rootedBoundsConverged':model['summaries']['rootedBoundsConverged'],'remainingAliases':model['summaries']['returnAlias'],'remainingReturnLengths':model['summaries']['returnMinLength'],'remainingAdmittedReferenceSites':sites,'interpretation':'Alias exhaustion clears aliases and return lengths but does not globally disable independent allocation/parameter sites. This differs from a strict all-facts/global rollback requirement; no wrong value shown.'},indent=2)+'\n')
(D/'actual19-root-review.json').write_text(json.dumps(actual,indent=2)+'\n')
report={'status':'PASS bounded actual19 semantic/root review; HOLD universal fallback/native-layout/all-work qualification','verifiedOwnerInputs':len(inputs),'actual19':len(actual),'prioritySites':60,'allSites':sum(x['referenceSites']for x in actual),'actualRootGraphEquality':True,'actualConvergenceAllSupportedModules':True,'actualPicoUnreachable':next(x['unreachablePrivateBodies']for x in actual if x['workload']=='picojpeg'),'review':{'roots':'All nonprivate/export and FADDR operand b. Whole original declared calls included, including dead/probe callers. Closed checked first/count0 + trusted published host entry only; arbitrary private entry, open/replacement and callback contracts excluded. CAP/indirect disables exclusion.','allcaller':'Topological singleton-SCC propagation; every reachable incoming call argument min includingunknown. Invalidcaller poisons rather than disappearing. An absent call from complete valid worklist means structurally unreachable instruction. MultinodeSCC bounds unknown. Final allcaller assert checks everyrunCache reachedcall, not omitted malformed source recovery.','returnAlias':'Selfcall hypothesis substitutes the actual passed argument, marks anchorfalse. Every normal reachedRET must return exactlysameparam origin/epoch; one may nonassumedbase anchor. Aliased calls inherit passedidentity; full cleanclosure prevents arena rewind. Induction proves normal-returnidentity, not termination. RET2/RES2 unsupported; no arbitrary recursion seeding.','arity':'Exact200:1,208:3,168:1,176:2,72:1,144:2 now checked. Unknown and reset effects kill vector facts. First-five FF type4 mapping bound to checker vector-i64 contract; missing NF extra/body typing remains an emission gate.','budget':'Transfer262144 and8aliaspasses bounded. Actualall supportedmodules converge. Mixed control showsalias-pass exhaustion is per-summary clear, not global-site rollback; stronger advertised globalfallback needs prospectivefix or explicitrefinedcontract. Sharedwork excludes graph/caller/SCC/type/domain scans; no all-work bound certified.','lifetime':'Conditional validdescriptor length; validation/traps remainoriginal. Runtimeepochclean whitelist and emittedentry/return fingerprint assumed suppliedsource contract, not actual universalhost theorem.'},'mixedNonconvergencePolicyCounterexample':{'aliasConverged':model['summaries']['aliasSummariesConverged'],'retainedSites':len(sites),'wrongValueDemonstrated':False,'current19Affected':False},'LPV3':'Arithmeticfits only underregistered explicit64locals+64temps state orchecked64totalfactalternative, labels<=8192 reserveLP+16384, nooriginalgnhelperwhileactive, dirtyzero-check andcleanupallLP beforegn-loop. V5 Python state maps do not qualify this representation. Actualpositivealias/boundsummary max40; unsupportedlargecallee/caller stillunknown andgraph/effects scanned.','nativeBuildGuestSolverNetworkTiming':0,'productEdited':False,'recommendation':'Typed analysis-only authoring is reasonable after exact LPV3 fields/all-work cap/global-vs-per-summary fallback contract registration; no branch deletion or performance qualification yet.'}
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n')
for p in [V/'artifact-pins.json',V/'source-contract-input-pins.json',V/'terminal-report.json']+list(D.iterdir()):
 if p.is_file()and p.name not in ['artifact-pins.json','terminal.json']:inputs[str(p)]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(D/'artifact-pins.json').write_text(json.dumps(inputs,indent=2)+'\n');t={'allWritesComplete':True,'reportSHA':hashlib.sha256((D/'report.json').read_bytes()).hexdigest(),'pinsSHA':hashlib.sha256((D/'artifact-pins.json').read_bytes()).hexdigest(),'pins':len(inputs),'extraOfflineModelRuns':1,'nativeBuildGuestSolverNetworkTiming':0};(D/'terminal.json').write_text(json.dumps(t,indent=2)+'\n');print(json.dumps(t));print({'aliasConverged':model['summaries']['aliasSummariesConverged'],'retainedSites':len(sites)})
