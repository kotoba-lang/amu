"""Pure SOURCE and saved-output controls only; no native/process/FD/thread/GO APIs."""
from pathlib import Path
import json,copy,ast
import run
import importlib.util
spec=importlib.util.spec_from_file_location('wrapper_control',Path(__file__).resolve().parent/'launch-wrapper.py');wrapper=importlib.util.module_from_spec(spec);spec.loader.exec_module(wrapper)
D=Path(__file__).resolve().parent;pr=run.load(D/'preregistration.json');ip=run.load(D/'input-pins.json')
assert run.registry_scope(pr,ip)and run.source_scope(pr)and run.fixture_guard(pr['ownershipIntegrationFixtureProof'],pr)
neg=[]
def refuse(name,fn):
 try:fn()
 except(AssertionError,KeyError,TypeError,ValueError,IndexError):neg.append(name)
 else:raise AssertionError('admitted mutant:'+name)
for name,key,value in [('stale-count','inputFiles',1),('bool-count','inputFiles',True),('stale-bytes','inputLogicalBytes',0),('bool-bytes','inputLogicalBytes',True),('raised-registry-cap','maximumInputFiles',512),('raised-byte-cap','maximumInputLogicalBytes',67108864)]:
 z=copy.deepcopy(pr);z[key]=value;refuse(name,lambda:run.registry_scope(z,ip))
for name,change in [('guest-fuel-changed',lambda z:z.update(guestFuelPerCall=1)),('guest-arena-changed',lambda z:z['guestArenaCaps'].update(vectors=8192)),('case-omitted',lambda z:z['cases'].pop()),('new-profile',lambda z:z['cases'][0].update(profile=42)),('wrong-ON-export',lambda z:z['cases'][1].update(offset=0)),('C2',lambda z:z.update(C2=True)),('thread-expansion',lambda z:z.update(maximumAuxiliaryThreadStarts=760)),('FD-expansion',lambda z:z.update(maximumControlledParentFDs=45))]:
 z=copy.deepcopy(pr);change(z);refuse(name,lambda:run.source_scope(z))
for c in pr['cases']:assert wrapper.allowed(c['nativeArgv'],pr)and wrapper.runtime_case(c['nativeArgv'],pr,c)
for i in [0,1,188,189]:
 c=pr['cases'][i];bad=c['nativeArgv'][:6]+['--']+c['nativeArgv'][6:];refuse('typed-guest-separator-'+str(i),lambda:wrapper.runtime_case(bad,pr,c))
z=copy.deepcopy(pr);z['qualifiedFixtureSourcePins']['sha256']='0'*64;refuse('wrong-fixture-source',lambda:run.fixture_guard(pr['ownershipIntegrationFixtureProof'],z))
z=copy.deepcopy(pr);z['qualifiedPolicySourcePins']['sha256']='0'*64;refuse('wrong-fixture-target',lambda:run.fixture_guard(pr['ownershipIntegrationFixtureProof'],z))
# Exact schema rejects missing/unknown authorization fields before any APIs.
schema=run.load(D/'go-schema.json');g={k:False for k in schema['exactKeys']};g.update(status=pr['rootGOStatus'],maximumLoaderCalls=190,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=True,C2=False,outerHostLaunchRequiresEscalation=True)
assert run.go_header(g,pr,Path(pr['freshOutputRoot']))
for name,change in [('GO-extra',lambda z:z.update(extra=True)),('GO-missing-runtime-auth',lambda z:z.pop('runtimeGuestAuthorized')),('GO-C2',lambda z:z.update(C2=True)),('GO-191',lambda z:z.update(maximumLoaderCalls=191)),('GO-timing',lambda z:z.update(timingAuthorized=True))]:
 z=copy.deepcopy(g);change(z);refuse(name,lambda:run.go_header(z,pr,Path(pr['freshOutputRoot'])))
# Saved original NS raw exercises copied strict complete output parser; no new guest.
from runtime import qualify
W=D.parent;base=W/'tc-hft-compose511-bound-hoist-original-ns-runtime10-source-v2-20261009/run-outputs/nsichneu-OFF-n2';out=base.with_suffix('.stdout').read_bytes();err=base.with_suffix('.stderr').read_bytes();r=qualify(out,err,1);assert r['result']==1 and r['fuelConsumed']==527 and len(r['arena17'])==17
for name,ob,eb in [('stdout-extra',out+b'foreign\n',err),('stderr-extra',out,err+b'foreign\n'),('stdout-truncated',out[:-1],err),('missing-arena',out,b'')]:refuse(name,lambda:qualify(ob,eb,1))
for p in D.glob('*.py'):ast.parse(p.read_bytes())
assert len(pr['cases'])==190 and len({c['label']for c in pr['cases']})==190 and len({tuple(c['nativeArgv'])for c in pr['cases']})==190
assert not Path(pr['freshOutputRoot']).exists()
text=(D/'run.py').read_text();assert text.index("finally:save(O/'terminal.json'")<text.index("status':'COMPLETE_HFT_G4_HELD_V6")
print(json.dumps({'status':'PASS_PURE_SOURCE_HFT_G4_HELD_V6_RUNTIME190_ONLY','positiveRuntimeGrammarCases':190,'refusals':neg,'sourceClosurePositive':True,'savedNSParserPositive':True,'nativeCalls':0,'actualFDThreadProcessCalls':0},indent=2))

