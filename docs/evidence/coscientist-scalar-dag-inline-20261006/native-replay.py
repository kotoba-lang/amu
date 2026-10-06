"""Offline retained-evidence replay; executes only Python proof analysis, no guests/solver/timing."""
from pathlib import Path
import json,hashlib,tarfile,tempfile,re,sys,subprocess,runpy
E=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text())
m=load(E/'archive-manifest.json');assert sha(E/'native-proof.tgz')==m['native-proof.tgz']['sha256']
root=Path(tempfile.mkdtemp(prefix='amu-scalar-dag-offline-'))
with tarfile.open(E/'native-proof.tgz') as t:t.extractall(root,filter='data')
P=root/'scalar-dag-proof';I=P/'implementation';T=P/'team-constructor';R=P/'team-resource';F=P/'root-proof';ss=I/'source-snapshot'
assert sha(P/'payload-pins.json')==m['payload-pins.json']['sha256'];pins=load(P/'payload-pins.json')
for name,v in pins.items():assert sha(P/name)==v['sha256'] and (P/name).stat().st_size==v['bytes'],name
for name,h in load(I/'source-pins.json').items():assert sha(I/name)==h
assert {sha(I/f'seed-{g}.bin') for g in [2,3,4]}=={'761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'}
assert sha(P/'baseline/seed-4.bin')=='eab3a7c26eac2fdf32a3d4736fd8dd1c159b811a6dc6b5ef0f69c1d44b798406'
parts=[p.strip() for p in (ss/'seed/MANIFEST').read_text().splitlines() if p.strip() and not p.lstrip().startswith('#')];assert '\n'.join((ss/p).read_text() for p in parts)==(I/'unity.kotoba').read_text()
assert (ss/'seed/41-a64gen.kotoba').read_bytes()==(I/'41-a64gen-prototype.kotoba').read_bytes()
def run(p):
 q=subprocess.run([sys.executable,str(p)],capture_output=True,text=True);assert q.returncode==0,(p,q.stdout[-800:],q.stderr[-1800:]);return q
before=load(I/'machine-audit.json');run(I/'machine-audit-portable.py');assert load(I/'machine-audit.json')==before
for script,out in [('source-oracle.py','source-meaning.json'),('admission-oracle.py','admission-oracle.json')]:
 before=load(T/out);run(T/script);assert load(T/out)==before
machine=runpy.run_path(str(I/'machine-audit-portable.py'));physical=[]
for row in load(T/'physical.json')['rows']:
 p=T/'physical'/row['case'];v=machine['audit'](machine['load'](p/'baseline'),machine['load'](p/'candidate'));assert json.loads(json.dumps(v))=={k:x for k,x in row.items() if k!='case'};physical.append(v)
assert sum(x['sites'] for x in physical)==266
before=load(P/'team-fixture-machine/report.json');run(P/'team-fixture-machine/audit-portable.py');assert load(P/'team-fixture-machine/report.json')==before
# Current fixture table reconstructed with immutable contract dependencies and historical prefix.
sys.path.insert(0,str(F));modules=[]
for name in ['permanent-a64gen-fixtures.py','original-permanent-a64gen-fixtures.py']:
 src=(F/name).read_text();needle="R = '/Users/junkawasaki/github/wt/amu-seed17'";assert src.count(needle)==1;src=src.replace(needle,'R = '+repr(str(ss)),1);ns={'__name__':'frozen_fixture_table','__file__':str(F/name)};exec(compile(src,str(F/name),'exec'),ns);modules.append(ns)
fx,old=modules;proof=load(F/'adoption-permanent-proof.json');assert fx['FIX'][:508]==old['FIX'] and fx['RUNS'][:14523]==old['RUNS'];assert len(fx['FIX'])==593 and len(fx['RUNS'])==len(proof['observations'])==25658;assert sha(F/'permanent-a64gen-fixtures.py')==proof['frozenGeneratorSha256']
fileExpect={}
for n,((name,args,expect,opts),row) in enumerate(zip(fx['RUNS'],proof['observations'])):
 assert row['index']==n and row['fixture']==name and row['args']==list(args) and row['expect']==expect
 so,se,exit=row['stdout'],row['stderr'],row['exit']
 if expect=='trap':good=exit!=0 and 'KEXE_TRAP' in se
 elif 'fuel_remaining' in opts:result=re.search(r':result (-?\d+)',so);good=exit==0 and result is not None and int(result[1])==expect
 elif 'cmd' in opts:good=exit==(expect&255)
 else:good=exit==0 and bool(so.splitlines()) and so.splitlines()[-1]==str(expect)
 if 'fuel_remaining' in opts:left=re.search(r':remaining (-?\d+)',so);good=good and left is not None and int(left[1])==opts['fuel_remaining']
 if 'stdout' in opts:good=good and so.startswith(opts['stdout'])
 if 'file' in opts:fileExpect[opts['file'][0]]=opts['file'][1]
 assert good,(n,name,expect,opts)
