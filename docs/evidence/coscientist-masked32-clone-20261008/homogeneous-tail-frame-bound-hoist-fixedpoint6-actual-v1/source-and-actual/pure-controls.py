"""Source reads plus injected generation/ownership data. No operational APIs."""
from pathlib import Path
import json,copy,hashlib,ast,importlib.util
import run
from integration import MEMORY_POLICY,classify_memory
from compiler_output import parse_output
D=Path(__file__).resolve().parent;pr=json.loads((D/'preregistration.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());neg=[]
def refuse(name,f):
 try:f()
 except (AssertionError,KeyError,IndexError,TypeError):neg.append(name)
 else:raise AssertionError('mutant admitted:'+name)
assert run.registry_scope(pr,ip)
for name,k,value in [('stale-old-file-count','exactInputFiles',50),('stale-old-byte-count','exactInputLogicalBytes',5292422),('bool-count','exactInputFiles',True),('bool-bytes','exactInputLogicalBytes',True)]:
 q=copy.deepcopy(pr);q[k]=value;refuse(name,lambda:run.registry_scope(q,ip))
schema=json.loads((D/'go-schema.json').read_bytes());assert set(schema['requiredExactKeys'])==set(['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','candidateSourcePinsSHA256']+run.PROOF_KEYS)
assert len(schema['requiredExactKeys'])==len(set(schema['requiredExactKeys']))
assert run.source_scope(pr,ip)
for p,r in ip.items():run.pin(p,r)
for name,change in [('seventh-case',lambda p:p['cases'].append(p['cases'][0])),('old-G1-equality-imposed',lambda p:p.update(requireG1G2Equal=True)),('wrong-generation-order',lambda p:p['cases'][2].update(generation=4)),('wrong-builder',lambda p:p['cases'][4].update(producer=p['G1Native']['path'])),('source-not-current-unity',lambda p:p['sourceCandidate'].update(sha256='0'*64)),('fuel-changed',lambda p:p['environment'].update(KEXE_FUEL='1')),('compiler-cap-broadened',lambda p:p.update(capabilities='20,35,37,38,39')),('clobber-invented',lambda p:p.update(clobberCertificateQualified=True)),('outer-host-missing',lambda p:p['operationalEnvironment'].update(requiresOuterHostEscalation=False))]:
 q=copy.deepcopy(pr);change(q);refuse(name,lambda:run.source_scope(q,ip))
for i,c in enumerate(pr['cases']):
 assert run.compiler_case(c['nativeArgv'],pr,c);a=c['nativeArgv'][:];a[6]='0';refuse('missing-guest-boundary-'+str(i),lambda:run.compiler_case(a,pr,c))
 raw=(b'{:ok true, :target :aarch64-macos, :output '+json.dumps(c['outputPath']).encode()+b', :bytes 30}\n')if c['kind']=='compile'else(b'{:ok true, :output '+json.dumps(c['outputPath']).encode()+b', :offset 0, :length 4, :arity 0}\n')
 assert parse_output(raw,c)['kind']==c['kind'];refuse('extra-output-'+str(i),lambda:parse_output(raw+b'x',c))
keys=['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','candidateSourcePinsSHA256']+run.PROOF_KEYS
GO={k:None for k in keys};GO.update(status=pr['rootGOStatus'],maximumLoaderCalls=6,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=False,C2=False,outerHostLaunchRequiresEscalation=True);assert run.go_header(GO,pr,Path(pr['freshOutputRoot']))
for name,k,v in [('GO-extra','extra',1),('GO-seven','maximumLoaderCalls',7),('GO-runtime','runtimeGuestAuthorized',True),('GO-timing','timingAuthorized',True),('GO-C2','C2',True),('GO-no-host','outerHostLaunchRequiresEscalation',False)]:
 q=copy.deepcopy(GO);q[k]=v;refuse(name,lambda:run.go_header(q,pr,Path(pr['freshOutputRoot'])))
# Synthetic normal-closure records are model inputs, not a native certificate.
r=dict(policy=MEMORY_POLICY,failure=None,acceptedSamples=1,acceptedLeaderBirthBound=True,otherRefusals=[],completePipeEOF=True,stoppedClosedCapture=True,rawTruncated=False,captureErrors=[],exactDirectChildWait='closed0',waitUncertain=False,withinOriginalDeadline=True,groupAuthorityRetired=True,groupOperationsAfterUncertainty=0,groupOperationsAfterWait=0,loaderWaitProtocolPinned=True)
obs=dict(semanticQualification=True,sampleReceiptPersistenceQualified=True,memoryAdmissionRecord=r,memoryObservation=classify_memory(r),status='COMPLETE_SEMANTIC_SAMPLED_MEMORY',strictOldMemoryPolicyPassed=True,capture={'firstFailure':None})
files={};O=Path(pr['freshOutputRoot']);realPath=run.Path;realPin=run.pin
class P:
 def __init__(self,p):self.p=str(p)
 def __str__(self):return self.p
 def __truediv__(self,p):return P(realPath(self.p)/str(p))
 def read_bytes(self):return files[self.p]
 def exists(self):return self.p in files
 def is_symlink(self):return False
 def __fspath__(self):return self.p
def rec(p):b=files[str(p)];return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def pinned(p,r):assert rec(p)==dict(path=str(p),bytes=r['bytes'],sha256=r['sha256']);return P(p)
run.Path=P;run.pin=pinned
root='/pure/root-go.json';files[root]=b'model exact rootGO';gr=rec(root);builds={};artifacts=[]
for gen in [2,3,4]:
 n=str(O/('G'+str(gen)+'.bin'));k=str(O/('G'+str(gen)+'.kseed'));files[n]=bytes.fromhex('c0035fd6');files[k]=b'KSEED1 4 1\nmain 0 0\n\n'+files[n];nr=rec(n);kr=rec(k)
 b=dict(format='hft-compose511-bound-hoist-generation-producer/v1',generation=gen,source=copy.deepcopy(pr['sourceCandidate']),builder=copy.deepcopy(pr['G1Native'])if gen==2 else copy.deepcopy(artifacts[-1]['native']),builderBuild=None if gen==2 else rec(O/('G'+str(gen-1)+'-build-receipt.json')),native=nr,container=kr,rootGO=gr,closedCompilerCalls=2,certificateQualified=False,attempts=[])
 for j in [0,1]:
  i=(gen-2)*2+j;c=pr['cases'][i];b['attempts'].append(dict(index=i+1,label=c['label'],nativeArgv=c['nativeArgv'],state='terminal',returncode=0,failure=None,captureStopAcknowledged=True,waitUncertain=False,controllerObservation=copy.deepcopy(obs),structuredReportObservation=dict(kind='compile',containerBytes=kr['bytes'])if j==0 else dict(kind='extract',offset=0,nativeBytes=4,arity=0)))
 assert run.build_guard(b,pr,nr,kr,gr,gen);files[str(O/('G'+str(gen)+'-build-receipt.json'))]=json.dumps(b).encode();builds[gen]=copy.deepcopy(b);artifacts.append(dict(generation=gen,native=nr,container=kr,exports=[('main',0,0)]))
assert run.fixedpoint(artifacts);assert pr['G1Native']['bytes']!=artifacts[0]['native']['bytes'] # model deliberately differs G1
for name,change in [('wrong-owned-source',lambda q:q['source'].update(sha256='0'*64)),('missing-prev-build',lambda q:q.update(builderBuild=None)),('wrong-prev-builder',lambda q:q['builder'].update(sha256='0'*64)),('wrong-prev-receipt',lambda q:q['builderBuild'].update(sha256='0'*64)),('wrong-root-GO',lambda q:q['rootGO'].update(sha256='0'*64)),('unclosed-stage',lambda q:q['attempts'][0].update(state='unclosed')),('nonzero-stage',lambda q:q['attempts'][1].update(returncode=2)),('wrong-extract-offset',lambda q:q['attempts'][1]['structuredReportObservation'].update(offset=4)),('active-writer',lambda q:q['attempts'][0].update(captureStopAcknowledged=False)),('unknown-sampling-refusal',lambda q:q['attempts'][1]['controllerObservation']['memoryAdmissionRecord'].update(otherRefusals=['failure-pid-not-previously-bound'])),('missing-previous-call',lambda q:q['attempts'].pop()),('extra-receipt-field',lambda q:q.update(extra=True)),('invented-certificate',lambda q:q.update(certificateQualified=True))]:
 q=copy.deepcopy(builds[4]);change(q);refuse(name,lambda:run.build_guard(q,pr,artifacts[2]['native'],artifacts[2]['container'],gr,4))
q=copy.deepcopy(artifacts);q[1]['exports']=[('main',4,0)];refuse('wrong-fixedpoint-exports',lambda:run.fixedpoint(q))
q=copy.deepcopy(artifacts);p=q[1]['native']['path'];files[p]=bytes.fromhex('000020d4');q[1]['native']=rec(p);kp=q[1]['container']['path'];files[kp]=b'KSEED1 4 1\nmain 0 0\n\n'+files[p];q[1]['container']=rec(kp);refuse('whole-generation-byte-difference',lambda:run.fixedpoint(q))
run.Path=realPath;run.pin=realPin
# Unchanged native-call guard refuses a seventh before library/API setup.
s=importlib.util.spec_from_file_location('pure_native',D/'native-call.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);refuse('seventh-before-API',lambda:m.call(D,O,pr,pr['cases'][0],[None]*6,lambda *a:None,'0'*64))
# Pure resource witness: no setters/syscalls. Missing or raised limits refuse.
keys=sorted(pr['environment']);jr=[dict(stage='environment-admission',suppliedKeyNames=keys,runtimeExtraKeyNames=[],missingKeyNames=[],changedExpectedKeyNames=[],nativeExecKeyNames=keys,nativeExecEnvironmentExact=True)]
for i,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)],1):
 jr.extend([dict(index=i,limit=name,stage='before',before=[9223372036854775807]*2,desired=[soft,hard]),dict(index=i,limit=name,stage='outcome',outcome='installed',readback=[soft,hard])])
