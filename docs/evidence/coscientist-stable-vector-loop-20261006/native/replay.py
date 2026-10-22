"""Portable offline validation of retained actual native observations, never executes guest binaries."""
from pathlib import Path
import json,hashlib,tarfile,tempfile,re,sys,subprocess,struct
E=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((E/'archive-manifest.json').read_text());assert sha(E/'native-proof.tgz')==manifest['native-proof.tgz']['sha256'] and (E/'native-proof.tgz').stat().st_size==manifest['native-proof.tgz']['bytes']
root=Path(tempfile.mkdtemp(prefix='amu-stable-vector-offline-'))
with tarfile.open(E/'native-proof.tgz') as t:t.extractall(root,filter='data')
P=root/'stable-vector-proof';I=P/'implementation';T=P/'team-constructor';R=P/'team-resource';F=P/'root-proof';load=lambda p:json.loads(p.read_text())
assert sha(P/'payload-pins.json')==manifest['payload-pins.json']['sha256'];pins=load(P/'payload-pins.json')
for name,v in pins.items():assert sha(P/name)==v['sha256'] and (P/name).stat().st_size==v['bytes'],name
for name,h in load(I/'source-pins.json').items():assert sha(I/name)==h
seed='cb83290d6d6ef471570adac42c891be0e084d836697a56f26617b026f2145769';assert {sha(I/f'seed-{g}.bin') for g in [2,3,4]}=={seed};assert sha(P/'baseline/seed-0.bin')=='f00e38312ac7278b1b597207054cba521fafa28f30f03d20d237a07fd59647e2'
ss=I/'source-snapshot';parts=[s.strip() for s in (ss/'seed/MANIFEST').read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')];assert '\n'.join((I/'41-a64gen-prototype.kotoba' if x=='seed/41-a64gen.kotoba' else ss/x).read_text() for x in parts)==(I/'unity.kotoba').read_text()
# Actual normalized machine proofs and packet mutants recomputed using only retained code/logs.
originalMachine=load(I/'machine-audit.json');q=subprocess.run([sys.executable,str(I/'machine-audit-portable.py')],capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);assert load(I/'machine-audit.json')==originalMachine
for fname,script in [('oracle.json','oracle-portable.py'),('admission.json','admission-portable.py')]:
 before=load(T/fname);q=subprocess.run([sys.executable,str(T/script)],capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);assert load(T/fname)==before
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
# Retained exact native semantic/resource reports; no new guest executions.
s=load(T/'semantic.json');assert len(s['rows'])==s['ordinaryComparisons']==336 and len(s['publicRows'])==s['publicFirstReadComparisons']==112
for row in s['rows']+s['publicRows']:assert row['candidate']=={k:row['baseline'][k] for k in ['exit','stdout','stderr']}
for filename,count in [('resource-states.json',161),('fuel-states.json',209)]:
 j=load(R/filename);assert len(j['rows'])==count
 for row in j['rows']:assert row['product']==row['candidate']
assert load(R/'regeneration-proof.json')['rows'][0]['observations']['OPEN-CODE-EQUAL']==1 and load(R/'regeneration-proof.json')['rows'][0]['observations']['AGAIN-CODE-EQUAL']==1
assert all(x['detected'] for x in load(R/'regeneration-proof.json')['rows'][1:]);assert load(R/'callee-proof.json')['actualMachineMutantsDetected']==2
for row in load(R/'callee-proof.json')['rows']:assert row['direct']==row['sentinels']
m=load(T/'mutants.json');assert len(m['records'])==3
for row in m['records']:assert row['detected'] and row['mutantObservation']!={k:row['baseline'][k] for k in ['exit','stdout','stderr']}
assert next(x for x in m['records'] if x['case']=='two-vector')['baseline']['exit']!=0
abi=[json.loads(x) for x in (T/'callee-abi-proof.jsonl').read_text().splitlines()];assert abi[0]['result']==abi[1]['result']==abi[2]['result']==37 and abi[0]['fuel']==abi[1]['fuel']==abi[2]['fuel']==1048573 and abi[0]['calleePreserved'] and abi[1]['calleePreserved'] and not abi[2]['calleePreserved']
# Source mathematical oracle recomputed against the full-fuel retained observations.
q=subprocess.run([sys.executable,str(T/'meaning.py')],capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);assert len(load(T/'meaning.json')['checks'])==56
# Recompute candidate observer byte parity, admitted functions and each concrete guarded read/bounds/fresh-load skeleton.
ad=load(T/'admission.json')['rows'];guardCount=0
for row in load(T/'emit-check.json')['rows']:
 name=row['case'];p=T/name;assert (p/'candidate-observer.bin').read_bytes()==(p/'candidate.bin').read_bytes();expected=[r['function'] for r in ad if r['case']==name and r['structuralCandidateShape']];assert expected==row['expectedStructuralFunctions']==[x[0] for x in row['actualAdmit']]
 raw=(p/'candidate.bin').read_bytes();words=struct.unpack('<'+'I'*(len(raw)//4),raw[:len(raw)//4*4])
 for check in row['machineGuardChecks']:
  flag=check['cacheRegs'][2]
  for i in check['guardSitesWords']:
   assert words[i]==0xb5000000|(13<<5)|flag and words[i+12]==0xd2800000|(1<<5)|flag and words[i+14]==0x54000043 and words[i+15]==0;guardCount+=1
law=load(F/'read-law.json');assert law['status'].startswith('PASS') and not law['TLCorTLAPSExecuted'];assert all(x['status'] in ['sat','unsat'] and (F/(x['name']+'.smt2')).exists() for x in law['checks'])
out={'status':'PASS portable extracted offline actual-native proof replay','pinnedFiles':len(pins),'currentFixtures':593,'currentRetainedNativeObservationsChecked':25658,'historicalFixturePrefix':508,'historicalRunPrefix':14523,'fixedPointGenerations':[2,3,4],'candidateSeedSha256':seed,'original19MatrixObservations':nr,'original19Fuel1Reports':19,'fullNativeNormalizedMachineAuditRecomputed':True,'machinePacketMutantsRecomputed':len(originalMachine['controls']),'constructorMustCFGAndStructuralOracleRecomputed':True,'constructorMainFullStatePairs':448,'constructorAdditionalTwoVectorReferenceAndAbiEvidenceChecked':True,'retainedGuardedReadSkeletonsChecked':guardCount,'resourceFullStatePairs':161,'fuelPartialStatePairs':209,'regenerationAndCalleeMutantsChecked':True,'recordedSMTStatusesAndSourcesVerified':True,'freshSolverExecutions':0,'freshGuestNativeExecutions':0,'timingExcluded':True,'performanceClaim':False,'candidatePortsCorrectnessCopiedBaselineOnly':True,'productPromoted':False,'CGoalAchieved':False,'limitations':['Checks retained execution evidence; no new native or solver execution.','Final write-artifact bytes checked; intermediate filesystem history not recorded.','Runtime-native sample elapsed fields are incidental correctness outputs, not evaluated as benchmark results.','Finite proofs do not establish universal compiler, authority, concurrency or OS stack-limit equivalence.']}
(E/'replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
