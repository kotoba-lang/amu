"""Finite pure model/byte controls; no Popen/thread/FD/resource/kernel operations."""
from pathlib import Path
import json,hashlib,copy,importlib.util,ast
import run
from integration import MEMORY_POLICY,classify_memory
from artifact_admission import accept_artifact_observation
from compiler_output import parse_output
D=Path(__file__).resolve().parent
pr=json.loads((D/'preregistration.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());neg=[]
def refuse(name,f):
 try:f()
 except (AssertionError,IndexError,KeyError,TypeError):neg.append(name)
 else:raise AssertionError('negative admitted:'+name)
assert run.source_scope(pr,ip) is True
for p,r in ip.items():run.pin(p,r)
for name,change in [('seventh-case',lambda p:p['cases'].append(p['cases'][0])),('wrong-producer-order',lambda p:p['cases'][2].update(producer=p['producer'])),('stage-certified',lambda p:p.update(clobberCertificateQualified=True)),('fuel-changed',lambda p:p['environment'].update(KEXE_FUEL='1'))]:
 q=copy.deepcopy(pr);change(q);refuse(name,lambda:run.source_scope(q,ip))
for i,c in enumerate(pr['cases']):
 assert run.compiler_case(c['nativeArgv'],pr,c)
 q=c['nativeArgv'].copy();q[6]='0';refuse('misplaced-guest-boundary-'+str(i),lambda:run.compiler_case(q,pr,c))
 q=c['nativeArgv'].copy();q[2]='4';refuse('wrong-entry-'+str(i),lambda:run.compiler_case(q,pr,c))
# Model observation deliberately not a native certificate.
record=dict(policy=MEMORY_POLICY,failure=None,acceptedSamples=1,acceptedLeaderBirthBound=True,otherRefusals=[],completePipeEOF=True,stoppedClosedCapture=True,rawTruncated=False,captureErrors=[],exactDirectChildWait='closed0',waitUncertain=False,withinOriginalDeadline=True,groupAuthorityRetired=True,groupOperationsAfterUncertainty=0,groupOperationsAfterWait=0,loaderWaitProtocolPinned=True)
obs=dict(semanticQualification=True,sampleReceiptPersistenceQualified=True,memoryAdmissionRecord=record,memoryObservation=classify_memory(record),status='COMPLETE_SEMANTIC_SAMPLED_MEMORY',strictOldMemoryPolicyPassed=True,capture={'firstFailure':None})
assert accept_artifact_observation(obs)
g={'path':'/pure/go.json','bytes':17,'sha256':'a'*64};nr={'path':pr['candidateNativePath'],'bytes':4,'sha256':'b'*64};kr={'path':pr['candidateContainerPath'],'bytes':30,'sha256':'c'*64}
b={'format':'published-mode2-x8-sealed-producer/v1','source':pr['sourceCandidate'],'builder':dict(path=pr['producer'],**ip[pr['producer']]),'native':nr,'container':kr,'rootGO':g,'closedCompilerCalls':2,'certificateQualified':False,'attempts':[]}
for i,c in enumerate(pr['cases'][:2]):
 b['attempts'].append(dict(index=i+1,label=c['label'],nativeArgv=c['nativeArgv'],state='terminal',returncode=0,failure=None,captureStopAcknowledged=True,waitUncertain=False,controllerObservation=copy.deepcopy(obs),structuredReportObservation={'kind':'compile','containerBytes':30}if i==0 else {'kind':'extract','offset':0,'nativeBytes':4,'arity':0}))
assert run.build_guard(b,pr,nr,kr,g)
for name,change in [('wrong-owned-source',lambda q:q['source'].update(sha256='0'*64)),('wrong-builder',lambda q:q['builder'].update(sha256='0'*64)),('unclosed-build',lambda q:q['attempts'][1].update(state='unclosed')),('nonzero-build',lambda q:q['attempts'][0].update(returncode=2)),('wrong-build-main-entry',lambda q:q['attempts'][1]['structuredReportObservation'].update(offset=4)),('active-capture',lambda q:q['attempts'][0].update(captureStopAcknowledged=False)),('unknown-sampler-refusal',lambda q:q['attempts'][1]['controllerObservation']['memoryAdmissionRecord'].update(otherRefusals=['failure-pid-not-previously-bound'])),('wrong-root-go',lambda q:q['rootGO'].update(sha256='0'*64)),('invented-certificate',lambda q:q.update(certificateQualified=True)),('missing-build-attempt',lambda q:q['attempts'].pop()),('extra-build-field',lambda q:q.update(extra=True))]:
 q=copy.deepcopy(b);change(q);refuse(name,lambda:run.build_guard(q,pr,nr,kr,g))
# Compiler-output whole-string controls for all six, no execution.
for i,c in enumerate(pr['cases']):
 p=json.dumps(c['outputPath']).encode()
 raw=(b'{:ok true, :target :aarch64-macos, :output '+p+b', :bytes 30}\n')if c['kind']=='compile'else (b'{:ok true, :output '+p+b', :offset 0, :length 4, :arity '+str(c['arity']).encode()+b'}\n')
 assert parse_output(raw,c)['kind']==c['kind'];refuse('extra-output-'+str(i),lambda:parse_output(raw+b'x',c))
# Exact GO positives and unknown/broadening keys refused.
gh={k:None for k in ['sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','integrationFixtureProof','baselineActualProof','TCActualProof','candidateSourcePinsSHA256']};gh.update(status=pr['rootGOStatus'],maximumLoaderCalls=6,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=False,C2=False);assert run.go_header(gh,pr,Path(pr['freshOutputRoot']))
for name,k,v in [('GO-extra','extra',True),('GO-runtime','runtimeGuestAuthorized',True),('GO-C2','C2',True),('GO-retry','noRetry',False),('GO-seventh','maximumLoaderCalls',7)]:
 q=copy.deepcopy(gh);q[k]=v;refuse(name,lambda:run.go_header(q,pr,Path(pr['freshOutputRoot'])))
# The unchanged caller refuses seven before adapter setup; imports are inert.
s=importlib.util.spec_from_file_location('pure_native_call',D/'native-call.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
refuse('seventh-before-operational-setup',lambda:m.call(D,Path(pr['freshOutputRoot']),pr,pr['cases'][0],[None]*6,lambda *a:None,'0'*64))
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
print(json.dumps({'status':'PASS_PURE_SOURCE_SCOPE_SEALED_PRODUCER_AND_COMPILER_GRAMMAR_ONLY','sourceScopePositive':1,'compilerCases':6,'generatedProducerModelPositive':1,'generatedProducerMutants':11,'negatives':neg,'operationalCalls':0,'nativeCertificateQualified':False},indent=2))
