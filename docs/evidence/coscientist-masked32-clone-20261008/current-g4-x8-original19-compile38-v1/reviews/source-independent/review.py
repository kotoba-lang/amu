"""Independent saved SOURCE audit only. No native/process/thread/FD/group/network calls."""
from pathlib import Path
import json,hashlib,stat,sys,runpy,io,contextlib,copy,ast
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-g4-original19-compile38-source-v1-20261009';O=Path(__file__).resolve().parent
sys.path.insert(0,str(D))
def r(p):
 assert stat.S_ISREG(p.lstat().st_mode)and not p.is_symlink();b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def save(n,q):(O/n).write_text(json.dumps(q,indent=2)+'\n')
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');freeze=load(D/'freeze.json');before={str(D/n):r(D/n)for n in sp}
assert r(D/'source-pins.json')['sha256']=='099f52dbbbd0a09bdb9bec665287785fc7bd42074f98c9410659d230cefe068b'
assert r(D/'input-pins.json')['sha256']=='ab76312481d00a708be43bd18f824b360493fd9db36d710944d0fce34bf31f14'
assert r(D/'run.py')['sha256']=='129d5ef6ca7347bf0884b82b613404bd2e35534ae6767ce71091644bd6736343'
assert r(D/'preregistration.json')['sha256']=='337f1571da4603ed8f1afd8efa2f736b9f23e342ba92d7366acb8955236ea85f'
assert len(sp)==22 and len(ip)==80 and sum(v['bytes']for v in ip.values())==10983592
for n,v in sp.items():assert r(D/n)==v,n
for n,v in ip.items():assert r(Path(n))==v,n
for n in sp:
 if n.endswith('.py'):ast.parse((D/n).read_text())
import run
assert run.source_scope(pr,ip)and run.existing_g4_guard(pr)
# Read-only recomputation of author's pure modeled controls; stdout captured in memory.
controls={}
for name in ['pure-controls.py','wrapper-controls.py']:
 buf=io.StringIO()
 with contextlib.redirect_stdout(buf):runpy.run_path(str(D/name),run_name='independent_pure_control')
 q=json.loads(buf.getvalue());assert q['operationalCalls']==0 and q==load(D/(name[:-3]+'.json'));controls[name]=q
 save(name[:-3]+'-recomputed.json',q)
assert len(controls['pure-controls.py']['refusedMutants'])==102 and controls['pure-controls.py']['compilerCases']==38
assert controls['wrapper-controls.py']['positiveCompilerCases']==38 and len(controls['wrapper-controls.py']['refusedMutants'])==11
# Independently check source supervisor's exact four-pin source spans, even though immutable parent guard uses whole pins.
pv=load(pr['loaderSupervisorProtocolView']['path']);assert len(pv['pins'])==4
for v in pv['pins']:assert r(Path(v['path']))=={k:v[k]for k in ['bytes','sha256']}
lines=Path(pv['pins'][0]['path']).read_text().splitlines(keepends=True)
for s in pv['spans']:
 text=''.join(lines[s['start']-1:s['end']]);assert text==s['text']and hashlib.sha256(text.encode()).hexdigest()==s['sha256']
