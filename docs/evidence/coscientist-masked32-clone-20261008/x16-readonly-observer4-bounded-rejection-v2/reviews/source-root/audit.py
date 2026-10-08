from pathlib import Path
import json,hashlib,stat,ast,importlib.util,sys
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-published-x16-current-observer-source-v2-20261009';O=Path(__file__).resolve().parent;H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());pr=json.loads((D/'preregistration.json').read_bytes())
for p,z in [(D/n,z)for n,z in sp.items()]+[(Path(n),z)for n,z in ip.items()]:
 s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size==z['bytes']and H(p)==z['sha256']
assert len(sp)==25 and len(ip)==pr['exactInputFiles']==2819 and sum(z['bytes']for z in ip.values())==pr['exactInputLogicalBytes']==446728459
assert H(D/'input-pins.json')==pr['inputPinsSHA256']and not (D/'run-outputs').exists()
for p in D.glob('*.py'):ast.parse(p.read_text())
ordinary=(D/'ordinary-current16.kotoba').read_text();observer=(D/'observer-current16.kotoba').read_text();delta=json.loads((D/'instrumentation-delta.json').read_bytes());helpers=(D/'observer-helpers.kotoba').read_text();assert observer.count(helpers+'\n')==1 and observer.count(delta['newLoop'])==1 and observer.count(delta['newDriver'])==1
bare=observer.replace(helpers+'\n','',1);assert bare.replace(delta['newLoop'],delta['oldLoop'],1).replace(delta['newDriver'],delta['oldDriver'],1)==ordinary
assert delta['newLoop'].count('(gn-ins M i (gn-op M i))')==1 and helpers.count('(gn-run M)')==2 and '(if (not allowed)'in helpers
assembly=json.loads(Path(pr['sourceAssembly']).read_bytes());parts=[Path(assembly['candidate41']['path']if n=='seed/41-a64gen.kotoba'else z['path']).read_bytes()+b'\n'for n,z in zip(assembly['modules'],assembly['modulePins'])];assert len(parts)==16 and b''.join(parts)==ordinary.encode() and H(D/'ordinary-current16.kotoba')=='94fe39401f5f0a1120b12b2d17bf000d14a54c9c68e1f8976b8b0ced8794f199'
old=W/'tc-original19-remaining10-fixedpoint-source-v4-20261009'
for n in ['capture.py','integration.py','controller.py','artifact_admission.py','typed-adapter.py']:assert (D/n).read_bytes()==(old/n).read_bytes()
spec=importlib.util.spec_from_file_location('inert_x16_driver',D/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);payload,exports=m.container(Path(pr['candidateContainer']).read_bytes());assert payload==Path(pr['producer']).read_bytes()and exports==[('main',0,0)]
assert len(pr['cases'])==4
for i,c in enumerate(pr['cases']):assert c['nativeArgv'][1]==(pr['producer']if i<2 else str(D/'run-outputs/G1.bin'))and c['nativeArgv'][2:7]==['0','0','aarch64','35,37,38,39','--']and Path(c['outputPath']).parent==D/'run-outputs'
for c in pr['cases'][2:]:assert c['arity']==1 and Path(c['ordinaryContainer']).is_file()
sys.path.insert(0,str(D));tree=ast.parse((D/'source-controls.py').read_text());tree.body=tree.body[:-1];ns={'__file__':str(D/'source-controls.py'),'__name__':'root_source_model'};exec(compile(tree,str(D/'source-controls.py'),'exec'),ns);assert ns['positive']['eligiblePairs']==1 and len(ns['neg'])==16
run=(D/'run.py').read_text();assert run.index("finally:save(O/'terminal.json'")<run.index("save(O/'report.json'")and "g['C2']is False"in run
q={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':H(D/'source-pins.json'),'driverSHA256':H(D/'run.py'),'preregistrationSHA256':H(D/'preregistration.json'),'sourceFiles':25,'inputFiles':2819,'inputBytes':446728459,'pureSyntheticPatternPositive':1,'pureZeroPatternRejection':1,'negativeControls':16,'sourceReverseExact':True,'originalGnInsOnce':True,'wholeCurrent16Binding':True,'fixedCommands':4,'validLastVerified':True,'incomingTargetsDominanceRegisterProofPending':True,'patternIsNotRewriteProof':True,'initialConditionalGnRunLiteralAssumptionCorrected':True,'nativeCalls':0,'operationalGO':False};(O/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(q)
