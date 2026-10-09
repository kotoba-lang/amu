"""Synthetic bounded JSON/SHA contract model, not Kotoba/IPLD/native cache implementation."""
import json,hashlib,copy
from pathlib import Path
D=Path(__file__).resolve().parent
def need(v,m):
 if not v:raise AssertionError(m)
def encode(x):
 def check(v,depth=0):
  need(depth<=12,'finite depth')
  if type(v)in [int,bool,str]or v is None:
   if type(v)is int:need(-(2**63)<=v<2**63,'i64 only')
   if type(v)is str:need(len(v.encode())<=1024,'bounded string')
  elif type(v)is list:
   need(len(v)<=64,'bounded sequence')
   for z in v:check(z,depth+1)
  elif type(v)is dict:
   need(len(v)<=64 and all(type(k)is str for k in v),'string map keys')
   for k,z in v.items():check(k,depth+1);check(z,depth+1)
  else:raise AssertionError('unsupported value')
 check(x);b=json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode();need(len(b)<=65536,'bounded canonical model bytes');return b
def ident(domain,x):return hashlib.sha256(domain.encode()+b'\0'+encode(x)).hexdigest()
def snapshot(x):
 b=encode(x);return {'bytes':b,'id':hashlib.sha256(b).hexdigest()}
def validate_request(q):
 need(set(q)=={'schema','snapshot','owner','implementation','dependencies','readSet','inputState','rules','phase','targetABI','numericTrap','effect','resources','interpretation','outputContract'},'complete request fields')
 need(q['schema']=='compute-model/v1'and q['outputContract']=='owned-edge-min/v1','named model contracts')
 need(set(q['readSet'])=={'declared','closed','unclassifiedReads','unclassifiedWriters'}and q['readSet']['closed']is True and q['readSet']['unclassifiedReads']==q['readSet']['unclassifiedWriters']==[],'explicit read/writer closure premise')
 need(set(q['resources'])=={'compilerWorkCap','remainingObservableFuel','observableFuelSemantics'}and q['resources']['observableFuelSemantics']=='debit-each-use/v1','resource meanings')
 return ident('ComputeCID-model/v1',q)
def validate_result(q,r):
 need(set(r)=={'schema','snapshot','owner','outputContract','answer','edges','support','poison','diagnostics','effectTrap','logicalFuel'},'owned result fields, no request CID/global scratch')
 need(r['schema']=='result-model/v1'and r['snapshot']==q['snapshot']and r['owner']==q['owner']and r['outputContract']==q['outputContract'],'owned output scope')
 need(type(r['support'])is bool and type(r['poison'])is bool and type(r['logicalFuel'])is int and r['logicalFuel']>=0,'owned status/fuel')
 manifest=q['inputState']['edgeManifest'];need(len(r['edges'])==len(manifest)<=8,'complete edge ownership')
 for ordinal,(e,m)in enumerate(zip(r['edges'],manifest)):
  need(set(e)=={'edge','ordinal','target','parameter','arity','bound'}and all(e[k]==m[k]for k in ['edge','target','parameter','arity'])and e['ordinal']==ordinal,'exact order/edge/arity, not target aggregation')
  need(type(e['bound'])is int and e['bound']>=-1,'-1 neutral distinct from zero')
 return ident('ResultCID-model/v1',r)
def lookup(store,q,addressFn=None):
 cid=validate_request(q);address=addressFn(q)if addressFn else cid
 entry=store.get(address)
 if entry is None:return None
 need(set(entry)=={'complete','requestBytes','result','resultCID'},'complete stored binding fields')
 need(entry['complete']is True and entry['requestBytes']==encode(q),'full bounded key equality even forced hash collision')
 need(validate_result(q,entry['result'])==entry['resultCID'],'stored ResultCID verifies owned result bytes');return copy.deepcopy(entry['result'])
def aggregate(ledger):
 out={}
 # Original replay ordinal is retained; min here is the declared model merge.
 for edges in ledger.values():
  for e in edges:
   k=e['target']+':'+str(e['parameter']);v=e['bound']
   if v>=0:out[k]=v if k not in out else min(out[k],v)
 return out