jr.append(dict(stage='exec-ready',argv=pr['cases'][0]['nativeArgv'],ASSetterRequested=False,CPUGraceHardSeconds=1801))
class Journal:
 def __init__(self,rows):self.raw=b''.join(json.dumps(r).encode()+b'\n'for r in rows)
 def stat(self):return type('S',(),{'st_size':len(self.raw)})()
 def read_bytes(self):return self.raw
assert m.resource_journal(Journal(jr),pr,pr['cases'][0]['nativeArgv'])
for name,change in [('missing-resource-readback',lambda r:r.pop(4)),('finite-cpu-raised',lambda r:r[3].update(before=[10,11])),('unknown-env-key',lambda r:r[0]['nativeExecKeyNames'].append('EXTRA')),('wrong-exec-argv',lambda r:r[5].update(argv=['wrong']))]:
 q=copy.deepcopy(jr);change(q);refuse(name,lambda:m.resource_journal(Journal(q),pr,pr['cases'][0]['nativeArgv']))

for p in D.glob('*.py'):ast.parse(p.read_text())
print(json.dumps(dict(status='PASS_PURE_G2_G3_G4_SOURCE_SEALED_CHAIN_AND_WHOLE_FIXEDPOINT_MODELS_ONLY',sourceScopePositive=True,compilerOutputPositiveCases=6,generatedChainPositiveStages=3,G2G3G4WholeEqualModel=True,G1DifferentModelAccepted=True,refusedMutants=neg,operationalCalls=0),indent=2))
