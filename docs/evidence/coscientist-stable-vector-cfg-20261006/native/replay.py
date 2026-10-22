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
seed='eab3a7c26eac2fdf32a3d4736fd8dd1c159b811a6dc6b5ef0f69c1d44b798406';assert {sha(I/f'seed-{g}.bin') for g in [2,3,4]}=={seed};assert sha(P/'baseline/seed-0.bin')=='f00e38312ac7278b1b597207054cba521fafa28f30f03d20d237a07fd59647e2'
ss=I/'source-snapshot';parts=[s.strip() for s in (ss/'seed/MANIFEST').read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')];assert '\n'.join((I/'41-a64gen-prototype.kotoba' if x=='seed/41-a64gen.kotoba' else ss/x).read_text() for x in parts)==(I/'unity.kotoba').read_text()
# Actual normalized machine proofs and packet mutants recomputed using only retained code/logs.
originalMachine=load(I/'machine-audit.json');q=subprocess.run([sys.executable,str(I/'machine-audit-portable.py')],capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);assert load(I/'machine-audit.json')==originalMachine
for fname,script in [('oracle.json','oracle-portable.py'),('allpred.json','allpred-portable.py')]:
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

def run(script):
 q=subprocess.run([sys.executable,str(script)],capture_output=True,text=True);assert q.returncode==0,(str(script),q.stdout[-1000:],q.stderr[-2000:]);return q
run(P/'cfg-model/replay.py')
before=load(I/'admission-audit.json');run(I/'admission-audit-portable.py');after=load(I/'admission-audit.json');assert before['rows']==after['rows'] and after['nativeProofFunctions']==7 and sorted(r['originVisits'] for r in after['rows'] if r['nativeAccepted'])==[47,69]
s=load(T/'semantic.json');assert len(s['rows'])==432 and len(s['publicRows'])==144
for row in s['rows']+s['publicRows']:assert row['candidate']=={k:row['baseline'][k] for k in ['exit','stdout','stderr']}
run(T/'meaning.py');assert len(load(T/'meaning.json')['checks'])==72
for filename,count in [('resource-states.json',161),('fuel-states.json',209)]:
 j=load(R/filename);assert len(j['rows'])==count
 for row in j['rows']:assert row['product']==row['candidate']
callee=load(R/'callee-proof.json');assert callee['pairs']==8 and callee['actualMachineMutantsDetected']==4
for row in callee['rows']:assert row['direct']==row['sentinels']
for row in load(R/'frame-native-proof.json')['rows']:assert row['detected'] and row['candidate']!=row['frame-mutant']
regen=load(R/'regeneration-proof.json');assert len(regen['rows'])==4
for row in regen['rows']:
 d=R/row['variant'];assert sha(d/'probe.bin')==row['sha256'];actual={x.split()[0]:int(x.split()[1]) for x in (d/'stdout').read_text().splitlines() if len(x.split())==2};assert actual==row['observations']
for row in regen['rows'][1:]:assert row['detected']
# Independent bounded frame arithmetic recalculation.
n=0;gap=[]
for old in range(8):
 for homes in range(4097):
  nnew=old+3;frame=((8*(homes+2)+15)//16)*16+((8*nnew+15)//16)*16
  if frame>32768:continue
  lowest=frame-8*(homes+2);saved=8*nnew;assert lowest>=saved and 18+nnew<=28;n+=1;gap.append(lowest-saved)
assert n==32704==load(R/'frame-arithmetic.json')['combinations'] and min(gap)==load(R/'frame-arithmetic.json')['minHomeSaveGap']
pred=load(T/'native-predicate.json');assert len(pred['controls'])==10 and len(pred['mutants'])==2
for row in pred['controls']:assert row['actual']['exit']==0 and int(re.search(r':result (-?\d+)',row['actual']['stdout'])[1])==row['expected']
for row in pred['mutants']:assert row['detected'] and row['baseline']['stdout']!=row['mutant']['stdout']
fault=load(T/'runtime-fault.json');assert fault['mutant']!={k:fault['baseline'][k] for k in ['exit','stdout','stderr']};raw=(T/'framed-diamond/candidate.bin').read_bytes();bad=(T/'flag-init-valid.bin').read_bytes();site=fault['wordSite']*4;assert raw[:site]==bad[:site] and raw[site+4:]==bad[site+4:] and struct.unpack_from('<I',raw,site)[0]==fault['before'] and struct.unpack_from('<I',bad,site)[0]==fault['after']
# Actual native primary helper/source mutant results retained; never execute target binaries.
pc=load(I/'proof-controls/report.json');assert len(pc['rows'])==7
pristine=pc['rows'][0]['outcomes'];assert len(pristine)==8
for row in pc['rows']:
 d=I/'proof-controls'/row['variant'];assert sha(d/'native.bin')==row['nativeSha256']
 for k,v in enumerate(row['outcomes']):assert int(re.search(r':result (-?\d+)',(d/f'case-{k}.stdout').read_text())[1])==v
for row in pc['rows'][1:]:assert row['outcomes']!=pristine and row['status']=='MUTATION DETECTED'
# Concrete read guards and observer bytes/offset parity recomputed.
ad=load(T/'allpred.json')['rows'];guards=0
for row in load(T/'emit-check.json')['rows']:
 name=row['case'];d=T/name;assert (d/'candidate-observer.bin').read_bytes()==(d/'candidate.bin').read_bytes();assert int((d/'candidate.offset').read_text())==int(re.search(r':offset (\d+)',(d/'candidate-observer-extract.log').read_text())[1]);assert [r['function'] for r in ad if r['case']==name and r['prospectiveAdmitted']]==[e[0] for e in row['actualAdmit']]
 raw=(d/'candidate.bin').read_bytes();words=struct.unpack('<'+'I'*(len(raw)//4),raw[:len(raw)//4*4])
 for ck in row['machineChecks']:
  length,base,flag=ck['cacheRegs']
  for i in ck['actualGuardSitesWords']:assert words[i]==0xb5000000|(13<<5)|flag and words[i+12]==0xd2800000|32|flag and words[i+14]==0x54000043 and words[i+15]==0;guards+=1
law=load(F/'read-law.json');assert law['status'].startswith('PASS') and not law['TLCorTLAPSExecuted']
for x in law['checks']:assert x['status'] in ['sat','unsat'] and (F/(x['name']+'.smt2')).exists()
assert load(F/'source-fixedpoint.json')['status'].startswith('PASS') and load(F/'bootstrap-boundary-proof.json')['status'].startswith('PASS')
boot=load(F/'bootstrap-boundary-proof.json');assert sha(F/'bootstrap-boundary-before.log')==boot['beforeSha256']==boot['afterSha256']==sha(F/'bootstrap-boundary-after.log')
out={'status':'PASS portable extracted offline CFG native proof replay','pinnedFiles':len(pins),'fixtures':593,'retainedNativeObservations':25658,'historicalFixturePrefix':508,'historicalRunsPrefix':14523,'original19Matrix':95,'original19Fuel1':19,'constructorNativeFullStatePairs':576,'constructorMeaningCases':72,'constructorNativePredicateControls':10,'constructorActualSourceOrMachineFaults':3,'primaryNativePredicateExecutionsRetained':56,'primaryPredicateSourceFaultsRetained':6,'original19NativeAdmissionDecisions':7,'acceptedSharedOriginVisits':[69,47],'resourcePairs':161,'fuelPairs':209,'calleeSentinelPairs':8,'frameArithmeticCombinations':32704,'normalizedMachineAuditRecomputed':True,'machineFaultsRecomputed':12,'independentConstructorAndOriginal19CFGModelsRecomputed':True,'nativeSeedSha256':seed,'freshNativeExecutions':0,'freshSolverExecutions':0,'timingExcluded':True,'copiedBaselineOracleExplicit':True,'productPromoted':False,'performanceClaim':False,'limitations':['Retained actual outputs and finite models only, not universal compiler proof.','Recorded SMT status verified; solver not rerun.','Frame expansion omission was not detected by sample guest results; physical invariant detected it.','No OS stack ceiling or concurrency equivalence claim.']}
(E/'replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
