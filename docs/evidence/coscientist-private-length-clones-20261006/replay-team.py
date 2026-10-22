from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,tempfile
E=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
a=E/'team-proof.tgz';assert sha(a)==load(E/'team-archive-manifest.json')['sha256']
with tempfile.TemporaryDirectory(prefix='amu-clone-team-replay-') as tmp:
 W=Path(tmp)
 with tarfile.open(a) as t:t.extractall(W,filter='data')
 pins=load(W/'team-pins.json')
 for n,h in pins['files'].items():assert sha(W/n)==h,n
 M=W/'team-machine';old=load(M/'audit.json')
 q=subprocess.run([sys.executable,str(M/'audit.py')],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 assert load(M/'audit.json')==old
 D=W/'team-constructor';report=load(D/'report.json');count=0
 for n in ['semantic.json','extra-semantic.json']:
  for z in load(D/n)['rows']:assert z['baseline']==z['candidate'];count+=1
 x=load(D/'public-entry.json');assert x['originalExportSafeFlags']==0
 for z in x['rows']:
  if z['label']=='baseline':
   v=next(v for v in x['rows'] if v['label']=='candidate' and v['handle']==z['handle'])
   assert {k:v for k,v in z.items() if k!='label'}=={k:v for k,v in v.items() if k!='label'};count+=1
 assert count==report['fullStateComparisons']==304
 ms=load(D/'mutants.json');mm=load(D/'merge-mutant.json')
 assert len(ms['records'])==2 and all(z['detected'] and z['baseline']!=z['mutant'] for z in ms['records'])
 assert mm['detected'] and mm['baseline']!=mm['mutant']
 D=W/'team-resource';report=load(D/'report.json');rs=load(D/'resource-states.json')
 assert len(rs['rows'])==report['fullStatePairs']==161 and all(z['product']==z['candidate'] for z in rs['rows'])
 assert sum(z['product']['exit']!=0 for z in rs['rows'])==46
 rest=load(D/'restoration.json')['rows'];assert rest[0]['accepted'] and rest[0]['observations']['CODE-EQUAL']==1
 assert all(z['detected'] and not z['accepted'] for z in rest[1:])
 assert all(rest[0]['observations'][n]==4102 for n in ['BAD-ORIGIN','BAD-COUNT','BAD-FNCOUNT','BAD-SITE','BAD-TARGET','BAD-NONCALL'])
 result={'status':'PASS extracted independent team proof replay','allArtifactPinsVerified':True,'all19ActualMachineAuditRecomputed':True,'deletedBounds':old['totals']['deletedBounds'],'provedSirDeletedBounds':old['totals']['provedSirDeletedBounds'],'machineCalibrationControls':len(old['controls']),'constructorFullStatePairs':304,'actualConstructorCompilerMutantsDetected':3,'resourceFullStatePairs':161,'resourceTraps':46,'actualRestorationCompilerMutantsDetected':2,'invalidUndoControls':6,'freshNativeExecutions':0,'performanceClaim':False,'productPromoted':False,'COrBetterAchieved':False}
 (E/'team-replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
