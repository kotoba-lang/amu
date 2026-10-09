"""Independent SOURCE-only review of root-authored runtime190, no operational callbacks."""
from pathlib import Path
import json,hashlib,stat,sys,runpy,io,contextlib,copy,ast,importlib.util
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-g4-original19-runtime190-source-v1-20261009-root';O=Path(__file__).resolve().parent;X=W/'published-mode2-x8-statemate-vector-runtime12-source-v1-20261009'
sys.path.insert(0,str(D))
def r(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=33554432;b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def save(n,q):(O/n).write_text(json.dumps(q,indent=2)+'\n')
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');fz=load(D/'freeze.json');original={str(D/n):r(D/n)for n in sp}
assert len(sp)==18 and len(ip)==120 and sum(v['bytes']for v in ip.values())==9774015
for name,key in [('source-pins.json','sourcePins'),('input-pins.json','inputPins'),('run.py','driver'),('preregistration.json','preregistration')]:assert r(D/name)==fz[key]
for n,v in sp.items():assert r(D/n)==v,n
for p,v in ip.items():assert r(p)==v,p
assert r(D/'source-pins.json')['sha256']=='6f2f75edbd2cc26ed16f58014df720e67cba1bdc121703622fc00f5c8af26873'
assert r(D/'input-pins.json')['sha256']=='06d92ea9ef141736f006ccc26bf1bbbf7436a23fc98398b1fcd42329c20046b7'
assert r(D/'run.py')['sha256']=='aad898d4ff88fc472fa39e3cb3245965553209d6ba616d1c615cbe351d9289e9'
assert r(D/'preregistration.json')['sha256']=='79bfa6a89e700925e1b31b5a47c939b0635b63b0bd07cf0d0e2c0d8a0089b4f9'
import run
assert run.source_scope(pr)and run.loader_protocol(pr)
controls={}
for name in ['pure-controls.py','wrapper-controls.py']:
 buf=io.StringIO()
 with contextlib.redirect_stdout(buf):runpy.run_path(str(D/name),run_name='independent_source_control')
 q=json.loads(buf.getvalue());assert q['operationalCalls']==0;controls[name]=q;save(name[:-3]+'-recomputed.json',q)
assert controls['pure-controls.py']['typedArgvCases']==190 and len(controls['pure-controls.py']['refusedMutants'])==226
assert controls['wrapper-controls.py']['positiveWholeImagesAndExportCases']==190 and len(controls['wrapper-controls.py']['refusedMutants'])==201
# Read-only source/whole artifact association independently of subject's routine.
actual=load(pr['G4Original19ActualProof']['path']);fp=load(pr['FixedpointActualProof']['path']);off=load(pr['OFFActualProof']['path']);oracle=load(pr['C95Oracle']['path']);completion=load(pr['G4Original19Completion']['path']);matrix=load(pr['canonicalMatrix']['path'])
assert actual['original19Images']==pr['imagesON']==completion['original19Images']and actual['completion']==pr['G4Original19Completion']and actual['currentG4Native']==pr['G4Producer']['native']and actual['currentG4Container']==pr['G4Producer']['container']and actual['fixedpointActualProof']==pr['FixedpointActualProof']
assert actual['closedCompilerCalls']==38 and actual['qualification']['guestRuntime']is False and actual['qualification']['adoption']is False
assert pr['imagesOFF']==off['joinedOriginal19Images']and len(pr['cases'])==190
assert [e['workload']for e in pr['entries']]==[e['workload']for e in matrix['entries']]
assert len({(c['workload'],c['profile'],c['arm'])for c in pr['cases']})==190 and len({c['label']for c in pr['cases']})==190
for i,c in enumerate(pr['cases']):
 assert c['arm']==['OFF','ON'][i%2]and type(c['profile'])is int and type(c['expectedResult'])is int and c['expectedResult']in [0,1]
 answers=[v for v in oracle['rows']if v['workload']==c['workload']and v['n']==c['profile']];assert len(answers)==1 and c['expectedResult']==answers[0]['result']and c['source']['sha256']==answers[0]['sourceSHA256']and c['symbol']==answers[0]['symbol']
 from loader_grammar import interpretation
 assert interpretation(c['nativeArgv'])==dict(typedI64=[c['profile']],guestArgv=None,effectiveArgc=7)
# Qualified mechanics exact and wrapper counter-only bounded change.
components=['capture.py','controller.py','integration.py','runtime.py','typed-adapter.py','artifact_admission.py','callback_contract.py','loader_grammar.py','native-call.py'];xsp=load(X/'source-pins.json')
for n in components:assert (D/n).read_bytes()==(X/n).read_bytes()and r(D/n)==xsp[n]
assert (D/'launch-wrapper.py').read_text()==(X/'launch-wrapper.py').read_text().replace("go['maximumLoaderCalls']==12","go['maximumLoaderCalls']==190")
fixture=load(pr['qualifiedIntegrationFixtureProof']['path']);assert fixture['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY'
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert sp[n]['sha256']==fixture[k]
# Active import graph cannot reach excluded draft preparation helpers.
active=set(sp);imports=[]
for n in active:
 if not n.endswith('.py'):continue
 tree=ast.parse((D/n).read_text())
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
  if isinstance(node,ast.ImportFrom)and node.module:imports.append(node.module)
assert not any('draft' in x or 'prepare' in x or 'bind' in x or 'prospective' in x for x in imports)
assert 'prepare-v1.py'not in active and not Path(pr['freshOutputRoot']).exists()
# Additional decoder/resource/GO rejection models, entirely in memory.
spec=importlib.util.spec_from_file_location('source_resource_only',D/'native-call.py');nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc);extra=[]
def refuse(name,fn):
 try:fn()
 except (AssertionError,KeyError,IndexError,ValueError,TypeError):extra.append(name)
 else:raise AssertionError('admitted independent mutant:'+name)
from runtime import qualify,FIELDS
raw=b'{:status :ok :result 1 :fuel {:initial 16777216 :remaining 16777215} :heap {:capacity 2097152 :used 0} :string-pool {:capacity 65536 :used 0} :vectors {:capacity 4096 :used 0} :vector-items {:capacity 65536 :used 0}}\n';err=('KEXE_ARENA_USE {'+' '.join(':'+k+' 0'for k in FIELDS)+'}\n').encode();assert qualify(raw,err,1)['fuelConsumed']==1
for name,a,b in [('empty-output',b'',err),('trap-is-not-success',raw.replace(b':status :ok :result 1',b':status :trap :exit 120'),err),('fuel-overrun',raw.replace(b'16777215',b'16777217'),err),('wrong-initial-fuel',raw.replace(b'16777216',b'1000000'),err),('duplicate-counter-line',raw,err+err)]:refuse(name,lambda:qualify(a,b,1))
keys=sorted(pr['environment']);jr=[dict(stage='environment-admission',suppliedKeyNames=keys,runtimeExtraKeyNames=[],missingKeyNames=[],changedExpectedKeyNames=[],nativeExecKeyNames=keys,nativeExecEnvironmentExact=True)]
for i,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',30,31)],1):jr.extend([dict(index=i,limit=name,stage='before',before=[9223372036854775807]*2,desired=[soft,hard]),dict(index=i,limit=name,stage='outcome',outcome='installed',readback=[soft,hard])])
jr.append(dict(stage='exec-ready',argv=pr['cases'][0]['nativeArgv'],ASSetterRequested=False,CPUGraceHardSeconds=31))
class J:
 def __init__(self,q):self.b=b'\n'.join(json.dumps(x).encode()for x in q)
 def stat(self):return type('S',(),dict(st_size=len(self.b)))()
 def read_bytes(self):return self.b
assert nc.resource_journal(J(jr),pr,pr['cases'][0]['nativeArgv'])
for name,change in [('wrongCPU-hard32',lambda q:q[4].update(readback=[30,32])),('inheritedCPUraise',lambda q:q[3].update(before=[10,11])),('missing-resource-row',lambda q:q.pop(4)),('unexpected-runtime-env',lambda q:q[0].update(runtimeExtraKeyNames=['EXTRA'])),('false-native-exec-env',lambda q:q[0].update(nativeExecEnvironmentExact=False))]:
 q=copy.deepcopy(jr);change(q);refuse(name,lambda:nc.resource_journal(J(q),pr,pr['cases'][0]['nativeArgv']))
refuse('call191-pre-API-independent',lambda:nc.call(D,Path(pr['freshOutputRoot']),pr,pr['cases'][0],[None]*190,None,'0'*64))
# Scheme, budgets and exact original guest resource contract distinct from enlarged total campaign reservation.
schema=load(D/'go-schema.json');g={k:None for k in schema['requiredExactKeys']};g.update(status=pr['rootGOStatus'],maximumLoaderCalls=190,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=True,C2=False,outerHostLaunchRequiresEscalation=True);assert run.go_header(g,pr,Path(pr['freshOutputRoot']))
assert pr['maximumSequentialCampaignSeconds']==12000 and pr['controlledOutputReservationBytes']==4294967296 and pr['maximumRuntimeNativeStarts']==190 and pr['maximumConservativeWrapperLoaderNativeStages']==570 and pr['maximumAuxiliaryThreadStarts']==380
assert 190*(8388608+1048576+8388608)+8*16777216+190*4096+33554432<4294967296
for p,v in original.items():assert r(p)==v
q=dict(status=pr['sourceReviewStatus'],independent=True,subjectImplementationAuthorship=False,sourcePinsSHA256=r(D/'source-pins.json')['sha256'],inputPinsSHA256=r(D/'input-pins.json')['sha256'],driverSHA256=r(D/'run.py')['sha256'],preregistrationSHA256=r(D/'preregistration.json')['sha256'],verifiedClosure=dict(activeSourceFiles=18,targetedInputFiles=120,inputLogicalBytes=9774015,excludedDraftHelpersNotDriverReachable=True),proofBinding=dict(G4Original19ActualProof=pr['G4Original19ActualProof'],G4Original19Completion=pr['G4Original19Completion'],FixedpointActualProof=pr['FixedpointActualProof'],OFFActualProof=pr['OFFActualProof'],all190TypedArgsSourceBound=True,all95SavedCResultRowsSourceSymbolProfileBound=True),copiedComponents=components,wrapperChange='exactGO ceiling12→190 only',pureControls=dict(subjectSourceNegatives=226,wrapperWholeCasePositives=190,wrapperNegatives=201,extraIndependentRefusals=extra),findings=[],conclusions=['all190 adjacentOFF/ON cases bind unchanged19workload bodies/95canonical profiles including depthconv2000/ownarity1 exports and exactwhole payloads','ON receipts come from independently audited currentG4 compile38 and fixedpoint258d, not G1 artifacts','runtime17env/fuel16777216/17arena/zero capabilities/CPU30 hard31/outer30 directcleanup30 unchanged','fresh namespace, sealed exactargv,191preAPI refusal, immutable journals/stoppedraw and per-pair fuel/result17counter parity enforce finite diagnostic','durable terminal and finalcomplete guards before valid-last report; failure stops without retry','12000s campaign and4GiB output reservation explicit; no guest cap increase or filesystemquota/hardpeak assertion'],limitations=['SOURCE review only; no actual190 execution','typed prior-bound termination-gap diagnostics remain separate from strict finite sampled/hardpeak memory qualification','C95 supplies result only, no Cfuel/arenas/timing','generalABI/privateclobber/currenttypedmode2 admission/adoption/performance remain unqualified','active registry excludes draft helpers; pure controls AST-read drafts without executing them','cooperative IO/wall/cleanup and pinned source loader protocol do not prove dynamic OS closure'],auditScript=dict(path=str(Path(__file__)),**r(Path(__file__))),operationalCalls=0,subjectSourceWrites=0)
save('report.json',q);print(q['status'])
