"""Pure SOURCE controls: no native/process/thread/FD/network/resource APIs."""
from pathlib import Path
import json,copy,importlib.util,ast
from runtime import qualify,FIELDS
from callback_contract import row
from run import source_scope,go_header,input_closure
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('inert_wrapper',D/'launch-wrapper.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
def refuses(fn):
 try:fn()
 except (AssertionError,KeyError,ValueError,TypeError,IndexError):return True
 raise AssertionError('mutant admitted')
def controls():
 pr=json.loads((D/'preregistration.json').read_bytes());assert source_scope(pr)
 ip=json.loads((D/'input-pins.json').read_bytes());assert input_closure(pr,ip)
 closure=[]
 for name,k,v in [('stale-V1-count','inputFiles',155),('stale-V1-bytes','inputLogicalBytes',13280263),('count-minus-one','inputFiles',255),('bytes-minus-one','inputLogicalBytes',20913900),('boolean-count','inputFiles',True),('boolean-bytes','inputLogicalBytes',True)]:
  z=copy.deepcopy(pr);z[k]=v;assert refuses(lambda:input_closure(z,ip));closure.append(name)
 z=copy.deepcopy(ip);z.pop(next(iter(z)));assert refuses(lambda:input_closure(pr,z));closure.append('missing-registry-entry')
 z=copy.deepcopy(ip);next(iter(z.values()))['bytes']+=1;assert refuses(lambda:input_closure(pr,z));closure.append('registry-byte-corruption')
 schema=json.loads((D/'go-schema.json').read_bytes());g={k:None for k in schema['exactKeys']};g.update(status=pr['rootGOStatus'],maximumLoaderCalls=10,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,runtimeGuestAuthorized=True,C2=False,outerHostLaunchRequiresEscalation=True)
 assert go_header(g,pr,Path(pr['freshOutputRoot']))
 goRefusals=[]
 for name,mutate in [('old50-scope',lambda x:x.update(maximumLoaderCalls=50)),('C2',lambda x:x.update(C2=True)),('timing',lambda x:x.update(timingAuthorized=True)),('unknown',lambda x:x.update(extra=1)),('missing-ON-proof',lambda x:x.pop('ONActualProof')),('retry',lambda x:x.update(noRetry=False)),('wrong-output',lambda x:x.update(outputRoot='/old')),('missing-host-escalation',lambda x:x.update(outerHostLaunchRequiresEscalation=False))]:
  z=copy.deepcopy(g);mutate(z);assert refuses(lambda:go_header(z,pr,Path(pr['freshOutputRoot'])));goRefusals.append(name)
 structural=[]
 for name,mutate in [('extra-case',lambda p:p['cases'].append(p['cases'][0])),('arm-reorder',lambda p:p['cases'].__setitem__(0,p['cases'][1])),('source-change',lambda p:p['entries'][0]['source'].update(sha256='0'*64)),('profile-change',lambda p:p['cases'][0].update(profile=99)),('wrong-result',lambda p:p['cases'][0].update(expectedResult=1)),('wrong-export',lambda p:p['cases'][0].update(offset=0)),('old-ON-image',lambda p:p['images'].__setitem__('ON',p['images']['OFF'])),('fuel-expansion',lambda p:p.update(guestFuelPerCall=33554432)),('arena-expansion',lambda p:p['guestArenaCaps'].update(pairs=4194304)),('composition-on',lambda p:p.update(generalCompositionAdoptionAuthorized=True))]:
  z=copy.deepcopy(pr);mutate(z);assert refuses(lambda:source_scope(z));structural.append(name)
 assert all(w.runtime_case(c['nativeArgv'],pr,c)for c in pr['cases'])
 wrapperMutants=[]
 for name,index,value in [('wrong-offset',2,'0'),('arity-zero',3,'0'),('wrong-abi',4,'x86_64'),('effect-grant',5,'35'),('profile',6,'999'),('wrong-image',1,'/unbound.bin')]:
  c=pr['cases'][0];a=list(c['nativeArgv']);a[index]=value;assert refuses(lambda:w.runtime_case(a,pr,c));wrapperMutants.append(name)
 for name,key,val in [('fuel-off','KEXE_FUEL','off'),('arena-expanded','KEXE_PAIRS','4194304'),('extra-env','KEXE_COMMAND','1')]:
  z=copy.deepcopy(pr);z['environment'][key]=val;assert refuses(lambda:w.runtime_case(z['cases'][0]['nativeArgv'],z,z['cases'][0]));wrapperMutants.append(name)
 raw=b'{:status :ok :result 1 :fuel {:initial 16777216 :remaining 16777200} :heap {:capacity 2097152 :used 0} :string-pool {:capacity 65536 :used 0} :vectors {:capacity 4096 :used 0} :vector-items {:capacity 65536 :used 0}}\n'
 err=('KEXE_ARENA_USE {'+' '.join(':'+k+' 0'for k in FIELDS)+'}\n').encode();answer=qualify(raw,err,1);assert answer['fuelConsumed']==16 and len(answer['arena17'])==17
 decoder=[]
 for name,a,b,expected in [('extra-stdout',raw+b'0\n',err,1),('extra-stderr',raw,err+b'x',1),('wrong-fuel',raw.replace(b'16777216',b'1000000'),err,1),('unmetered',raw.replace(b':remaining 16777200}',b':remaining 16777200 :metered false}'),err,1),('arena-cap',raw.replace(b'2097152',b'4194304'),err,1),('counter-used-mismatch',raw,err.replace(b':pairs 0',b':pairs 1'),1),('wrong-Boolean',raw,err,0),('fuel-overrun',raw.replace(b'16777200',b'16777217'),err,1),('trap',raw.replace(b':status :ok :result 1',b':status :trap :exit 1'),err,1)]:
  assert refuses(lambda:qualify(a,b,expected));decoder.append(name)
 sample={'sample':2048,'ownedPGID':2147483647,'metric':'sum-ri_phys_footprint','aggregateBytes':4294967296,'thresholdBytes':4294967296,'members':[{'pid':2147483647,'start':2**64-1,'exit':0,'physicalFootprintBytes':2147483648,'uuid':'f'*32},{'pid':2147483646,'start':2**64-1,'exit':0,'physicalFootprintBytes':2147483648,'uuid':'f'*32}],'hardMemoryCapEstablished':False}
 numeric,birth=row(sample,2**64-1,2147483647,{});serialized=(json.dumps(numeric,separators=(',',':'))+'\n').encode();assert len(serialized)<=4096 and 2048*4096==8388608
 callback=[]
 for name,mutate in [('sample-overflow',lambda s:s.update(sample=2049)),('duplicate-member',lambda s:s['members'][1].update(pid=2147483647)),('changed-birth',lambda s:s['members'][0].update(start=1)),('threshold-expanded',lambda s:s.update(thresholdBytes=2**64-1)),('aggregate-wrong',lambda s:s.update(aggregateBytes=0)),('unknown-key',lambda s:s.update(foo=0)),('boolean-pid',lambda s:s['members'][0].update(pid=True)),('unknown-member-key',lambda s:s['members'][0].update(foo=0))]:
  q=copy.deepcopy(sample);mutate(q);assert refuses(lambda:row(q,1,2147483647,birth));callback.append(name)
 spec=importlib.util.spec_from_file_location('inert_native',D/'native-call.py');nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
 originalSelected=json.loads((D/'preregistration.json').read_text());assert refuses(lambda:nc.call(D,Path(originalSelected['freshOutputRoot']),originalSelected,originalSelected['cases'][0],[{}for _ in range(10)],None,'0'*64))
 keys=sorted(pr['environment']);journal=[{'stage':'environment-admission','suppliedKeyNames':keys,'runtimeExtraKeyNames':[],'missingKeyNames':[],'changedExpectedKeyNames':[],'nativeExecKeyNames':keys,'nativeExecEnvironmentExact':True}]
 for i,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',30,31)],1):journal.extend([{'index':i,'limit':name,'stage':'before','before':[9223372036854775807,9223372036854775807],'desired':[soft,hard]},{'index':i,'limit':name,'stage':'outcome','outcome':'installed','readback':[soft,hard]}])
 journal.append({'stage':'exec-ready','argv':pr['cases'][0]['nativeArgv'],'ASSetterRequested':False,'CPUGraceHardSeconds':31})
 class MemoryFile:
  def __init__(self,rows):self.b=b'\n'.join(json.dumps(r).encode()for r in rows)
  def stat(self):return type('S',(),{'st_size':len(self.b)})()
  def read_bytes(self):return self.b
 assert nc.resource_journal(MemoryFile(journal),pr,pr['cases'][0]['nativeArgv'])
 resources=[]
 for name,mutate in [('changed-env',lambda j:j[0].update(changedExpectedKeyNames=['KEXE_FUEL'])),('unknown-env',lambda j:j[0].update(runtimeExtraKeyNames=['SECRET'])),('CPU-hard-wrong',lambda j:j[4].update(readback=[30,32])),('raised-inherited-limit',lambda j:j[3].update(before=[1,2])),('unknown-row-key',lambda j:j[3].update(extra=True)),('wrong-exec',lambda j:j[5].update(argv=[]))]:
  j=copy.deepcopy(journal);mutate(j);assert refuses(lambda:nc.resource_journal(MemoryFile(j),pr,pr['cases'][0]['nativeArgv']));resources.append(name)
 from loader_grammar import interpretation
 assert all(interpretation(c['nativeArgv'])=={'typedI64':[c['profile']],'guestArgv':None,'effectiveArgc':7}for c in pr['cases'])
 assert refuses(lambda:interpretation(pr['cases'][0]['nativeArgv'][:6]+['--',str(pr['cases'][0]['profile'])]))
 assert refuses(lambda:w.runtime_case(pr['cases'][0]['nativeArgv'][:6]+['--',str(pr['cases'][0]['profile'])],pr,pr['cases'][0]))
 assert interpretation(pr['cases'][0]['nativeArgv']+['--','guest-option'])['guestArgv']==['guest-option']
 return {'status':'PASS_PURE_SOURCE_HFT_RUNTIME10_SCOPE_DECODER_WRAPPER_CALLBACK_ONLY','originalFivePairsSourcePositive':True,'completePreregistryCountGuardPositive':True,'closureRefusals':closure,'runtimeCasePositives':10,'GORefusals':goRefusals,'sourceRefusals':structural,'wrapperRefusals':wrapperMutants,'decoderRefusals':decoder,'sampleRefusals':callback,'resourceJournalRefusals':resources,'nativeCall11RefusedBeforeAPI':True,'primaryTypedLoaderGrammar10AndMisplacedSeparatorRefused':True,'actualNativeProcessThreadFDPipeGroupNetworkCalls':0,'scope':'SOURCE only; two reviews and root GO pending'}
if __name__=='__main__':print(json.dumps(controls(),indent=2))
