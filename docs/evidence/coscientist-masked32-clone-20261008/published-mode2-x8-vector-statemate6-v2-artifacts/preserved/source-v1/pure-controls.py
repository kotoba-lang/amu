"""Bounded pure source/byte/invalidation controls only, no operational APIs."""
from pathlib import Path
import json,copy,importlib.util,ast
import run
from compiler_output import parse_output
D=Path(__file__).resolve().parent;pr=json.loads((D/'preregistration.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());neg=[]
def refuse(name,f):
 try:f()
 except (AssertionError,IndexError,KeyError,TypeError):neg.append(name)
 else:raise AssertionError('mutant admitted:'+name)
assert run.source_scope(pr,ip)and run.existing_candidate_guard(pr)
for p,r in ip.items():run.pin(p,r)
for name,change in [('seventh-case',lambda p:p['cases'].append(p['cases'][0])),('wrong-OFF-order',lambda p:p['cases'][0].update(producer=p['candidateNativePath'])),('invented-stage-certificate',lambda p:p.update(clobberCertificateQualified=True)),('changed-compiler-fuel',lambda p:p['environment'].update(KEXE_FUEL='1')),('changed-fixture',lambda p:p['fixtureSource'].update(sha256='0'*64)),('changed-original-statemate',lambda p:p['statemateEntry']['source'].update(sha256='0'*64)),('changed-profile',lambda p:p['statemateEntry']['iterations'].append(64))]:
 q=copy.deepcopy(pr);change(q);refuse(name,lambda:run.source_scope(q,ip))
for name,change in [('wrong-candidate-native',lambda p:p['candidateCompiler'].update(sha256='0'*64)),('wrong-candidate-container',lambda p:p['candidateCompilerContainer'].update(sha256='0'*64)),('wrong-existing-proof-hash',lambda p:p['candidateActualProof'].update(sha256='0'*64)),('rewritten-old-build-GO',lambda p:p['candidateBuildRootGO'].update(sha256='0'*64)),('wrong-old-build-receipt',lambda p:p['candidateSealedBuild'].update(sha256='0'*64)),('wrong-old-SOURCE-lineage',lambda p:p['candidateSourcePreregistration'].update(sha256='0'*64)),('wrong-owned-definition',lambda p:p['sourceCandidate'].update(sha256='0'*64))]:
 q=copy.deepcopy(pr);change(q);refuse(name,lambda:run.existing_candidate_guard(q))
for i,c in enumerate(pr['cases']):
 assert run.compiler_case(c['nativeArgv'],pr,c)
 q=c['nativeArgv'].copy();q[6]='0';refuse('wrong-guest-boundary-'+str(i),lambda:run.compiler_case(q,pr,c))
 raw=(b'{:ok true, :target :aarch64-macos, :output '+json.dumps(c['outputPath']).encode()+b', :bytes 30}\n')if c['kind']=='compile'else(b'{:ok true, :output '+json.dumps(c['outputPath']).encode()+b', :offset 0, :length 4, :arity 1}\n')
 assert parse_output(raw,c)['kind']==c['kind'];refuse('extra-output-'+str(i),lambda:parse_output(raw+b'x',c))
keys=['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','integrationFixtureProof','baselineActualProof','TCActualProof','candidateSourcePinsSHA256','candidateActualProof'];g={k:None for k in keys};g.update(status=pr['rootGOStatus'],maximumLoaderCalls=6,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=False,C2=False);assert run.go_header(g,pr,Path(pr['freshOutputRoot']))
for name,k,v in [('GO-extra','extra',True),('GO-guest','runtimeGuestAuthorized',True),('GO-C2','C2',True),('GO-retry','noRetry',False),('GO-seventh','maximumLoaderCalls',7)]:
 q=copy.deepcopy(g);q[k]=v;refuse(name,lambda:run.go_header(q,pr,Path(pr['freshOutputRoot'])))
s=importlib.util.spec_from_file_location('pure_native',D/'native-call.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);refuse('seventh-before-adapter-setup',lambda:m.call(D,Path(pr['freshOutputRoot']),pr,pr['cases'][0],[None]*6,lambda *a:None,'0'*64))
keys=sorted(pr['environment']);jr=[dict(stage='environment-admission',suppliedKeyNames=keys,runtimeExtraKeyNames=[],missingKeyNames=[],changedExpectedKeyNames=[],nativeExecKeyNames=keys,nativeExecEnvironmentExact=True)]
for i,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)],1):jr.extend([dict(index=i,limit=name,stage='before',before=[9223372036854775807]*2,desired=[soft,hard]),dict(index=i,limit=name,stage='outcome',outcome='installed',readback=[soft,hard])])
jr.append(dict(stage='exec-ready',argv=pr['cases'][0]['nativeArgv'],ASSetterRequested=False,CPUGraceHardSeconds=1801))
class J:
 def __init__(self,q):self.b=b''.join(json.dumps(r).encode()+b'\n'for r in q)
 def stat(self):return type('S',(),dict(st_size=len(self.b)))()
 def read_bytes(self):return self.b
assert m.resource_journal(J(jr),pr,pr['cases'][0]['nativeArgv'])
for name,change in [('resource-row-missing',lambda q:q.pop(4)),('finite-limit-raised',lambda q:q[3].update(before=[10,11])),('unknown-env',lambda q:q[0]['nativeExecKeyNames'].append('EXTRA'))]:
 q=copy.deepcopy(jr);change(q);refuse(name,lambda:m.resource_journal(J(q),pr,pr['cases'][0]['nativeArgv']))
for p in D.glob('*.py'):ast.parse(p.read_text())
print(json.dumps(dict(status='PASS_PURE_FIXED_AUDITED_PRODUCERS_SOURCE_COMPILER6_ONLY',fixedSourceAndCandidateReusePositive=True,fixedCompilerCases=6,refusedMutants=neg,operationalCalls=0,stageCertificateQualified=False),indent=2))
