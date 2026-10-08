from pathlib import Path
import json,hashlib,stat,ast,re
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-original19-fixedpoint-source-v1-20261009';O=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def check(p,v):
 assert stat.S_ISREG(p.lstat().st_mode)and not p.is_symlink();b=p.read_bytes();assert len(b)==v['bytes']and sha(b)==v['sha256'],str(p)
f=json.loads((D/'freeze.json').read_text());sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text());pr=json.loads((D/'preregistration.json').read_text());a=json.loads((D/'source-assembly.json').read_text())
assert sha((D/'source-pins.json').read_bytes())=='df8cd519b1da94f915791b669e7eca1b9412a876e8235067215047da4149731e'
for n,v in sp.items():check(D/n,v)
for n,v in ip.items():check(Path(n),v)
assert len(sp)==16 and len(ip)==2560 and sum(v['bytes']for v in ip.values())==441662409
for p in D.glob('*.py'):ast.parse(p.read_text())
parts=[Path(a['candidate41']['path']if n=='seed/41-a64gen.kotoba'else v['path']).read_bytes()+b'\n'for n,v in zip(a['modules'],a['modulePins'])];assert len(parts)==16 and b''.join(parts)==(D/'unity-tc.kotoba').read_bytes()and sha(b''.join(parts))=='94fe39401f5f0a1120b12b2d17bf000d14a54c9c68e1f8976b8b0ced8794f199'
mat=json.loads(Path(pr['canonicalMatrix']).read_text());assert len(mat['entries'])==len(pr['entries'])==19
for e,m in zip(pr['entries'],mat['entries']):assert e['workload']==m['workload']and e['symbol']==m['symbol']and e['iterations']==m['iterations']and e['source']['sha256']==m['expectedSourceSha256']
assert len(pr['cases'])==pr['maximumLoaderCalls']==44 and len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='off'and pr['capabilities']=='35,37,38,39'and pr['strictSampledMemoryRequired']is True and pr['terminationGapAdmitted']is False
for i,e in enumerate(pr['entries']):
 assert [c['label']for c in pr['cases'][2*i:2*i+2]]==[e['workload']+'-compile',e['workload']+'-extract']
for i,c in enumerate(pr['cases']):
 assert c['nativeArgv'][:1]==[pr['loader']]and c['nativeArgv'][2:7]==['0','0','aarch64','35,37,38,39','--']and c['nativeArgv'][7]==('compile'if c['kind']=='compile'else'extract-native')
 assert c['nativeArgv'][1]==(pr['producer']if i<40 else str(Path(pr['freshOutputRoot'])/('G1.bin'if i<42 else'G2.bin')))
# Execute only isolated pure wrapper admission function; no module imports or main.
wr=ast.parse((D/'launch-wrapper.py').read_text());fn=next(x for x in wr.body if isinstance(x,ast.FunctionDef)and x.name=='allowed');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'pure-allowed','exec'),ns)
try:ns['allowed'](pr['cases'][0]['nativeArgv'],pr)
except KeyError as ex:assert ex.args==('orderedChildren',);firstFault=str(ex)
else:raise AssertionError('missing schema mismatch')
assert 'offArtifact'not in pr and 'onArtifact'not in pr and type(pr['loader'])is str
# Original run's pure container parser only, no main/import operational module.
rt=ast.parse((D/'run.py').read_text());pure=[x for x in rt.body if isinstance(x,ast.FunctionDef)and x.name in ['need','container']];rs={'re':re};exec(compile(ast.Module(body=pure,type_ignores=[]),'pure-container','exec'),rs)
payload,exports=rs['container'](Path(pr['candidateContainer']).read_bytes());assert payload==Path(pr['producer']).read_bytes()and exports==[('main',0,0)]and len(payload)==866384 and sha(payload)=='5cda246fec1d653b5ff044a56491069874f7a0b58da87785887c369573ccec8c'
# Pure compiler output validator positive and explicit wrong-path/extra/offset/size refusals.
co={};exec(compile((D/'compiler_output.py').read_bytes(),'pure-output','exec'),co)
c=pr['cases'][0];good=('{:ok true, :target :aarch64-macos, :output '+json.dumps(c['outputPath'])+', :bytes 3724}\n').encode();assert co['parse_output'](good,c)=={'kind':'compile','containerBytes':3724}
e=pr['cases'][1];eg=('{:ok true, :output '+json.dumps(e['outputPath'])+', :offset 1224, :length 3640, :arity 1}\n').encode();assert co['parse_output'](eg,e)['offset']==1224
for b,k in [(good+b'EXTRA\n',c),(good.replace(b'3724',b'4194561'),c),(eg.replace(b'1224',b'1225'),e),(eg.replace(b'3640',b'1000'),e)]:
 try:co['parse_output'](b,k)
 except AssertionError:pass
 else:raise AssertionError('bad output admitted')
