"""Pure static SOURCE controls. AST selects parser functions only: main/Ledger never loaded or called."""
from pathlib import Path
import ast,json,hashlib,stat,re
D=Path(__file__).resolve().parent;J=lambda p:json.loads(Path(p).read_bytes());H=lambda b:hashlib.sha256(b).hexdigest()
s=(D/'run.py').read_bytes();tree=ast.parse(s);allowed={'need','load','regular','pin','container','native','unique','csample'};nodes=[]
for n in tree.body:
 if isinstance(n,ast.FunctionDef)and n.name in allowed:nodes.append(n)
 elif isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in {'NATIVE','CAPS','CFIELDS'}for t in n.targets):nodes.append(n)
ns={'Path':Path,'json':json,'hashlib':hashlib,'stat':stat,'re':re};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<parser-only AST>','exec'),ns)
pr=J(D/'preregistration.json');cl=J(D/'input-closure.json');assert len(pr['cases'])==19 and sum(len(c['iterations'])for c in pr['cases'])==95 and pr['maximumFutureChildCalls']==285 and pr['nativeCalls']==190 and pr['CCalls']==95 and pr['retainedAcceptedCalls']==0
assert pr['maximumInputFiles']==4096 and pr['maximumInputLogicalBytes']==448*1024**2 and not(D/'run-outputs').exists()
assert len(cl)<=4096 and sum(v['bytes']for v in cl.values())<=448*1024**2
# Stat every single inherited input before streaming any closure hash.
for path,v in cl.items():p=ns['regular'](path,v['bytes']);assert p.stat().st_size==v['bytes']
for path,v in cl.items():ns['pin']({'path':path,**v})
for role,p in pr['proofs'].items():
 q=J(p['report']['path']);assert q['status']==p['status'] and q[p.get('inputPinsSHA256Field','inputPinsSHA256')]==p['inputPins']['sha256']
 for path,v in J(p['inputPins']['path']).items():assert cl[path]==v
accept=J(pr['scalar44RootAcceptance']['path']);assert accept['status']==pr['root44AcceptanceRequired'] and accept['independentActualReceipt']==pr['proofs']['scalar44']['report'] and accept['sourcePinsSHA256']==pr['root44SourcePinsSHA256']
assert accept['closedLoaderCalls']==44 and accept['original19CompileExtractCalls']==38 and accept['selfbuildCalls']==6
matrix=J(pr['canonicalMatrix']['path'])['entries'];images=J(pr['scalar44Images']['path']);profiles=J(pr['resourceProfiles']['path']);cr=J(pr['proofs']['C19']['report']['path']);rr=J(pr['proofs']['CConsumer19']['report']['path'])
mutants=0;positive=0;cpositive=0
for c,e,z in zip(pr['cases'],matrix,images):
 assert c['workload']==e['workload']==z['workload'] and c['source']==z['source'] and c['source']['sha256']==e['expectedSourceSha256'] and c['symbol']==e['symbol'] and c['iterations']==e['iterations']==z['iterations']
 sr=J(pr['proofs']['SR4'if c['workload']in ['nettle-aes','nettle-sha256']else'SR40']['report']['path']);off=next(v for v in(sr['images']if c['workload']in ['nettle-aes','nettle-sha256']else sr['remaining17'])if v.get('workload',v.get('label'))==c['workload']);assert c['OFF']==off['native'] and c['OFFContainer']==off['container'] and c['OFFOffset']==off['offset']
 assert c['ON']==z['native'] and c['ONContainer']==z['container'] and c['ONOffset']==z['offset']
 for arm in ['OFF','ON']:
  ex,p=ns['container'](c[arm+'Container']);assert ex==c[arm+'Exports'] and p==Path(c[arm]['path']).read_bytes() and {'name':c['symbol'],'offset':c[arm+'Offset'],'arity':1}in ex
 assert [(v['name'],v['arity'])for v in c['OFFExports']]==[(v['name'],v['arity'])for v in c['ONExports']]
 ci=next(v for v in cr['images']if v['workload']==c['workload']);ri=next(v for v in rr['images']if v['workload']==c['workload']);assert ci['sha256']==c['C']['sha256'] and ci['bytes']==c['C']['bytes'] and ci['cSymbolPlannedOnly']==c['CSymbol'] and ri['runnerSHA256']==c['CRunner']['sha256'] and ri['runnerBytes']==c['CRunner']['bytes']
 cb=Path(c['C']['path']).read_bytes();rb=Path(c['CRunner']['path']).read_bytes();assert rb.count(cb)==1 and rb.find(cb)==ri['immutableImageByteAnchors']['C']
 assert c['resourceReferenceProfiles']==[v for v in profiles if v['workload']==c['workload']]
 for r in c['resourceReferenceProfiles']:
  a=r['nativeArenas'];b=('{' +f':status :ok :result {r["result"]} :fuel '+'{'+f':initial 16777216 :remaining {16777216-r["nativeFuelConsumed"]}'+'} '+ ' '.join(':'+x+' {'+f':capacity {a[y]["capacity"]} :used {a[y]["used"]}'+'}'for x,y in [('heap','pairs'),('string-pool','stringPoolBytes'),('vectors','vectors'),('vector-items','vectorItems')])+'}\n').encode();ns['native'](b,b'',r['n']);positive+=1
  for mutant,err in [(b[:-1],b''),(b.replace(b':status :ok',b':status :trap'),b''),(b.replace(b':remaining ',b':unknown '),b''),(b.replace(b':initial 16777216',b':initial 0'),b''),(b,b'noise'),(b+b,b''),(b.replace(b':remaining '+str(16777216-r['nativeFuelConsumed']).encode(),b':remaining 0'),b'')]:
   try:ns['native'](mutant,err,r['n'])
   except AssertionError:mutants+=1
   else:raise AssertionError('native malformed/trap/exhaustion accepted')
  q={'format':'kotoba.runtime-sample/v1','calls':1,'warmupCalls':0,'elapsedNanoseconds':1,'result':r['result'],'maxRssBytes':1,'fuelPerCall':16777216,'contextFuelBefore':16777216,'contextFuelAfter':16777216,'contextFuelConsumed':0,'nativeArtifactAbi':'kotoba.native-artifact-i64x8-to-i64-indirect/v1','artifactKind':'dylib','nativeArenaStatus':'unavailable-C','nativeArenas':None};ns['csample']((json.dumps(q)+'\n').encode(),b'',r['n']);cpositive+=1
  for key,value in [('result',1-r['result']),('calls',2),('warmupCalls',1),('contextFuelConsumed',1),('nativeArenaStatus','ok'),('nativeArenas',{})]:
   x=dict(q);x[key]=value
   try:ns['csample']((json.dumps(x)+'\n').encode(),b'',r['n'])
   except AssertionError:mutants+=1
   else:raise AssertionError('C mutant accepted')
  try:ns['csample']((json.dumps(q)[:-1]+',"result":0}\n').encode(),b'',r['n'])
  except AssertionError:mutants+=1
  else:raise AssertionError('duplicate key accepted')
