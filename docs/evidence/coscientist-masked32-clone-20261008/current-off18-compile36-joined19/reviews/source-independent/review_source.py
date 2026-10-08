from pathlib import Path
import json,hashlib,stat,ast,sys,io,contextlib
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-current7618-off18-compile36-source-v1-20261009';B=W/'tc-original19-remaining10-fixedpoint-source-v4-20261009';R=Path(__file__).parent;h=lambda b:hashlib.sha256(b).hexdigest();pr=json.loads((D/'preregistration.json').read_bytes());regs={}
for n,rel in [('source-pins.json',True),('input-pins.json',False)]:
 x=json.loads((D/n).read_bytes());total=0
 for k,v in x.items():
  p=D/k if rel else Path(k);assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink();b=p.read_bytes();assert len(b)==v['bytes'] and h(b)==v['sha256'];total+=len(b)
 regs[n]={'files':len(x),'bytes':total,'sha256':h((D/n).read_bytes()),'allRegularNonSymlinkAndHashesExact':True}
assert regs['source-pins.json']['sha256']=='7663e9cd700585e24cc064b1bb95e052f7220aed1c05240e3a34b588fb692155' and regs['input-pins.json']['files']==2831 and regs['input-pins.json']['bytes']==452695483
for n in ['capture.py','integration.py','controller.py','typed-adapter.py','runtime.py','artifact_admission.py','compiler_output.py']:assert (D/n).read_bytes()==(B/n).read_bytes(),n
nc=(D/'native-call.py').read_text();old=(B/'native-call.py').read_text();assert nc.replace("len(rows)<36","len(rows)<10").replace('fixed ordered OFF18compile36 no retry','fixed ordered remaining10 no retry')==old
# Recompute static invocation matrix without running loader/wrapper.
mat=json.loads(Path(pr['canonicalMatrix']).read_bytes());assert len(pr['entries'])==len(mat['entries'])==19
expected=[]
for e,m in zip(pr['entries'],mat['entries']):
 assert (e['workload'],e['symbol'],e['iterations'],e['source']['sha256'])==(m['workload'],m['symbol'],m['iterations'],m['expectedSourceSha256'])
 if e['workload']=='crc32':continue
 n=e['workload'];out=Path(pr['freshOutputRoot']);prefix=[pr['loader'],pr['producer'],'0','0','aarch64','35,37,38,39','--'];expected.extend([(n+'-compile',prefix+['compile',str(out/(n+'.kotoba')),'--target','aarch64-macos','--output',str(out/(n+'.kseed'))]),(n+'-extract',prefix+['extract-native',str(out/(n+'.kseed')),'--symbol',e['symbol'],'--output',str(out/(n+'.bin'))])])
assert [(x['label'],x['nativeArgv']) for x in pr['cases']]==expected and len(set(tuple(x[1]) for x in expected))==36
ass=json.loads((D/'source-assembly.json').read_bytes());assert len(ass['modules'])==len(ass['modulePins'])==16;assert b''.join(Path(v['path']).read_bytes()+b'\n' for v in ass['modulePins'])==Path(pr['ownSource']).read_bytes();assert h(Path(pr['ownSource']).read_bytes())=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418';assert any(v['sha256']=='4ed9b5600505c33013c966d266a977a3d4ccd56ad3cdc425b1805acf390b95f3' for v in ass['modulePins'])
# Only inert parser definitions extracted from source; no operational main imported.
runAST=ast.parse((D/'run.py').read_text());ns={'re':__import__('re')}
exec(compile(ast.Module(body=[x for x in runAST.body if isinstance(x,ast.FunctionDef) and x.name in ['need','container']],type_ignores=[]),'inert_container','exec'),ns)
baseRaw=Path(pr['candidateContainer']).read_bytes();payload,ex=ns['container'](baseRaw);assert ex==[('main',0,0)] and payload==Path(pr['producer']).read_bytes() and h(payload)=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'
crc=pr['retainedCRC'];cp,cx=ns['container'](Path(crc['container']['path']).read_bytes());assert cp==Path(crc['native']['path']).read_bytes() and len(cp)==3640 and ('bench',1224,1) in cx
for n in ['baselineActualProof','TCActualProof','qualifiedIntegrationFixtureProof']:
 v=pr[n];b=Path(v['path']).read_bytes();assert len(b)==v['bytes'] and h(b)==v['sha256']
