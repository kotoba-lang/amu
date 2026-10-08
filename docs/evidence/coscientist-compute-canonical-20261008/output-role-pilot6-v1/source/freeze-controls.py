from pathlib import Path
import sys,json,hashlib,ast,re,runpy
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;W=D.parent;B=W/'vector-compute-current19-query-census40-plan-v2-controls'
forms=runpy.run_path(str(D/'source-preparation.py'))['forms']
def pin(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
kernel=(D/'41-result.kotoba').read_text();definitions={}
for a,b,t in forms(kernel):
 m=re.match(r'\(defn-?\s+([^\s\[()]+)',t)
 if m:definitions[m.group(1)]=(a,b,t)
seen=set();todo=['cq-original-query']
while todo:
 name=todo.pop()
 if name in seen:continue
 seen.add(name)
 for child in re.findall(r'\(([^\s()\[\]{}]+)',definitions[name][2]):
  if child in definitions and child not in seen:todo.append(child)
sinks=['vector-assoc!','gn-put','gn-gs','vw-write','vw-cs','vw-fs','vw-bs','vw-vset']
inventory=[]
for name in sorted(seen):
 a,b,t=definitions[name];calls=[x for x in sinks if re.search(r'\('+re.escape(x)+r'\s',t)]
 if calls:inventory.append({'function':name,'lineStart':kernel.count('\n',0,a)+1,'sourceSHA256':hashlib.sha256(t.encode()).hexdigest(),'writePrimitives':calls,'body':t})
save(D/'write-role-inventory.json',{'status':'STATIC_QUERY_CLOSURE_WRITE_SITE_INVENTORY_OUTPUT_ROLE_NOT_CLOSED','root':'cq-original-query','closureFunctions':sorted(seen),'writeSites':inventory,'semanticRoles':[{'role':'summary/certificate controls9..14','writers':['vw-ret','vw-reset-flow','vw-run-fn'],'captured':True},{'role':'subject VW16 and FN16 fields including support/poison','writers':['vw-width-store','vw-run-fn','vw-arg-bound'],'capturedSubject':True,'allTargetsCaptured':False},{'role':'ordered outgoing per-site four contributions and exact call arity','writers':['vw-memo-reset','vw-memo-capture'],'captured':True},{'role':'caller aggregate target bounds fields6..9','writers':['vw-arg-bound','vw-memo-replay'],'capturedSubjectOnly':True,'completeTransitionCaptured':False},{'role':'existing memo validity and saved fourbounds','writers':['vw-memo-valid-store','vw-memo-key-save'],'capturedValidity':True,'savedKeyNotNewResult':True},{'role':'certificate bank','writer':'vw-read-certificate','mode2Guard':True,'queryIntendedMode':1,'capturedWholeBank':False},{'role':'work/status/control and scratch CFG/current/blockbank','writers':['vw-tick','vw-zero-work','vw-reset-flow','vw-merge-slot','vw-flow'],'recordedWorkStatus':True,'completeEffectsCaptured':False}],'outputRoleClosed':False,'readClosureQualified':False,'reapplicationQualified':False})
save(D/'request-key-contract.json',{'status':'SOURCE_INPUT_CONTEXT_CONTRACT_PENDING_READ_ROLE_CLOSURE','typedContext':['exact analyzer source/rules','ABI target architecture','memory geometry','opcode/runtime semantics','feature flags','original source/declaration/module scope','literal bytes','codec schema'],'dynamicInputRoles':['target/mode/candidate','complete subject and relevant dependency FREC/SIR/labels','fourbounds','incoming aggregates','memo validity/stored keys','all status/control/scratch prestate actually read','remaining workbudget/trap/diagnostics','generationbase and vectorcount'],'sealPolicy':'Once per immutable activation context, verify subsequent writes; not implemented in this output-only pilot','localKeyPolicy':'Strict structural interned tokens including dynamic/budget roles; hash only persistence; not implemented/qualified','exclusionsApproved':[],'fullDefCIDBridge':False,'fullComputeCIDQualified':False,'fullResultCIDQualified':False,'newQuerySkips':0,'C2':False})
save(D/'capture-schema.json',{'status':'DECLARED_OUTPUT_PROJECTION_SCHEMA/v1','additionalTags':{'CR-RESULT':['f','status','support','poison','memo-valid','control9','control10','control11','control12','control13','control14'],'CR-WVF':['f','index0..15','value'],'CR-FNF':['f','index0..15','value'],'CR-EDGE':['caller','ordinal','site','target','base','arity','opcode','IF-A','IF-B','IF-C','contribution0','contribution1','contribution2','contribution3'],'CR-EDGE-INVALID':['caller','ordinal','invalidsite'],'CR-END':['f','supportBefore','poisonBefore','supportedDomain','edgeRecordCount']},'ordering':'CQ-EXIT then CR-RESULT then16paired WVF/FNF then each CQ-EDGE+CR-EDGE then CR-END','arityProof':'OP-CALL13,IFA==target,IFB==base,IFC==arity; source-bound vw-memo-find already checks these fields','completeProjectionNotFullResult':True,'supportDropPoisonErrorIncompleteExcluded':True,'nativeCalls':0})
for filename in ('artifact.py','census.py','origin-pins.json'):(D/filename).write_bytes((B/filename).read_bytes())
base=(B/'run40.py').read_text();tree=ast.parse(base);lines=base.splitlines(keepends=True);starts=[];n=0
for line in lines:starts.append(n);n+=len(line)
edits=[]
for node in ast.walk(tree):
 if isinstance(node,ast.Constant)and type(node.value)is int and node.value in (40,19):edits.append((starts[node.lineno-1]+node.col_offset,starts[node.end_lineno-1]+node.end_col_offset,str(6 if node.value==40 else 2)))
driver=base
for a,b,t in sorted(edits,reverse=True):driver=driver[:a]+t+driver[b:]
driver=driver.replace("from census import parse","from census import parse\nfrom decode import parse as parse_output")
driver=driver.replace("preregistration.json","pilot-preregistration.json").replace('unity-census.kotoba','unity-result.kotoba').replace('40hardcap','6hardcap').replace('exact40/19','exact6/2').replace('PASS_ACTUAL_CURRENT19_QUERY_FREQUENCY40_BYTE_IDENTITY_ONLY','PASS_ACTUAL_DECLARED_OUTPUT_ROLE_CRC32_SLRE_PILOT6_BYTE_IDENTITY_ONLY')
needle="need(qualification['activations'],'genuine analysis activation records');"
assert driver.count(needle)==1
driver=driver.replace(needle,needle+"qualification['declaredOutput']=parse_output((p/(str(len(rows)-1)+'.stdout')).read_bytes());need(qualification['declaredOutput']['calls']==qualification['queryCalls'],'complete output query count');")
driver=driver.replace("'fullComputeCIDQualified':False,'newQuerySkips':0","'fullComputeCIDQualified':False,'fullResultCIDQualified':False,'outputRoleClosed':False,'original19Qualified':False,'newQuerySkips':0")
ast.parse(driver);(D/'run6.py').write_text(driver)
save(D/'driver-authoring.json',{'status':'SOURCE_ONLY_PILOT_DRIVER_ADAPTATION','baseDriver':pin(B/'run40.py'),'constantASTChanges':len(edits),'sequence':'observer2 then exactcrc32/slre2each; maximum6','guards':'freshnamespace,2specificSOURCEreceipts,rootGO,original763inputclosure,cleanliteralenv,raw17counters,64MiBstdout1MiBstderr,RLIMIT,1810wall,groupkill/reap,firstFAILnoRetry,wholeoldcontainer/native/export identity','baselineParserRetained':True,'additionalStrictProjectionDecoder':True,'nativeCalls':0,'SSHCalls':0,'driverExecuted':False})
save(D/'README.json',{'status':'SOURCE_ONLY_DECLARED_OUTPUT_ROLE_PILOT6_PENDING_TWO_REVIEWS_ROOT_GO','scope':'Observer implements arity+summary/FREC closure for a declared projection; complete semantic writes/readclosure/effects not qualified','implementation':'Kotoba unified/kernel observer implemented; Python source-authoring and offline controls are harness only','prototypeContextKeyOnlyContract':True,'noNewCacheOrSkips':True,'baselineOnce':True,'nativeCalls':0,'SSHCalls':0,'C2':False})
print('Source inventory/schema/pilot driver prepared, unexecuted')