def replay(q,r,state,admission,nonce):
 c=validate_request(q);rid=validate_result(q,r)
 need(set(admission)=={'allowed','authorityRevision','resourceContract','remainingFuel','noExternalWrite'}and admission['allowed']is True and admission['noExternalWrite']is True,'fresh admission, no cached authority')
 need(admission['resourceContract']==q['resources']['observableFuelSemantics']and admission['remainingFuel']==state['fuel'],'current resource binding')
 need(q['resources']['remainingObservableFuel']==state['fuel']and q['inputState']['existingAggregate']==state['aggregate'],'full conservative request matches current transition inputs')
 need(nonce not in state['receipts']and r['logicalFuel']<=state['fuel'],'single application receipt and logical budget')
 need(r['support']is True and r['poison']is False and state['callerSupported']is True and state['callerPoison']is False,'support loss/poison cannot be overwritten by saved success')
 new=copy.deepcopy(state);before=ident('State-model/v1',state)
 # Replace all contributions owned by this query, then reaggregate. No +=.
 key=q['snapshot']+'/'+q['owner']+'/'+q['outputContract'];new['ledger'][key]=copy.deepcopy(r['edges']);new['aggregate']=aggregate(new['ledger']);new['fuel']-=r['logicalFuel'];new['receipts'].append(nonce)
 receipt={'schema':'transition-model/v1','compute':c,'result':rid,'before':before,'after':ident('State-model/v1',new),'authorityRevision':admission['authorityRevision'],'nonce':nonce,'logicalFuelCharged':r['logicalFuel'],'compilerWorkMeasured':None,'hashLookupReplayCostMeasured':None,'admissionPassed':True}
 return new,receipt
def publish(store,q,r,receipt,flags):
 need(flags=={'owned':True,'complete':True,'validated':True,'persisted':True,'budgetPassed':True,'trap':False,'unsupported':False},'valid-last success only')
 c=validate_request(q);rid=validate_result(q,r)
 need(receipt['compute']==c and receipt['result']==rid and receipt['admissionPassed']is True,'verified current transition bound')
 need(r['support']is True and r['poison']is False,'no unsupported success binding')
 need(r['effectTrap']=='complete-no-trap','no failed result published')
 store[c]={'requestBytes':encode(q),'result':copy.deepcopy(r),'resultCID':rid,'complete':True};return c
def downstream_cut(oldResult,newResult,contract,before,after,pending):
 need(contract['closed']is True and contract['unclassified']==[]and pending==[],'complete consumer and SCC pending contract')
 return oldResult==newResult and all(before[k]==after[k]for k in contract['reads'])