bp=json.loads(Path(pr['baselineActualProof']['path']).read_bytes());assert bp['currentProducerBindingQualified'] and bp['wholeBaselineNative']=={'bytes':len(payload),'sha256':h(payload)} and bp['benchOffset']==1224
# Reviewed fixed controls only call synthetic admit and fake filesystem; never main/setters/exec.
stream=io.StringIO()
with contextlib.redirect_stdout(stream):exec(compile((D/'wrapper-controls.py').read_bytes(),str(D/'wrapper-controls.py'),'exec'),{'__file__':str(D/'wrapper-controls.py'),'__name__':'pure_source_controls'})
controls=json.loads(stream.getvalue());assert controls['fixedUniqueCases']==36 and len(controls['negatives'])==8 and controls['operationalCalls']==0
(R/'recomputed-wrapper-controls.json').write_text(json.dumps(controls,indent=2)+'\n')
integ={};exec(compile((D/'integration.py').read_bytes(),'inert_integration','exec'),integ);t=ast.parse((D/'artifact_admission.py').read_text());an={k:integ[k] for k in ['classify_memory','MEMORY_POLICY']};exec(compile(ast.Module(body=[x for x in t.body if not isinstance(x,(ast.Import,ast.ImportFrom))],type_ignores=[]),'pure_artifact_admission','exec'),an)
actual=json.loads((B/'run-outputs/attempts.json').read_bytes());assert an['accept_artifact_observation'](actual[0]['controllerObservation']) and an['accept_artifact_observation'](actual[-1]['controllerObservation'])
ud=json.loads((W/'tc-original19-remaining42-fixedpoint-source-v3-20261009/run-outputs/attempts.json').read_bytes())[-1]['controllerObservation']
try:an['accept_artifact_observation'](ud)
except AssertionError:pass
else:raise AssertionError('unbound UD admitted')
code=(D/'run.py').read_text();assert code.index("finally:save(O/'terminal.json'")<code.index('durable closed terminal')<code.rindex("save(O/'report.json'");assert pr['maximumLoaderCalls']==36 and pr['maximumGuestWorkloadExecutions']==0 and len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='off';assert not Path(pr['freshOutputRoot']).exists()
r={'status':'PASS_SOURCE_ONLY_CURRENT7618_OFF18_COMPILE36_V1','independent':True,'priorAuthorshipOfSubject':False,'subject':str(D),'sourcePinsSHA256':regs['source-pins.json']['sha256'],'inputPinsSHA256':regs['input-pins.json']['sha256'],'driverSHA256':h((D/'run.py').read_bytes()),'preregistrationSHA256':h((D/'preregistration.json').read_bytes()),'freezeSHA256':h((D/'freeze.json').read_bytes()),'registries':regs,'verified':['Unmodified current16 baseline unity953f, current41 4ed9 and whole baseline native7618 solemain0 container; TC candidate not substituted.','All19 source/profile/symbol receipts canonical;18 excluding retainedCRC generate exactly36 unique fixed argv/capabilities35,37,38,39, no guest.','RetainedCRC native3640/container3724/fullpayload/bench1224 source and current actualbinding proof exact. TCadfb proof lineage only.','Qualified fixture capture/integration/controller and typed sampler/runtime/artifact-admission/compiler-output byte-identical accepted remaining10; native-call only raises fixed call count10to36.','Wrapper narrows to immutable current7618 only; no dynamic G1/G2 producer. Canonical interpreter/loader receipt, fullseal index/argv/source/output/GO checks;17env with onlyoptionalCF runtimeextra and original17 explicit exec.','Finite named FSIZE64MiB and CPU1800/1801 resource journal/readback, no AS; soft sampled4GiB metric only. Ownership lock/uncertainty retirement/watchdog-stop/one directwait/closed capture retained.','Synthetic wrapper1positive8negative recomputed; accepted saved strict/gap observations admitted but unbound UD refused by unchanged artifact policy.','Fresh namespace/no retry/first failure stops; durable terminal+finalguard precede completed artifact-only report, no runtime/performance/hardpeak claims.'],'pureControls':controls,'artifactPolicySavedControls':{'strictPositive':1,'typedBoundGapPositive':1,'unboundUDRefused':True},'limitations':['SOURCE admission only; no36execution or new artifact qualification.','Memory partial/soft finite sampling is not strict whole campaign hard-memory qualification.','Copied transport previous actual fixture scope remains finiteFileIO/injected authority, not universal OS schedule/childtrace.','No historicalOFFLC/currentC timing reused; future currentOFF/TC guest190 must separately bind savedC95 results.'],'reviewerOperations':{'nativeCompilerLoaderThreadFDPipeProcessNetworkSetterLibprocCalls':0,'frozenSubjectWrites':0}}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');b=(R/'report.json').read_bytes();print(len(b),h(b))