for name,data in fileExpect.items():assert (F/'adoption-permanent-run'/name).read_bytes()==data
blobs=[fx['blob_from']((F/f'adoption-permanent-{kind}.stdout').read_text()) for kind in ['test','real']];a,b=blobs;assert a[1]==b[1] and a[0][:len(b[0])]==b[0] and not any(a[0][len(b[0]):]) and 0<=len(a[0])-len(b[0])<=7;assert (F/'adoption-permanent-fixture.bin').read_bytes()==b[0];assert proof['realTestCodeAndLiteralBytesEqual'] and proof['realTestFnOffsetsEqual'] and not proof['committedGoldenChanged']
# Full original nineteen source/iteration matrix; incidental elapsed fields are never interpreted as performance.
baseline={x['workload']:x for x in load(P/'baseline/ports-correctness.json')['entries']};build={x['workload']:x for x in load(I/'ports-build.json')['entries']};ports=load(F/'ports-semantic.json');assert len(ports['entries'])==len(build)==19;nr=0
for e in ports['entries']:
 name=e['workload'];old=baseline[name];assert e['nativeSha256']==sha(I/'ports'/name/'native.bin')==build[name]['nativeSha256'];assert e['offset']==build[name]['offset'];assert e['sourceSha256']==old['sourceSha256'];assert e['iterations']==[x['n'] for x in e['runs']]
 for got,want in zip(e['runs'],old['runs']):
  assert (got['n'],got['result'],got['fuelConsumed'],got['exit'])==(want['n'],want['result'],want['fuelConsumed'],0)
  raw=load(F/'ports-semantic-raw'/name/f"n-{got['n']}.stdout");assert raw['result']==got['result'] and raw['contextFuelConsumed']==got['fuelConsumed'] and raw['contextFuelBefore']-raw['contextFuelAfter']==got['fuelConsumed'];nr+=1
 assert e['fuelTrapReturncode']==old['fuelTrapReturncode'];assert (F/'ports-semantic-raw'/name/'fuel1.stderr').exists()
assert nr==95==ports['matrixExecutions']

meaning={(r['case'],tuple(r['inputs'])):r for r in load(T/'source-meaning.json')['rows']};assert len(meaning)==150
for row in load(T/'semantic.json')['rows']:
 assert row['baseline']==row['candidate'];want=meaning[row['case'],tuple(row['inputs'])]
 if row['fuel']==1048576:
  actual=row['candidate'];assert bool(actual['exit'])==want['expectedTrap']
  if not want['expectedTrap']:assert int(re.search(r':result (-?\d+)',actual['stdout'])[1])==want['expectedResult'];assert actual['stdout'].startswith(want['expectedEffectTrace'])
for row in load(T/'public.json')['rows']:assert row['baseline']==row['candidate']
assert len(load(T/'semantic.json')['rows'])==750 and len(load(T/'public.json')['rows'])==60
faults=load(T/'faults.json')['rows'];assert len(faults)==3
for r in faults:
 assert r['detected']
 if 'mutant' in r:assert r['mutant']!=r['baseline']
 else:assert 'E4001' in (T/'faults/omit-caller-state-restore-target-compile.log').read_text()
for filename,count in [('resource-states.json',161),('fuel-states.json',209),('ordinary-states.json',57),('caller-proof.json',220)]:
 rows=load(R/filename)['rows'];assert len(rows)==count
 for row in rows:assert row['candidate']==row.get('product',row.get('baseline'))
