from pathlib import Path
import ast,json,hashlib,stat,importlib.util,sys
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-current7618-off18-compile36-source-v1-20261009';O=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());pr=json.loads((D/'preregistration.json').read_bytes())
for p,v in [(D/n,v)for n,v in sp.items()]+[(Path(p),v)for p,v in ip.items()]:
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==v['bytes'] and H(p)==v['sha256']
assert len(ip)==pr['exactInputFiles']==2831 and sum(v['bytes']for v in ip.values())==pr['exactInputLogicalBytes']==452695483
assert H(D/'input-pins.json')==pr['inputPinsSHA256'] and not (D/'run-outputs').exists()
for p in D.glob('*.py'):ast.parse(p.read_text())
a=json.loads((D/'source-assembly.json').read_bytes());assert len(a['modulePins'])==16 and b''.join(Path(z['path']).read_bytes()+b'\n'for z in a['modulePins'])==Path(pr['ownSource']).read_bytes();assert H(Path(pr['ownSource']))=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418'
mat=json.loads(Path(pr['canonicalMatrix']).read_bytes());assert len(mat['entries'])==len(pr['entries'])==19
for e,m in zip(pr['entries'],mat['entries']):assert e['workload']==m['workload'] and e['source']['sha256']==m['expectedSourceSha256'] and e['symbol']==m['symbol'] and e['iterations']==m['iterations']
assert len(pr['cases'])==36 and len({tuple(c['nativeArgv'])for c in pr['cases']})==36
names=[e['workload']for e in pr['entries']if e['workload']!='crc32']
for i,c in enumerate(pr['cases']):assert c['nativeArgv'][1]==pr['producer'] and c['nativeArgv'][2:7]==['0','0','aarch64','35,37,38,39','--'] and c['label']==names[i//2]+('-compile'if i%2==0 else'-extract') and Path(c['outputPath']).parent==D/'run-outputs'
for n in ['capture.py','integration.py','controller.py','artifact_admission.py','typed-adapter.py']:assert (D/n).read_bytes()==(W/'tc-original19-remaining10-fixedpoint-source-v4-20261009'/n).read_bytes()
spec=importlib.util.spec_from_file_location('root_inert_driver',D/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);payload,exports=m.container(Path(pr['candidateContainer']).read_bytes());assert payload==Path(pr['producer']).read_bytes() and exports==[('main',0,0)] and H(Path(pr['producer']))=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'
b=json.loads(Path(pr['baselineActualProof']['path']).read_bytes());assert b['currentProducerBindingQualified'] is True and b['wholeBaselineNative']==ip[pr['producer']]
r=pr['retainedCRC'];payload,exports=m.container(Path(r['container']['path']).read_bytes());assert payload==Path(r['native']['path']).read_bytes() and ('bench',1224,1)in exports and b['wholeOriginalCRCNative']==ip[r['native']['path']]
t=ast.parse((D/'wrapper-controls.py').read_text());t.body=t.body[:-1];ns={'__file__':str(D/'wrapper-controls.py'),'__name__':'root_source_model'};exec(compile(t,str(D/'wrapper-controls.py'),'exec'),ns);assert len(ns['neg'])==8
sys.path.insert(0,str(D));from artifact_admission import accept_artifact_observation
old=json.loads((W/'tc-original19-fixedpoint-source-v2-20261009/run-outputs/attempts.json').read_bytes());assert accept_artifact_observation(old[0]['controllerObservation']) and accept_artifact_observation(old[1]['controllerObservation'])
ud=json.loads((W/'tc-original19-remaining42-fixedpoint-source-v3-20261009/run-outputs/attempts.json').read_bytes())[-1]['controllerObservation']
try:accept_artifact_observation(ud)
except AssertionError:pass
else:raise AssertionError('unbound UD admitted')
run=(D/'run.py').read_text();assert run.index("finally:save(O/'terminal.json'")<run.index("save(O/'report.json'");assert "need(g['C2']is False"in run or "need(g['C2'] is False"in run
q={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':H(D/'source-pins.json'),'driverSHA256':H(D/'run.py'),'preregistrationSHA256':H(D/'preregistration.json'),'sourceFiles':len(sp),'inputFiles':len(ip),'inputBytes':pr['exactInputLogicalBytes'],'fullSourceModules':16,'fullOriginalWorkloads':19,'freshWorkloads':18,'fixedCommands':36,'wrapperPurePositives':1,'wrapperPureNegatives':8,'retainedCRCWholePayloadVerified':True,'exactCurrentOFFProducerVerified':True,'unboundUDRemainsRefused':True,'validLastSourceOrderVerified':True,'nativeCalls':0,'operationalGO':False,'performanceQualified':False};(O/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(q)