def controls():
 positives=[];negatives=[]
 def reject(name,f):
  try:f()
  except (AssertionError,KeyError,TypeError):negatives.append(name)
  else:raise AssertionError('accepted mutant '+name)
 mutable={'typedBody':[1,2],'alias':[0,0]};snap=snapshot(mutable);frozen=bytes(snap['bytes']);mutable['typedBody'][0]=9;need(snap['bytes']==frozen and snapshot(mutable)['id']!=snap['id'],'owned snapshot changed alias');positives.append('mutable-source-sealed-copy')
 q={'schema':'compute-model/v1','snapshot':snap['id'],'owner':'query-A','implementation':'analyzer-CID1','dependencies':['def-A','def-B'],'readSet':{'declared':['SIR','FREC','bound4','aliases','support','poison','work','aggregate','control'],'closed':True,'unclassifiedReads':[],'unclassifiedWriters':[]},'inputState':{'bound4':[8,-1,0,4],'aliases':[0,0],'support':True,'poison':False,'compilerWork':0,'existingAggregate':{'T:0':12},'controlRevision':1,'edgeManifest':[{'edge':'e0','target':'T','parameter':0,'arity':1},{'edge':'e1','target':'T','parameter':0,'arity':1}]},'rules':'ruleCID1','phase':'shape-mode1','targetABI':'aarch64-v1','numericTrap':'i64-and-ordered-trap-v1','effect':'read-analysis-state','resources':{'compilerWorkCap':268435456,'remainingObservableFuel':100,'observableFuelSemantics':'debit-each-use/v1'},'interpretation':'typed-expanded-source-with-implicit-library/v1','outputContract':'owned-edge-min/v1'}
 r={'schema':'result-model/v1','snapshot':q['snapshot'],'owner':q['owner'],'outputContract':q['outputContract'],'answer':{'returnBound':8},'edges':[dict(m,ordinal=i,bound=v)for i,(m,v)in enumerate(zip(q['inputState']['edgeManifest'],[8,4]))],'support':True,'poison':False,'diagnostics':[],'effectTrap':'complete-no-trap','logicalFuel':4}
 state={'ledger':{'other-owner':[{'target':'T','parameter':0,'bound':12}]},'aggregate':{'T:0':12},'fuel':100,'receipts':[],'callerSupported':True,'callerPoison':False}
 adm={'allowed':True,'authorityRevision':1,'resourceContract':'debit-each-use/v1','remainingFuel':100,'noExternalWrite':True}
 s1,t1=replay(q,r,state,adm,'n1');need(s1['aggregate']=={'T:0':4}and s1['fuel']==96,'owned replacement/charged fuel');positives.append('ordered-same-target-distinct-edges')
 adm2=dict(adm,remainingFuel=96,authorityRevision=2);q2=copy.deepcopy(q);q2['resources']['remainingObservableFuel']=96;q2['inputState']['existingAggregate']=s1['aggregate'];s2,t2=replay(q2,r,s1,adm2,'n2');need(s2['aggregate']==s1['aggregate']and s2['ledger']==s1['ledger']and s2['fuel']==92 and t1!=t2,'idempotent contributions, fresh consumption');positives.append('replay-idempotent-ledger-not-free-fuel')
 reject('stale-full-request-at-new-state',lambda:replay(q,r,s1,adm2,'bad'))
 reject('duplicate-transition-nonce',lambda:replay(q2,r,s1,adm2,'n1'))
 weaker=copy.deepcopy(r);weaker['edges'][1]['bound']=10;q3=copy.deepcopy(q2);q3['resources']['remainingObservableFuel']=92;s3,_=replay(q3,weaker,s2,dict(adm2,remainingFuel=92),'n3');need(s3['aggregate']=={'T:0':8},'replace allows bound retraction, old4 not retained');positives.append('replace-reaggregate-removes-stale-min')
 neutral=copy.deepcopy(r);neutral['edges'][0]['bound']=-1;neutral['edges'][1]['bound']=0;s4,_=replay(q,neutral,state,adm,'n4');need(s4['aggregate']=={'T:0':0},'zero not neutral');positives.append('neutral-minus1-zero-distinct')
 flags={'owned':True,'complete':True,'validated':True,'persisted':True,'budgetPassed':True,'trap':False,'unsupported':False};store={};cid=publish(store,q,r,t1,flags);need(lookup(store,q)==r,'complete lookup');positives.append('valid-last-complete-binding')
 tampered=copy.deepcopy(store);tampered[cid]['result']['edges'][0]['bound']=9;reject('stored-result-corruption',lambda:lookup(tampered,q))
 incomplete=copy.deepcopy(store);incomplete[cid]['complete']=False;reject('stored-incomplete-binding',lambda:lookup(incomplete,q))
 missing=copy.deepcopy(store);missing[cid].pop('resultCID');reject('missing-stored-ResultCID',lambda:lookup(missing,q))
 for field in q:
  if field in ['schema','outputContract']:continue
  changed=copy.deepcopy(q)
  if field=='readSet':changed[field]['declared'].append('new-reader')
  elif field=='inputState':changed[field]['bound4'][0]+=1
  elif field=='resources':changed[field]['remainingObservableFuel']-=1
  elif type(changed[field])is list:changed[field].append('new-dependency')
  else:changed[field]+='changed'
  need(validate_request(changed)!=cid and lookup(store,changed)is None,'key invalidation '+field);positives.append('invalidate-'+field)
 for name,edit in [('transitive-body',lambda x:x['dependencies'].__setitem__(1,'def-B-new-body')),('aggregate',lambda x:x['inputState']['existingAggregate'].update({'T:0':3})),('alias',lambda x:x['inputState']['aliases'].__setitem__(0,1)),('support',lambda x:x['inputState'].update(support=False)),('poison',lambda x:x['inputState'].update(poison=True)),('work',lambda x:x['inputState'].update(compilerWork=1)),('control',lambda x:x['inputState'].update(controlRevision=2))]:
  changed=copy.deepcopy(q);edit(changed);need(validate_request(changed)!=cid,'full input invalidates');positives.append('invalidate-'+name)
 changed=copy.deepcopy(q);changed['implementation']='analyzer-CID2';need(validate_request(changed)!=cid and validate_result(changed,r)==validate_result(q,r),'output identity independent of request');positives.append('different-compute-equal-result-encoding-only')
 reject('forced-hash-collision-full-key',lambda:lookup({'forced':store[cid]},changed,lambda _: 'forced'))
 for k in flags:
  f=dict(flags);f[k]=not f[k];reject('publication-'+k,lambda f=f:publish({},q,r,t1,f))
 for name,edit in [('reordered',lambda x:x['edges'].reverse()),('missing-edge',lambda x:x['edges'].pop()),('wrong-arity',lambda x:x['edges'][0].update(arity=2)),('wrong-owner',lambda x:x.update(owner='B')),('borrowed-scratch',lambda x:x.update(globalScratch=1))]:
  bad=copy.deepcopy(r);edit(bad);reject('result-'+name,lambda bad=bad:validate_result(q,bad))
 for name,edit in [('permission-revoked',lambda x:x.update(allowed=False)),('fuel-insufficient',lambda x:x.update(remainingFuel=1)),('write-effect',lambda x:x.update(noExternalWrite=False))]:
  a=dict(adm);edit(a);reject(name,lambda a=a:replay(q,r,state,a,'bad'))
 for name,edit in [('support-loss',lambda x:x.update(callerSupported=False)),('poison-now',lambda x:x.update(callerPoison=True))]:
  s=copy.deepcopy(state);edit(s);reject(name,lambda s=s:replay(q,r,s,adm,'bad'))
 bad=copy.deepcopy(q);bad['readSet']['unclassifiedReaders']=['X'];reject('unknown-read-role',lambda:validate_request(bad))
 contract={'closed':True,'unclassified':[],'reads':['type','effect','aggregate','poison','interface','authority','budget']};view={k:0 for k in contract['reads']};rid=validate_result(q,r)
 need(downstream_cut(rid,rid,contract,view,view,[])is True,'complete view only');positives.append('equal-result-complete-consumer-view-candidate')
 changedview=dict(view,poison=1);need(downstream_cut(rid,rid,contract,view,changedview,[])is False,'poison invalidates consumer');positives.append('equal-result-not-enough-poison')
 reject('pending-SCC',lambda:downstream_cut(rid,rid,contract,view,view,['query-B']))
 reject('consumer-read-open',lambda:downstream_cut(rid,rid,dict(contract,closed=False),view,view,[]))
 reject('bounded-key-size',lambda:encode({'oversize':'x'*1025}))
 return {'status':'PASS_SYNTHETIC_BOUNDED_COMPUTE_RESULT_TRANSITION_CONTRACT_ONLY','positiveControls':positives,'refusedMutants':negatives,'maximumCanonicalBytes':65536,'maximumResultEdges':8,'productionReadClosureQualified':False,'IPLDQualified':False,'nativeImporterQualified':False,'performanceMeasured':False,'cacheEnabled':False,'C2':False,'newAnalysisSkips':0,'keyExclusions':[]}
if __name__=='__main__':
 result=controls();(D/'controls-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'positive':len(result['positiveControls']),'negative':len(result['refusedMutants']),'nativeCalls':0}))
