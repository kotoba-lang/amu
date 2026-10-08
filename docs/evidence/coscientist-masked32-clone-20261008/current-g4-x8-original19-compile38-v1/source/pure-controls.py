"""Pure SOURCE/read receipt and compiler grammar models; no operations."""
from pathlib import Path
import json,copy,importlib.util,ast
import run
from compiler_output import parse_output
D=Path(__file__).resolve().parent;pr=json.loads((D/'preregistration.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());neg=[]
def refuse(name,f):
 try:f()
 except (AssertionError,KeyError,IndexError,TypeError):neg.append(name)
 else:raise AssertionError('mutant admitted:'+name)
assert run.source_scope(pr,ip)
for p,r in ip.items():run.pin(p,r)
for name,change in [('thirtyninth-case',lambda p:p['cases'].append(p['cases'][0])),('missing-original-workload',lambda p:p['entries'].pop()),('changed-source',lambda p:p['entries'][0]['source'].update(sha256='0'*64)),('changed-symbol',lambda p:p['entries'][1].update(symbol='wrong')),('changed-profile',lambda p:p['entries'][1]['iterations'].append(64)),('G1-substitute',lambda p:p['currentCompiler'].update(path=p['fixedpointPreregistration']['path'])),('wrong-G4-bytes',lambda p:p['currentCompiler'].update(sha256='0'*64)),('wrong-container',lambda p:p['currentCompilerContainer'].update(sha256='0'*64)),('wrong-fixedpoint-proof',lambda p:p['fixedpointActualProof'].update(sha256='0'*64)),('wrong-generated-build-receipt',lambda p:p['fixedpointBuildReceipt'].update(sha256='0'*64)),('old-output-reuse',lambda p:p.update(reusesPreviousWorkloadArtifacts=True)),('changed-compiler-fuel',lambda p:p['environment'].update(KEXE_FUEL='1')),('broadened-capability',lambda p:p.update(capabilities='20,35,37,38,39')),('invented-adoption',lambda p:p.update(candidateAdoptionQualified=True)),('wrong-campaign-bound',lambda p:p.update(maximumSequentialCampaignSeconds=100000)),('missing-hostprofile',lambda p:p['operationalEnvironment'].update(requiresOuterHostEscalation=False))]:
 q=copy.deepcopy(pr);change(q);refuse(name,lambda:run.source_scope(q,ip))
for i,c in enumerate(pr['cases']):
 assert run.compiler_case(c['nativeArgv'],pr,c);a=c['nativeArgv'][:];a[6]='0';refuse('wrong-guest-boundary-'+str(i),lambda:run.compiler_case(a,pr,c))
 path=json.dumps(c['outputPath']).encode();raw=(b'{:ok true, :target :aarch64-macos, :output '+path+b', :bytes 30}\n')if c['kind']=='compile'else(b'{:ok true, :output '+path+b', :offset 0, :length 4, :arity 1}\n')
 assert parse_output(raw,c)['kind']==c['kind'];refuse('extra-output-'+str(i),lambda:parse_output(raw+b'x',c))
keys=['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','candidateSourcePinsSHA256']+run.PROOF_KEYS
GO={k:None for k in keys};GO.update(status=pr['rootGOStatus'],maximumLoaderCalls=38,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=False,C2=False,outerHostLaunchRequiresEscalation=True);assert run.go_header(GO,pr,Path(pr['freshOutputRoot']))
for name,k,v in [('GO-extra','extra',True),('GO-thirtynine','maximumLoaderCalls',39),('GO-runtime','runtimeGuestAuthorized',True),('GO-timing','timingAuthorized',True),('GO-C2','C2',True),('GO-no-hostprofile','outerHostLaunchRequiresEscalation',False)]:
 q=copy.deepcopy(GO);q[k]=v;refuse(name,lambda:run.go_header(q,pr,Path(pr['freshOutputRoot'])))
s=importlib.util.spec_from_file_location('pure_native',D/'native-call.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);refuse('thirtyninth-before-API',lambda:m.call(D,Path(pr['freshOutputRoot']),pr,pr['cases'][0],[None]*38,lambda *a:None,'0'*64))
# Pure unchanged installed resource receipt, no actual setter.
keys=sorted(pr['environment']);jr=[dict(stage='environment-admission',suppliedKeyNames=keys,runtimeExtraKeyNames=[],missingKeyNames=[],changedExpectedKeyNames=[],nativeExecKeyNames=keys,nativeExecEnvironmentExact=True)]
for i,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)],1):jr.extend([dict(index=i,limit=name,stage='before',before=[9223372036854775807]*2,desired=[soft,hard]),dict(index=i,limit=name,stage='outcome',outcome='installed',readback=[soft,hard])])
jr.append(dict(stage='exec-ready',argv=pr['cases'][0]['nativeArgv'],ASSetterRequested=False,CPUGraceHardSeconds=1801))
class J:
 def __init__(self,r):self.b=b''.join(json.dumps(x).encode()+b'\n'for x in r)
 def stat(self):return type('S',(),dict(st_size=len(self.b)))()
 def read_bytes(self):return self.b
assert m.resource_journal(J(jr),pr,pr['cases'][0]['nativeArgv'])
for name,change in [('missing-resource-readback',lambda q:q.pop(4)),('raising-finite-cpu',lambda q:q[3].update(before=[10,11])),('unknown-native-env',lambda q:q[0]['nativeExecKeyNames'].append('EXTRA'))]:
 q=copy.deepcopy(jr);change(q);refuse(name,lambda:m.resource_journal(J(q),pr,pr['cases'][0]['nativeArgv']))
for p in D.glob('*.py'):ast.parse(p.read_text())
print(json.dumps(dict(status='PASS_PURE_CURRENT_G4_ORIGINAL19_COMPILE38_SOURCE_AND_REFUSAL_CONTROLS_ONLY',sourceScopePositive=True,compilerCases=38,refusedMutants=neg,operationalCalls=0),indent=2))
