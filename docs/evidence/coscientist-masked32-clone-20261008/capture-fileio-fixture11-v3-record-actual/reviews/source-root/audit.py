from pathlib import Path
import ast,json,hashlib,stat,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-capture-popen-transfer-fixture-source-v3-20261009';V=W/'crc-capture-popen-transfer-fixture-source-v2-20261009';O=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text())
for p,v in [(D/n,v)for n,v in sp.items()]+[(Path(n),v)for n,v in ip.items()]:
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==v['bytes'] and H(p)==v['sha256']
for n in ['run.py','capture.py','integration.py']:assert (D/n).read_bytes()==(V/n).read_bytes()
a=ast.parse((D/'controller.py').read_text());b=ast.parse((V/'controller.py').read_text());replaced=0
for n in ast.walk(a):
 if isinstance(n,ast.Dict):
  for i,k in enumerate(n.keys):
   if isinstance(k,ast.Constant) and k.value=='memoryAdmissionRecord':
    assert isinstance(n.values[i],ast.Name)and n.values[i].id=='record';del n.keys[i];del n.values[i];replaced+=1;break
assert replaced==1 and ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
assert H(D/'controller.py')=='6a78a0ffeaa5183af9439ac6319b9e90b5f530c33c0353666ee118f13b0f4190'
# Pure injected SOURCE model only; no driver/native/FD/thread execution.
z=subprocess.run(['python3',str(D/'pure-observe16.py')],capture_output=True,check=True);q=json.loads(z.stdout);assert q==json.loads((D/'pure-observe16-results.json').read_text()) and len(q['controls'])==16
(O/'pure-results.json').write_bytes(z.stdout)
pr=json.loads((D/'preregistration.json').read_text());old=json.loads((V/'preregistration.json').read_text());assert pr['fixedArgv'][1]==str(D/'run.py') and pr['fixedSuppliedEnvironment']['TMPDIR']==str(D/'run-outputs');assert pr['maximumDriverLaunches']==1 and pr['noRetry'] is True and pr['rootOuterWallSeconds']==10 and pr['rootReapSeconds']==5
assert not (D/'run-outputs').exists()
r={'status':'PASS_SOURCE_ONLY_FIXED_FILEIO_CAPTURE_CONTROLLER_FIXTURE','sourcePinsSHA256':H(D/'source-pins.json'),'driverSHA256':H(D/'run.py'),'sourceFiles':len(sp),'inputFiles':len(ip),'inputBytes':sum(v['bytes']for v in ip.values()),'pureObserveControlsRecomputed':16,'actualFixtureRuns':0,'newControllerSHA256':H(D/'controller.py'),'controllerOnlyReturnRecordDelta':True,'operationalGO':False}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
