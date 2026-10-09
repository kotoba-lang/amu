from pathlib import Path
import ast,json,hashlib,stat,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-original19-remaining10-fixedpoint-source-v4-20261009';O=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text());pr=json.loads((D/'preregistration.json').read_text())
for p,v in [(D/n,v)for n,v in sp.items()]+[(Path(p),v)for p,v in ip.items()]:
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==v['bytes'] and H(p)==v['sha256']
assert len(ip)==pr['exactInputFiles']==2810 and sum(v['bytes']for v in ip.values())==pr['exactInputLogicalBytes']==444443889
assert H(D/'input-pins.json')==pr['inputPinsSHA256'] and not (D/'run-outputs').exists()
for p in D.glob('*.py'):ast.parse(p.read_text())
a=json.loads(Path(pr['sourceAssembly']).read_text());parts=[]
for n,p in zip(a['modules'],a['modulePins']):parts.append(Path(a['candidate41']['path'] if n=='seed/41-a64gen.kotoba'else p['path']).read_bytes()+b'\n')
assert len(parts)==16 and b''.join(parts)==Path(pr['ownSource']).read_bytes();assert H(Path(pr['ownSource']))=='94fe39401f5f0a1120b12b2d17bf000d14a54c9c68e1f8976b8b0ced8794f199'
mat=json.loads(Path(pr['canonicalMatrix']).read_text());assert len(mat['entries'])==len(pr['entries'])==19
for m,e in zip(mat['entries'],pr['entries']):assert e['workload']==m['workload'] and e['iterations']==m['iterations'] and e['symbol']==m['symbol'] and e['source']['sha256']==m['expectedSourceSha256']
assert len(pr['cases'])==10 and len({tuple(c['nativeArgv'])for c in pr['cases']})==10
for i,c in enumerate(pr['cases']):
 assert c['nativeArgv'][2:7]==['0','0','aarch64','35,37,38,39','--']
 if i<6:assert c['nativeArgv'][1]==pr['producer']
 elif i<8:assert c['nativeArgv'][1]==str(D/'run-outputs/G1.bin')
 else:assert c['nativeArgv'][1]==str(D/'run-outputs/G2.bin')
 assert Path(c['outputPath']).parent==D/'run-outputs'
 assert c['kind']==('compile'if i%2==0 else'extract')
for k in ['capture.py','integration.py','controller.py']:assert (D/k).read_bytes()==(W/'crc-capture-popen-transfer-fixture-source-v3-20261009'/k).read_bytes()
spec=importlib.util.spec_from_file_location('root_inert_driver',D/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);payload,exports=m.container(Path(pr['candidateContainer']).read_bytes());assert payload==Path(pr['producer']).read_bytes() and exports==[('main',0,0)]
# Executable pure wrapper controls read fixed files and replace all admission Path/check APIs with injected maps.
t=ast.parse((D/'wrapper-controls.py').read_text());assert isinstance(t.body[-1],ast.Expr);t.body=t.body[:-1];ns={'__file__':str(D/'wrapper-controls.py'),'__name__':'root_source_model'};exec(compile(t,str(D/'wrapper-controls.py'),'exec'),ns);assert ns['dynamic']==2 and len(ns['neg'])==8
run=(D/'run.py').read_text();assert run.index("finally:save(O/'terminal.json'")<run.index("save(O/'report.json'");assert "need(g['C2'] is False"in run and "need(set(g)=="in run
t=ast.parse((D/'artifact-admission-controls.py').read_text());t.body=t.body[:-1];import sys;sys.path.insert(0,str(D));ns2={'__file__':str(D/'artifact-admission-controls.py'),'__name__':'root_source_model'};exec(compile(t,str(D/'artifact-admission-controls.py'),'exec'),ns2);assert len(ns2['mutants'])==15
rp=json.loads(Path(pr['retainedArtifactProof']['path']).read_text());assert rp['conditionalAhaArtifactIdentityOnly']['verified'] is True and rp['campaignQualified'] is False
suite=json.loads(Path(pr['retainedSuiteProof']['path']).read_text());manifest=json.loads(Path(pr['retainedImages']).read_text());expected=[dict(workload='aha-mont64',source=rp['conditionalAhaArtifactIdentityOnly']['originalSource'],container=rp['conditionalAhaArtifactIdentityOnly']['container'],native=rp['conditionalAhaArtifactIdentityOnly']['native'],exports=rp['conditionalAhaArtifactIdentityOnly']['exports'],selectedExport=rp['conditionalAhaArtifactIdentityOnly']['selectedExport'],wholePayloadEqual=True,admittedByCampaign=False,conditionalArtifactIdentityOnly=True)]+suite['freshSavedArtifactIdentityObservations'];assert manifest==expected and len(manifest)==17
for e,z in zip(pr['entries'][:17],manifest):
 payload,exports=m.container(Path(z['container']['path']).read_bytes());assert payload==Path(z['native']['path']).read_bytes() and [list(x)for x in exports]==z['exports'] and e['source']==z['source'] and e['workload']==z['workload']
assert manifest[-1]['workload']=='ud' and manifest[-1]['admittedByCampaign'] is False and suite['campaignQualified'] is False
q={'retainedWholePayloadABIChecks':17,'UDRefusalPreserved':True,'artifactAdmissionPurePositives':2,'artifactAdmissionNegativeMutants':15,'retainedAhaProofVerified':True,'strictPhysicalMemoryQualified':False,'status':pr['sourceReviewStatus'],'sourcePinsSHA256':H(D/'source-pins.json'),'driverSHA256':H(D/'run.py'),'preregistrationSHA256':H(D/'preregistration.json'),'sourceFiles':len(sp),'inputFiles':len(ip),'inputBytes':pr['exactInputLogicalBytes'],'fullSourceModules':16,'fullOriginalWorkloads':19,'fixedCommands':10,'wrapperModelPositives':3,'wrapperModelNegatives':8,'changedComponentsMatchActualFixtureSource':True,'validLastSourceOrderVerified':True,'nativeCalls':0,'operationalGO':False,'performanceQualified':False}
(O/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(q)
