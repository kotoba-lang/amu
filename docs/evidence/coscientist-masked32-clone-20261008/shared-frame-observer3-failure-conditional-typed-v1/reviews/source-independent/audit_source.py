from pathlib import Path
import hashlib,json,stat,sys,importlib.util,difflib,re
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'shared-frame-currenttyped-observer3-source-v1-20261009';R=Path(__file__).parent
h=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def ck(p,v):assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink();b=p.read_bytes();assert len(b)==v['bytes']and h(b)==v['sha256'];return b
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());fr=json.loads((D/'freeze.json').read_bytes());pr=json.loads((D/'preregistration.json').read_bytes())
assert rec(D/'source-pins.json')['sha256']==fr['sourcePinsSHA256']=='3cadbd6ade753cb48a6ff808d4fd0174aaa08b6e0a75569732850af5fc007fd9';assert rec(D/'input-pins.json')['sha256']==fr['inputPinsSHA256']==pr['inputPinsSHA256']=='43404f19b567cec6e8e6c88e3d5f920cd1abed401b5d07692243582f0acd04c9'
for k,v in sp.items():ck(D/k,v)
for k,v in ip.items():ck(Path(k),v)
assert len(sp)==23 and len(ip)==2841 and sum(v['bytes']for v in ip.values())==449385544
for n,k in [('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert rec(D/n)['sha256']==fr[k]
off=(D/'ordinary-current16.kotoba').read_text();obs=(D/'observer-current16.kotoba').read_text();helper=(D/'observer-helpers.kotoba').read_text();delta=json.loads((D/'instrumentation-delta.json').read_bytes());bare=obs.replace(helper+'\n','',1)
for a,b in [('newLoop','oldLoop'),('newDriver','oldDriver'),('newLayout','oldLayout')]:assert bare.count(delta[a])==1;bare=bare.replace(delta[a],delta[b],1)
assert bare==off and h(off.encode())=='94fe39401f5f0a1120b12b2d17bf000d14a54c9c68e1f8976b8b0ced8794f199'
assembly=json.loads(Path(pr['sourceAssembly']).read_bytes());parts=[Path(assembly['candidate41']['path']if n=='seed/41-a64gen.kotoba'else v['path']).read_bytes()+b'\n'for n,v in zip(assembly['modules'],assembly['modulePins'])];assert len(parts)==16 and b''.join(parts)==off.encode()
# Only mutation operations in helper target separately allocated Q; snapshots do not write M.
assert not re.search(r'\((?:vector-assoc!?|gn-gs|gn-put) M\b',helper)
assert helper.count('(gn-run M)')==2 and '(ly-run M)'in helper and delta['newLoop'].count('(gn-ins M i op)')==1
assert 'sr-run M' in delta['newDriver'] and 'sr-layout M' in delta['newLayout']
prev=W/'tc-published-x16-current-observer-source-v2-20261009';equal=[]
for n in ['capture.py','integration.py','controller.py','typed-adapter.py','artifact_admission.py','runtime.py']:
 assert (D/n).read_bytes()==(prev/n).read_bytes();equal.append({'name':n,**rec(D/n)})
# Native call is reused exactly except three-call guard and specialized parser module.
x=(D/'native-call.py').read_text();y=(prev/'native-call.py').read_text();(R/'transport-delta.patch').write_text(''.join(difflib.unified_diff(y.splitlines(True),x.splitlines(True))))
assert x.replace('len(rows)<3','len(rows)<4')==y
f=json.loads(ck(Path(pr['qualifiedIntegrationFixtureProof']['path']),pr['qualifiedIntegrationFixtureProof']))
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert f[k]==sp[n]['sha256']
proof=json.loads(ck(Path(pr['currentProducerProof']['path']),pr['currentProducerProof']));assert proof['status']=='PASS_INDEPENDENT_ACTUAL_TC_JOINED_ORIGINAL19_ARTIFACT_IDENTITY_G1_G2_G3_MEMORY_PARTIAL_ONLY'and proof['G0G1G2G3WholeNativeEqual']and proof['G0G1G2G3WholeContainerEqual']
assert Path(pr['producer']).read_bytes()==Path(pr['candidateContainer']).read_bytes().split(b'\n\n',1)[1]and h(Path(pr['producer']).read_bytes())=='5cda246fec1d653b5ff044a56491069874f7a0b58da87785887c369573ccec8c'
assert len(pr['cases'])==pr['maximumLoaderCalls']==3 and len(pr['environment'])==17 and pr['maximumConservativeChildStarts']==9 and not pr['runtimeGuestAuthorized']and not pr['timingAuthorized']and not pr['C2']
O=Path(pr['freshOutputRoot']);assert O==D/'run-outputs'and not O.exists()
cs=pr['cases'];assert [c['label']for c in cs]==['G1-compile','G1-extract','nsichneu-compile']
for c in cs:
 a=c['nativeArgv'];assert a[:1]==[pr['loader']]and a[2:7]==['0','0','aarch64','35,37,38,39','--']and a[-1]==c['outputPath']and Path(c['outputPath']).parent==O
 assert c['kind']in ['compile','extract']
 if c['kind']=='compile':assert a[7]=='compile'and a[9:]==['--target','aarch64-macos','--output',c['outputPath']]
 else:assert a[7]=='extract-native'and a[9:]==['--symbol','main','--output',c['outputPath']]
assert cs[0]['nativeArgv'][1]==cs[1]['nativeArgv'][1]==pr['producer']and cs[2]['nativeArgv'][1]==str(O/'G1.bin')
assert cs[0]['nativeArgv'][8]==str(O/'observer-current16.kotoba')and cs[1]['nativeArgv'][8]==str(O/'G1.kseed')and cs[2]['nativeArgv'][8]==str(O/'nsichneu.kotoba')
assert (D/'nsichneu.kotoba').read_bytes()==Path(pr['entries'][0]['source']['path']).read_bytes()and cs[2]['expectedFNCount']==265
# Pure parser controls only; modules imported have no operational initialization.
sys.path.insert(0,str(D));spec=importlib.util.spec_from_file_location('inert_synthetic_source_controls',D/'source-controls.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);controls=mod.controls();assert controls==json.loads((D/'source-controls.json').read_bytes())and len(controls['negativeControls'])==23
# Key-names-only runtime metadata admission, no actual os.environ or limit calls.
spec=importlib.util.spec_from_file_location('inert_wrapper',D/'launch-wrapper.py');wrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(wrap)
for e in [dict(pr['environment']),dict(pr['environment'],__CF_USER_TEXT_ENCODING='opaque')]:assert wrap.environment_admission(pr['environment'],e)['nativeExecKeyNames']==sorted(pr['environment'])
for k in ['missing','changed','extra']:
 e=dict(pr['environment'])
 if k=='missing':e.pop('LANG')
 elif k=='changed':e['LANG']='C-invalid'
 else:e['UNKNOWN']='opaque'
 try:wrap.environment_admission(pr['environment'],e)
 except AssertionError:pass
 else:raise AssertionError('bad env accepted')
# Source law worst-case signed decimal rows: each module term covers all dump phases;1MiB reserve bounds selected events/snapshots.
assert '(= (vector-at M MM-LIT-N) 1)'in helper and '1048576) 8388608)'in helper
r={'status':pr['sourceReviewStatus'],'independent':True,'priorImplementationAuthorship':False,'sourcePinsSHA256':fr['sourcePinsSHA256'],'inputPinsSHA256':fr['inputPinsSHA256'],'driverSHA256':fr['driverSHA256'],'preregistrationSHA256':fr['preregistrationSHA256'],'freeze':rec(D/'freeze.json'),'sourceRegistry':{'files':23,'logicalBytes':sum(v['bytes']for v in sp.values())},'inputRegistry':{'files':2841,'logicalBytes':449385544},'exact16AssemblyAndReverseInstrumentation':True,'originalGenerationLayoutOnce':True,'readOnlyMSeparateSelectionQ':True,'currentProducerProof':pr['currentProducerProof'],'fixtureProof':pr['qualifiedIntegrationFixtureProof'],'reusedComponents':equal,'transportDelta':rec(R/'transport-delta.patch'),'cases':cs,'environmentSuppliedKeys':sorted(pr['environment']),'pureSyntheticControls':controls,'environmentControls':{'positive':2,'negative':3},'verifiedGates':['Exact3 arity0 compiler CLI argv and sole-main0 whole producer container; currentTC5cda/G1observer lineage, no targetguest.','Freshoutput exactGO keys/two distinct specific review receipts/input and generated seals guarded before each child; fixed3 noRetry, completion only after durable closed terminal/finalguard.','V4tested capture/FileIO integration/controller6a78+typed sampler+artifactgap policy byteexact; directwait retirement and bounded raw/resource/sample journals unchanged.','Named FSIZE64MiB CPU1800/hard1801,17nativeenv optionalCF only at Python admission, explicit originalenvexec. Soft4GiB sampled footprint/max2ownedmembers,1810deadline/reap30 remains qualified only as finite observations.','Non-name first-root exact12-chain selection;24edges/<=256ownedSIR/<=15owner+boundary fits16; cycles/short/role/budget mismatch zero. Complete module inventories are identity-only.','Complete ordered prefrontend/postemit/postlayout FN/NODE/TOK/SYM/SIR/CODE/FIX/LABEL/EXP; allword projection/exactrelocation/export relation and whole ordinarynsichneu container equality. No literalpool or partialoutput admission.','Frame/local/temp snapshots bounded16 and actual visit/skip/call ownership enforced. Generic BL/B classified by actual fixup/opcode; specialized/unclassified retained honestly.'],'limits':['SOURCE compiler types/syntax and current real selected region are still prospective;23mutants/positive/zero are synthetic only.','This gate observes structure and artifactidentity; shared-frame rewrite is absent. Privateentry/dominance/home relocation/callee-save/SLallocation/stacktrap/fuel/vector/17arena equivalence remain pending.','Observer IO/vector allocations change compiler resources; no compilerarena equivalence.','CurrentFNexpected265 is own ordinaryTCsource; historicalstage6 bodies/270SIR are not operative.','No targetguest/full19performance/C-or-better/hardpeak/CID cache effects. Source samplerpolicy eligible gaps remain explicit; unbound/unknown failures refuse.'],'operations':{'nativeThreadFDPipeProcessGroupSetterNetworkCalls':0,'productOrFrozenSubjectWrites':0}}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
