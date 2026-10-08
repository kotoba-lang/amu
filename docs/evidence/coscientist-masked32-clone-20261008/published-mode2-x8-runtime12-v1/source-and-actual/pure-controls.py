"""Finite source, loader ABI, whole report and refusal controls; no operational APIs."""
from pathlib import Path
import json,copy,importlib.util,ast
import run
from loader_grammar import interpretation
from runtime import qualify,FIELDS
D=Path(__file__).resolve().parent;pr=json.loads((D/'preregistration.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());neg=[]
def refuse(name,f):
 try:f()
 except (AssertionError,IndexError,KeyError,TypeError):neg.append(name)
 else:raise AssertionError('mutant admitted:'+name)
assert run.source_scope(pr)
for p,r in ip.items():run.pin(p,r)
for name,change in [('wrong-loader-protocol',lambda p:p['loaderSupervisorProtocolView'].update(sha256='0'*64)),('wrong-loader-binary',lambda p:p['loaderArtifact'].update(sha256='0'*64)),('thirteenth-case',lambda p:p['cases'].append(p['cases'][0])),('changed-statemate-profile',lambda p:p['cases'][8].update(profile=64)),('changed-statemate-symbol',lambda p:p['cases'][0].update(symbol='stage-cell')),('wrong-own-offset',lambda p:p['cases'][1].update(offset=0)),('wrong-container',lambda p:p['cases'][0]['container'].update(sha256='0'*64)),('wrong-source',lambda p:p['fixtureSource'].update(sha256='0'*64)),('wrong-expected-result',lambda p:p['cases'][0].update(expectedResult=1)),('changed-fuel',lambda p:p['environment'].update(KEXE_FUEL='1')),('changed-arena',lambda p:p['environment'].update(KEXE_VECTOR_ITEMS='1')),('outer-host-declaration-absent',lambda p:p['operationalEnvironment'].update(requiresOuterHostEscalation=False)),('loader-sandbox-weakening',lambda p:p['operationalEnvironment'].update(loaderSandboxWeakeningAuthorized=True)),('invented-adoption',lambda p:p.update(generalCandidateAdoptionQualified=True)),('invented-clobber',lambda p:p.update(fullClobberCertificateQualified=True)),('invented-typed-admission',lambda p:p.update(actualTypedMode2AdmissionObserved=True))]:
 q=copy.deepcopy(pr);change(q);refuse(name,lambda:run.source_scope(q))
for i,c in enumerate(pr['cases']):
 assert interpretation(c['nativeArgv'])==dict(typedI64=[c['profile']],guestArgv=None,effectiveArgc=7)
 q=c['nativeArgv'][:6]+['--']+c['nativeArgv'][6:];refuse('misplaced-typed-separator-'+str(i),lambda:interpretation(q))
# Pure parser fixture; these numbers are decoder inputs, not executed/golden fuel evidence.
a={k:0 for k in FIELDS};a.update(vectors=1,**{'vector-items':1,'heap-bytes':24});err=('KEXE_ARENA_USE {'+' '.join(':'+k+' '+str(a[k])for k in FIELDS)+'}\n').encode()
raw=b'{:status :ok :result 3 :fuel {:initial 16777216 :remaining 16777210} :heap {:capacity 2097152 :used 0} :string-pool {:capacity 65536 :used 0} :vectors {:capacity 4096 :used 1} :vector-items {:capacity 65536 :used 1}}\n'
assert qualify(raw,err,3)['result']==3
for name,o,e,x in [('extra-stdout',raw+b'x',err,3),('extra-stderr',raw,err+b'x',3),('wrong-result',raw,err,1),('unmetered',raw.replace(b':remaining 16777210}',b':remaining 16777210 :metered false}'),err,3),('changed-capacity',raw.replace(b':capacity 65536',b':capacity 1',1),err,3),('wrong-arena-parity',raw,err.replace(b':vectors 1',b':vectors 2'),3)]:refuse(name,lambda:qualify(o,e,x))
keys=['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','OFFActualProof','CandidateCompilerActualProof','C95Oracle','C95OracleProof','integrationFixtureProof','EmittedAssociationProof'];g={k:None for k in keys};g.update(status=pr['rootGOStatus'],maximumLoaderCalls=12,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=True,C2=False,outerHostLaunchRequiresEscalation=True);assert run.go_header(g,pr,Path(pr['freshOutputRoot']))
for name,k,v in [('GO-extra','extra',True),('GO-thirteenth','maximumLoaderCalls',13),('GO-timing','timingAuthorized',True),('GO-C2','C2',True),('GO-retry','noRetry',False),('GO-no-host-declaration','outerHostLaunchRequiresEscalation',False)]:
 q=copy.deepcopy(g);q[k]=v;refuse(name,lambda:run.go_header(q,pr,Path(pr['freshOutputRoot'])))
s=importlib.util.spec_from_file_location('pure_native',D/'native-call.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);refuse('thirteenth-before-adapter-setup',lambda:m.call(D,Path(pr['freshOutputRoot']),pr,pr['cases'][0],[None]*12,lambda *a:None,'0'*64))
keys=sorted(pr['environment']);jr=[dict(stage='environment-admission',suppliedKeyNames=keys,runtimeExtraKeyNames=[],missingKeyNames=[],changedExpectedKeyNames=[],nativeExecKeyNames=keys,nativeExecEnvironmentExact=True)]
for i,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',30,31)],1):jr.extend([dict(index=i,limit=name,stage='before',before=[9223372036854775807]*2,desired=[soft,hard]),dict(index=i,limit=name,stage='outcome',outcome='installed',readback=[soft,hard])])
jr.append(dict(stage='exec-ready',argv=pr['cases'][0]['nativeArgv'],ASSetterRequested=False,CPUGraceHardSeconds=31))
class J:
 def __init__(self,q):self.b=b''.join(json.dumps(x).encode()+b'\n'for x in q)
 def stat(self):return type('S',(),dict(st_size=len(self.b)))()
 def read_bytes(self):return self.b
assert m.resource_journal(J(jr),pr,pr['cases'][0]['nativeArgv'])
for name,change in [('resource-readback-missing',lambda q:q.pop(4)),('finite-cpu-raised',lambda q:q[3].update(before=[10,11]))]:
 q=copy.deepcopy(jr);change(q);refuse(name,lambda:m.resource_journal(J(q),pr,pr['cases'][0]['nativeArgv']))
for p in D.glob('*.py'):ast.parse(p.read_text())
print(json.dumps(dict(status='PASS_PURE_RUNTIME12_SOURCE_TYPED_ABI_REPORT_RESOURCE_AND_REFUSAL_CONTROLS_ONLY',positiveSourceScope=True,typedArgvCases=12,fixtureI64Result3ParserPositive=True,refusedMutants=neg,operationalCalls=0),indent=2))