v1=Path(pr['priorFailedNamespace']['driver']['path']);oldtree=ast.parse(v1.read_bytes())
for name in ['need','load','save','regular','pin','container','native','unique','csample','Ledger']:
 before=next(n for n in oldtree.body if getattr(n,'name',None)==name);after=next(n for n in tree.body if getattr(n,'name',None)==name);assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False),'functional parser/ledger immutable '+name
oldpr=J(pr['priorFailedNamespace']['preregistration']['path']);assert oldpr['cases']==pr['cases'] and oldpr['nativeFuel']==pr['nativeFuel'] and oldpr['nativeCaps']==pr['nativeCaps'] and oldpr['proofs']==pr['proofs']
assert pr['priorFailedAttempts']==1 and pr['maximumCumulativeAttempts']==286 and pr['launcherConstraint']['sandbox_permissions']=='require_escalated'
prior=pr['priorFailedNamespace'];vr=J(prior['independentReview']['path']);assert vr['status']=='CLOSED_FAIL1_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_SANDBOX_INIT_ONLY' and vr['auditInputPinsSHA256']==prior['independentReviewInputPins']['sha256'] and vr['rootGO']==prior['GO'] and vr['rawStdout']==prior['stdout'] and vr['rawStderr']==prior['stderr'] and vr['bodyResultEvidence']is False
for path,v in J(prior['independentReviewInputPins']['path']).items():assert cl[path]==v
assert J(prior['terminal']['path'])=={'calls':1,'allCallsClosed':True,'failure':True,'noRetry':True}
rows=J(prior['attempts']['path']);assert len(rows)==1 and rows[0]['state']=='terminal' and rows[0]['returncode']==125 and rows[0]['stdoutSHA256']==prior['stdout']['sha256'] and rows[0]['stderrSHA256']==prior['stderr']['sha256']
assert J(prior['report']['path'])['completedTriples']==0 and not(D/'run-outputs').exists()
report={'status':'PASS_PURE_STATIC_SOURCE_CONTROLS_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_V2','closureFiles':len(cl),'closureLogicalBytes':sum(v['bytes']for v in cl.values()),'artifactPairs':19,'nativeParserSyntheticPositiveControls':positive,'CParserSyntheticPositiveControls':cpositive,'rejectedSyntheticMutants':mutants,'operationalDriverCalls':0,'nativeCompilerGuestSSHCalls':0,'noMainOrLedgerLoaded':True,'candidateRuntimeQualified':False,'functionalParsersLedgerBodiesFuelCapsUnchangedFromV1':True,'fullV1FailedAttemptAndReviewClosureRetained':True,'priorFailedAttempts':1,'maximumCumulativeAttempts':286}
(D/'pure-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