controlDiff=(D/'controller.py').read_text();old=(W/'crc-original-guest-native-controller-source-v4-20261009-dense/controller.py').read_text();assert controlDiff.replace("'memoryAdmissionRecord':record,",'')==old
r={'status':'HOLD_SOURCE_TC_ORIGINAL19_FIXEDPOINT44_V1_WRAPPER_AND_COMPLETION','independent':True,'priorAuthorship':False,'sourcePinsSHA256':sha((D/'source-pins.json').read_bytes()),'driverSHA256':sha((D/'run.py').read_bytes()),'preregistrationSHA256':sha((D/'preregistration.json').read_bytes()),'subject':str(D),'freeze':pin(D/'freeze.json'),'verified':{'sourceFiles':16,'regularInputFiles':2560,'inputBytes':441662409,'allHashesExact':True,'canonicalOriginalSourcesAndProfiles':19,'current16TCSourceReconstructionExact':True,'unitySHA256':sha(b''.join(parts)),'G0WholeContainerNativeSoleMain0':True,'fixedCommands':44,'workloadCompileExtract':38,'ownSourceCompileExtract':6,'generationProducers':'G0 -> G1 -> G2 -> G3; G0/G1 equality recorded only, G1/G2/G3 whole identity required','environmentFields':17,'capabilities':'35,37,38,39','compileFuel':'off','strictSamplingOnly':True,'controllerDeltaOnlyMemoryAdmissionRecordReturn':True,'pureOutputPositiveControls':2,'pureOutputNegativeControls':4},
'blockers':[{'id':'B1','file':'launch-wrapper.py','issue':'Copied CRC wrapper cannot admit frozen44 schema: allowed() dereferences missing orderedChildren; subsequent offArtifact/onArtifact keys are also absent, and loader is a string while checked expects loader receipt dict. First fixed call fails before loader exec.','pureControl':{'firstFailure':firstFault,'nativeOperations':0},'minimalRepair':'Fresh exact wrapper uses cases, pinned loader/interpreter receipts, fixed G0 plus sealed generatedG1/G2 whole bytes and solemain0, bound case producers/order/input/output/capabilities. Preserve V1.'},{'id':'B2','file':'run.py:success report/finally terminal','issue':'COMPLETE report is saved inside try before required finally terminal save. Terminal write/fsync failure can leave a COMPLETE marker.','minimalRepair':'Save terminal first; only after successful final closure/evidence guard save final success report with GO/terminal/attempts/generated artifact bindings. No COMPLETE marker on evidence persistence failure.'}],
'additionalSchemaGap':'GO admission checks required values but does not reject unknown top-level keys or validate C2=false declared by go-schema. Fixed44 code limits operations, but exact schema admission should be explicit in fresh version.',
'operationalPrerequisiteHOLD':'Changed controller6a78 requires a fresh matching actual FileIO/controller fixture; old4a9 proof must not qualify. Two exact source reviews and specific GO remain absent. This report is not PASS.',
'limitations':['G0 saved conditional source/artifact correspondence is supported by prior failed7 raw and separate repair/extract identity proofs; old build8 remains failed, no selfbuild or runtime performance qualification.','Static code intended lifecycle/resource/capture/journal remains V4-based; no actual process/thread/FD/sampler/compiler/native operations were run here.','No claim all44 execute, whole original19 native correctness, ABI/trap/fuel, fixedpoint runtime, hard memory peak, officialscore/C2/CID/performance.','Complete pin hashing and narrow pure parser/admission controls only; no subject source write.'],
'operationalCalls':0,'actualThreadFDProcessNativeNetworkAPICalls':0,'subjectEdits':0,'reviewerSource':pin(Path(__file__))}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(O/'report.json')))