for row in load(R/'callee-proof.json')['rows']:assert row['direct']==row['sentinels']
assert len(load(R/'callee-proof.json')['rows'])==10
budgetRows=[]
for p in sorted(R.glob('budget-*/stdout')):
 lines=p.read_text().splitlines();spans=[list(map(int,l.split()[1:])) for l in lines if l.startswith('SPAN ')];tot={l.split()[0]:int(l.split()[1]) for l in lines if l.split()[0] in ['USED','SITES','ERR']};used=sites=0
 for words,start,end,priorused,priorsites in spans:
  assert words==end-start and used==priorused and sites==priorsites
  if words<=64 and used+words<=4096 and sites<256:used+=words;sites+=1
 assert tot=={'USED':used,'SITES':sites,'ERR':0};budgetRows.append({'control':p.parent.name,'used':used,'sites':sites,'spans':len(spans)})
assert len(budgetRows)==7 and max(x['sites'] for x in budgetRows)==256
rest=load(R/'restoration-proof.json');assert rest['restoration']=={'CLOSED-SOURCE':1,'CLOSED-USED':64,'OPEN-SOURCE':1,'OPEN-USED':0,'OPEN-SITES':0,'AGAIN-SOURCE':1,'AGAIN-CODE':1,'AGAIN-USED':64,'ERR':0};assert rest['accountingFault']=={'reported':64,'physicalSpan':65,'wronglyAccepted':True,'detected':True}
raw={l.split()[0]:int(l.split()[1]) for l in (R/'restoration/stdout').read_text().splitlines() if not l.startswith('SPAN ')};assert raw==rest['restoration']
rawspan=next(l for l in (R/'undercount-fault/stdout').read_text().splitlines() if l.startswith('SPAN '));v=list(map(int,rawspan.split()[1:]));assert v[0]==64 and v[2]-v[1]==65
pred=load(I/'proof-controls/report.json');assert pred['nativeExecutions']==136 and len(pred['rows'])==8 and len(pred['rows'][0]['outcomes'])==17
assert pred['rows'][0]['outcomes']==[6]+[0]*15+[6]
for row in pred['rows']:
 assert sha(I/'proof-controls'/row['variant']/'native.bin')==row['nativeSha256']
 for n,value in enumerate(row['outcomes']):assert int(re.search(r':result (-?\d+)',(I/'proof-controls'/row['variant']/f'case-{n}.stdout').read_text())[1])==value
for row in pred['rows'][1:]:assert row['status']=='MUTATION DETECTED' and row['outcomes']!=pred['rows'][0]['outcomes']
ro=load(F/'readonly-regressions/report.json');assert len(ro['controls'])==117
for row in ro['controls']:
 if row['expected'] in ['trap',None]:assert row['exit']!=0 and 'KEXE_TRAP' in row['stderr']
 else:assert row['exit']==0 and int(re.search(r':result (-?\d+)',row['stdout'])[1])==row['expected']
 if 'expectedConsumed' in row and row['expectedConsumed'] is not None:
  fuel=re.search(r':initial (\d+) :remaining (\d+)',row['stdout']);assert int(fuel[1])-int(fuel[2])==row['expectedConsumed']
assert len(load(F/'capture-law.json')['queries'])==10
for query in load(F/'capture-law.json')['queries']:
 assert sha(F/(query['name']+'.smt2'))==query['smt2Sha256'] and query['status'] in ['sat','unsat']
 assert query['status']==('sat' if query['name'].startswith('unsafe-') else 'unsat')
result={'status':'PASS portable retained actual native evidence and recomputed source/DAG/machine/fixture/budget proofs','selectedPayloadFiles':len(pins),'original19MachineSites':132,'typedNativePairs':810,'typedMeaningCases':150,'typedMachineSites':266,'permanentFixtures':593,'permanentNativeObservations':25658,'readonlyObservations':117,'original19ResultFuelPairs':95,'original19Fuel1Controls':19,'resourcePairs':161,'fuelPrefixAndOrdinaryPairs':266,'newCallerPairs':220,'sentinels':10,'nativePredicateExecutionsRetained':136,'nativePredicateCases':17,'nativePredicateSourceFaults':7,'constructorSourceFaults':3,'budgetControls':budgetRows,'smtQueriesRetained':10,'freshSolverRuns':0,'freshNativeExecutions':0,'timingIncluded':False,'productPromoted':False,'limits':['Retained actual observations are rechecked; no new guest/solver execution.','Prospective SMT statuses retained only, not universal compiler proof.','Existing fixture golden still differs by justified7call expansions; original golden unchanged.','Archive is selected current proof closure, not complete owner pin sets or historical intermediate candidates.']}
(E/'replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