assert pv['pins'][0]['sha256']=='f44b50995a0e45db4be35244da34dd61538a484c7d5ea2f15f7f5a73d9daa8c3'and pv['pins'][1]['sha256']=='5f7c433cf349362457887d0bdc01eb31b4e96413de2efe9a83b669675bcd6484'and pv['pins'][2]['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f'
# Exact qualified bytes / conservative old42 internal ceiling still subordinate to the38 finite schedule.
old=load(pr['nativeCallerSourcePins']['path']);assert r(D/'native-call.py')==old['native-call.py']
F=W/'published-mode2-x8-g2-g3-g4-fixedpoint6-source-v1-20261009';fsp=load(F/'source-pins.json')
qualified=['capture.py','controller.py','integration.py','typed-adapter.py','artifact_admission.py','compiler_output.py','runtime.py']
assert all(r(D/n)==fsp[n]for n in qualified)
assert (D/'fixedpoint_lineage.py').read_bytes()==(F/'run.py').read_bytes()
fixture=load(pr['qualifiedIntegrationFixtureProof']['path']);assert fixture['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert sp[n]['sha256']==fixture[k]
# Extra independent stored-build mutations exercise non-tautological prior admitted stage ownership.
from fixedpoint_lineage import build_guard
proof=load(pr['fixedpointActualProof']['path']);oldpr=load(pr['fixedpointPreregistration']['path']);base=load(pr['fixedpointBuildReceipt']['path']);root=proof['rootGO'];extra=[]
def refuses(name,z):
 try:build_guard(z,oldpr,pr['currentCompiler'],pr['currentCompilerContainer'],root,4)
 except (AssertionError,KeyError,TypeError,IndexError):extra.append(name)
 else:raise AssertionError('independent mutant admitted:'+name)
mutations=[('generation3',lambda z:z.update(generation=3)),('wrong-source',lambda z:z['source'].update(sha256='0'*64)),('unknown-receipt-key',lambda z:z.update(extra=True)),('invented-certificate',lambda z:z.update(certificateQualified=True)),('only-one-call',lambda z:z['attempts'].pop()),('prior-nonzero',lambda z:z['attempts'][0].update(returncode=1)),('prior-failure',lambda z:z['attempts'][0].update(failure='refused')),('uncertain-wait',lambda z:z['attempts'][1].update(waitUncertain=True)),('active-capture',lambda z:z['attempts'][0].update(captureStopAcknowledged=False)),('wrong-prior-argv',lambda z:z['attempts'][0].update(nativeArgv=[])),('wrong-rootGO',lambda z:z['rootGO'].update(sha256='0'*64)),('G1-builder-in-G4',lambda z:z['builder'].update(path=oldpr['G1Native']['path'])),('false-sample-admission',lambda z:z['attempts'][0]['controllerObservation'].update(semanticQualification=False)),('partial-payload-report',lambda z:z['attempts'][1]['structuredReportObservation'].update(nativeBytes=4))]
for name,mutate in mutations:
 z=copy.deepcopy(base);mutate(z);refuses(name,z)
# No frozen source byte changed by import/pure verification.
for p,v in before.items():assert r(Path(p))==v
assert not Path(pr['freshOutputRoot']).exists()
report=dict(status=pr['sourceReviewStatus'],independent=True,subjectImplementationAuthorship=False,sourcePinsSHA256=r(D/'source-pins.json')['sha256'],inputPinsSHA256=r(D/'input-pins.json')['sha256'],driverSHA256=r(D/'run.py')['sha256'],preregistrationSHA256=r(D/'preregistration.json')['sha256'],verifiedClosure=dict(sourceFiles=len(sp),inputFiles=len(ip),inputLogicalBytes=sum(v['bytes']for v in ip.values())),fixedG4=dict(native=pr['currentCompiler'],container=pr['currentCompilerContainer'],proof=pr['fixedpointActualProof'],recursiveCurrentG4G3G2AdmittedReceiptChain=True),pureControls=dict(recomputedAuthorNegatives=102,recomputedWrapperPositives=38,recomputedWrapperNegatives=11,independentStoredBuildNegatives=extra),findings=[],sourceConclusions=['exact38 adjacent fresh compile/extract original19 source/export/profile entries, no workload guest runs','current G4 complete payload sole main0 follows exact saved stage4/3/2 receipt chain; G1 cannot substitute','current16 source recomposition and candidate replacement whole bytes checked','fixed source loader protocol four pins and exact spans; conditional OS closure only','qualified seven components byte equal; native42 caller unchanged; finite38 schedule+case-array guard refuses39 before API','strict raw compile/extract whole output and full native/container selected own arity1; no sliced payload admission','original namedCPU1800/hard1801 FSIZE64MiB environment17 resources unchanged; campaign71000/output2GiB explicitly declared','valid-last only after38 admitted terminal0 calls+19whole images, immutable final guards and durable terminal; no retry'],limitations=['SOURCE only; no actual compile38 calls yet','sampled physical-footprint and explicitly eligible typed termination-gap diagnostic remain separate from hardpeak','inherited native-call42 docstring/guard is conservative; parent/wrapper/seals remain exact38','fixedpoint_lineage imports complete old driver as inert library; its main is never invoked','private-machine clobber/generalABI/full19 runtime/performance/adoption remain unqualified','targeted input proof archive hashes do not recursively reverify historical SDK closure'],auditScript=dict(path=str(Path(__file__)),**r(Path(__file__))),operationalCalls=0,subjectSourceWrites=0)
save('report.json',report);print(report['status'])
