"""Pure current G4 full19 metadata/ABI/parser/refusal controls; no guest operations."""
from pathlib import Path
import json,copy,ast,importlib.util
import run
from loader_grammar import interpretation
from runtime import qualify,FIELDS
D=Path(__file__).resolve().parent;p=json.loads((D/'preregistration.json').read_bytes());neg=[]
def refuse(n,f):
 try:f()
 except (AssertionError,KeyError,IndexError,TypeError,ValueError):neg.append(n)
 else:raise AssertionError('admitted mutant:'+n)
assert run.source_scope(p)
mutants=[('changed-G4',lambda q:q['G4Producer']['native'].update(sha256='0'*64)),('old-G1-substitute',lambda q:q['G4Producer']['native'].update(sha256='e8746fa1714bc63cfe347edb58cbff549ca6e923346ee08525e1acc155ab283e')),('changed-proof',lambda q:q['G4Original19ActualProof'].update(sha256='0'*64)),('changed-completion',lambda q:q['G4Original19Completion'].update(sha256='0'*64)),('changed-fixedpoint',lambda q:q['FixedpointActualProof'].update(sha256='0'*64)),('changed-C-oracle',lambda q:q['C95Oracle'].update(sha256='0'*64)),('changed-loader',lambda q:q['loaderArtifact'].update(sha256='0'*64)),('omitted-workload',lambda q:q['entries'].pop()),('profile-change',lambda q:q['entries'][0]['iterations'].append(64)),('source-body-change',lambda q:q['entries'][0]['source'].update(sha256='0'*64)),('symbol-change',lambda q:q['entries'][0].update(symbol='wrong')),('case191',lambda q:q['cases'].append(q['cases'][0])),('case-missing',lambda q:q['cases'].pop()),('case-reordered',lambda q:q['cases'].reverse()),('wrong-result',lambda q:q['cases'][0].update(expectedResult=99)),('wrong-offset',lambda q:q['cases'][0].update(offset=q['cases'][0]['offset']+4)),('wrong-fuel',lambda q:q['environment'].update(KEXE_FUEL='off')),('wrong-arena',lambda q:q['environment'].update(KEXE_VECTORS='8192')),('C2-enabled',lambda q:q.update(C2=True)),('timing-on',lambda q:q.update(timingAuthorized=True)),('adoption-on',lambda q:q.update(generalCandidateAdoptionQualified=True)),('clobber-qualified',lambda q:q.update(fullClobberCertificateQualified=True)),('no-hostprofile',lambda q:q['operationalEnvironment'].update(requiresOuterHostEscalation=False)),('sandbox-weakened',lambda q:q['operationalEnvironment'].update(loaderSandboxWeakeningAuthorized=True))]
for n,change in mutants:
 q=copy.deepcopy(p);change(q);refuse(n,lambda:run.source_scope(q))
for i,c in enumerate(p['cases']):
 assert interpretation(c['nativeArgv'])==dict(typedI64=[c['profile']],guestArgv=None,effectiveArgc=7)
 refuse('wrong-typed-separator-'+str(i),lambda c=c:interpretation(c['nativeArgv'][:6]+['--']+c['nativeArgv'][6:]))
proofs=['OFFActualProof','G4Original19ActualProof','C95Oracle','C95OracleProof','integrationFixtureProof','FixedpointActualProof'];keys=['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews']+proofs;g={k:None for k in keys};g.update(status=p['rootGOStatus'],maximumLoaderCalls=190,outputRoot=p['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=True,C2=False,outerHostLaunchRequiresEscalation=True);assert run.go_header(g,p,Path(p['freshOutputRoot']))
for n,k,v in [('GO-case191','maximumLoaderCalls',191),('GO-retry','noRetry',False),('GO-timing','timingAuthorized',True),('GO-C2','C2',True),('GO-no-host','outerHostLaunchRequiresEscalation',False),('GO-extra','extra',True)]:
 q=copy.deepcopy(g);q[k]=v;refuse(n,lambda:run.go_header(q,p,Path(p['freshOutputRoot'])))
a={k:0 for k in FIELDS};a.update(vectors=1,**{'vector-items':1,'heap-bytes':24});err=('KEXE_ARENA_USE {'+' '.join(':'+k+' '+str(a[k])for k in FIELDS)+'}\n').encode();raw=b'{:status :ok :result 3 :fuel {:initial 16777216 :remaining 16777210} :heap {:capacity 2097152 :used 0} :string-pool {:capacity 65536 :used 0} :vectors {:capacity 4096 :used 1} :vector-items {:capacity 65536 :used 1}}\n';assert qualify(raw,err,3)['fuelConsumed']==6
for n,o,e,x in [('extra-stdout',raw+b'x',err,3),('extra-stderr',raw,err+b'x',3),('wrong-result',raw,err,1),('unmetered',raw.replace(b':remaining 16777210}',b':remaining 16777210 :metered false}'),err,3),('wrong-arena',raw,err.replace(b':vectors 1',b':vectors 2'),3)]:refuse(n,lambda:qualify(o,e,x))
s=importlib.util.spec_from_file_location('pure_native',D/'native-call.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);refuse('call191-before-any-API',lambda:m.call(D,Path(p['freshOutputRoot']),p,p['cases'][0],[None]*190,lambda *a:None,'0'*64))
for f in D.glob('*.py'):ast.parse(f.read_text())
print(json.dumps(dict(status='PASS_PURE_G4_ORIGINAL19_RUNTIME190_SOURCE_ABI_REFUSAL_ONLY',positiveSourceScope=True,typedArgvCases=190,refusedMutants=neg,operationalCalls=0),indent=2))
