"""Finite pure contract model, not a cache implementation or production analyzer."""
import json,hashlib,copy
FIELDS=['schema','snapshot','analyzer','definition','dependencies','rules','stage','ABI','numeric','effects','traps','resourceContract','f','mode','entry4','readView','existingTargets','support','poison','diagnostics','workBefore','workLimit','fuelBefore','logicalCharge','admission']
def canonical(x,cap=16384):
 b=json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode();assert len(b)<=cap;return b
def cid(x):return hashlib.sha256(canonical(x)).hexdigest()
def request(q):
 assert set(q)==set(FIELDS) and q['mode']==1 and type(q['f'])is int and 1<=q['f']<128
 assert len(q['entry4'])==4 and all(type(v)is int and -1<=v<2**31 for v in q['entry4'])
 assert len(q['dependencies'])<=32 and len(q['existingTargets'])<=8 and len(q['readView'])<=8
 assert 0<=q['workBefore']<=q['workLimit']==268435456 and 0<=q['logicalCharge']<=q['fuelBefore']<2**64
 assert q['support']is True and q['poison']is False and q['admission']is True
 return canonical(q)
def answer(q):
 request(q);edges=[]
 for ordinal,e in enumerate(q['readView']):
  assert set(e)=={'site','target','arity','contribution4'} and type(e['site'])is int and 0<=e['site']<8193 and type(e['target'])is int and 0<e['target']<128 and type(e['arity'])is int and 0<=e['arity']<=32
  assert len(e['contribution4'])==4 and all(type(v)is int and -1<=v<2**31 for v in e['contribution4'])
  edges.append(dict(e,ordinal=ordinal))
 a={'scope':{'snapshot':q['snapshot'],'definition':q['definition'],'outputContract':'owned-mode1-summary-edges/v1'},'summary':[len(edges),0,1,0,min(q['entry4']),len(edges)],'edges':edges,'support':True,'poison':False,'diagnostics':copy.deepcopy(q['diagnostics']),'logicalCharge':q['logicalCharge']}
 canonical(a,8192);return copy.deepcopy(a)
def replay(q,a):
 request(q);assert a==answer(q),'owned answer/full ordered replay contract, not digest alone'
 targets=copy.deepcopy(q['existingTargets']);before=copy.deepcopy(targets)
 for ordinal,e in enumerate(a['edges']):
  assert e['ordinal']==ordinal and str(e['target'])in targets
  for k,L in enumerate(e['contribution4']):
   if L!=-1:targets[str(e['target'])][k]=L if targets[str(e['target'])][k]<0 else min(targets[str(e['target'])][k],L)
 assert q['workBefore']+a['logicalCharge']<=q['workLimit']
 return {'before':before,'after':targets,'fuelBefore':q['fuelBefore'],'fuelAfter':q['fuelBefore']-a['logicalCharge'],'logicalCharge':a['logicalCharge'],'workBefore':q['workBefore'],'workAfter':q['workBefore']+a['logicalCharge'],'callerPoisonApplied':False,'currentAdmission':True}
def publish(q,a,t,complete=True):
 assert complete is True;assert a==answer(q) and t==replay(q,a)
 return {'valid':True,'requestBytes':request(q),'computeCID':cid(q),'answer':copy.deepcopy(a),'resultCID':cid(a),'transitionCID':cid(t)}
def lookup(q,bucket):
 # Deliberately does not trust matching hash: forced hash collision is tested.
 assert bucket['valid']is True and bucket['requestBytes']==request(q)
 assert bucket['answer']==answer(q) and bucket['resultCID']==cid(bucket['answer'])
 return replay(q,bucket['answer'])
def refuses(fn):
 try:fn()
 except (AssertionError,KeyError,TypeError,ValueError):return True
 raise AssertionError('negative admitted')
def controls():
 q={k:'v1'for k in FIELDS};q.update(schema='full-shadow-only/v1',dependencies=['D1'],f=1,mode=1,entry4=[8,8,0,-1],readView=[{'site':11,'target':2,'arity':4,'contribution4':[8,-1,0,7]},{'site':12,'target':2,'arity':4,'contribution4':[4,0,-1,-1]}],existingTargets={'2':[-1,9,3,-1]},support=True,poison=False,diagnostics=[],workBefore=128,workLimit=268435456,fuelBefore=1000,logicalCharge=256,admission=True)
 a=answer(q);t=replay(q,a);b=publish(q,a,t);assert lookup(q,b)==t and t['after']['2']==[4,0,0,7] and t['fuelAfter']==744
 frozen=copy.deepcopy(a);q['readView'][0]['contribution4'][0]=99;assert a==frozen; q['readView'][0]['contribution4'][0]=8
 mutations=[]
 for key in FIELDS:
  z=copy.deepcopy(q);v=z[key]
  if type(v)is bool:z[key]=not v
  elif type(v)is int:z[key]=v+1
  elif type(v)is str:z[key]=v+'-changed'
  elif type(v)is list:z[key]=copy.deepcopy(v)+[0]
  else:z[key]=dict(v,changed=0)
  assert cid(z)!=cid(q) and refuses(lambda:lookup(z,b));mutations.append(key)
 coll=copy.deepcopy(b);coll['computeCID']=cid(dict(q,ABI='different'));assert refuses(lambda:lookup(dict(q,ABI='different'),coll))
 results=[]
 for name,change in [('missing-edge',lambda x:x['edges'].pop()),('reordered-edge',lambda x:x['edges'].reverse()),('arity',lambda x:x['edges'][0].update(arity=3)),('neutral-to-zero',lambda x:x['edges'][0]['contribution4'].__setitem__(1,0)),('wrong-owner',lambda x:x['scope'].update(definition='other')),('support-drop',lambda x:x.update(support=False)),('poison-drop',lambda x:x.update(poison=True)),('diagnostic-change',lambda x:x.update(diagnostics=['hidden'])),('charge-zero',lambda x:x.update(logicalCharge=0))]:
  aa=copy.deepcopy(a);change(aa);assert refuses(lambda:replay(q,aa));results.append(name)
 assert refuses(lambda:publish(q,a,t,False));assert refuses(lambda:replay(dict(q,workBefore=268435456),a));assert refuses(lambda:lookup(q,dict(b,valid=False)))
 # Equal result encoding for two requests is not evidence of two actual analyzer executions.
 q2=dict(q,ABI='different');assert cid(q)!=cid(q2) and cid(answer(q))==cid(answer(q2))
 # Caller support loss must poison targets in original order; it cannot publish success.
 lost=dict(q,support=False);assert refuses(lambda:publish(lost,a,t));poisoned=copy.deepcopy(t['after'])
 for e in q['readView']:poisoned[str(e['target'])]=[0,0,0,0]
 assert poisoned=={'2':[0,0,0,0]} and poisoned!=t['after']
 return {'status':'PASS_FINITE_PURE_CONTRACT_MODEL_ONLY','keyMutationRefusals':mutations,'forcedHashCollisionRefused':True,'ownedCopyUnaffectedByInputMutation':True,'resultMutantRefusals':results,'duplicateTargetEdgesPreserved':True,'neutralMinusOneDistinctFromZero':True,'fuelChargePreserved':256,'tornPublicationBudgetSupportLossRefused':True,'callerPoisonNegativeDetected':True,'differentRequestSameResultEncodingOnly':True,'productionReadClosureQualified':False,'nativeImporterQualified':False,'performanceQualified':False,'C2':False,'actualCompilerNativeThreadFDNetworkCalls':0}
if __name__=='__main__':print(json.dumps(controls(),indent=2))
