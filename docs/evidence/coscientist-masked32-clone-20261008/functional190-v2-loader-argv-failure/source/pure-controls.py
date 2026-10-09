"""Pure source controls; no process, pipe, FD, thread, sampler or network calls."""
from pathlib import Path
import json,copy,importlib.util
from runtime import qualify,FIELDS
from callback_contract import row
from run import source_scope
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('inert_wrapper',D/'launch-wrapper.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
def refuses(fn):
 try:fn()
 except (AssertionError,KeyError,ValueError,TypeError):return True
 raise AssertionError('mutant admitted')
def controls():
 pr=json.loads((D/'preregistration.json').read_text());proofs=[json.loads(Path(pr[k]['path']).read_text())for k in ['OFFActualProof','TCActualProof','C95Oracle']]
 assert source_scope(pr,*proofs)
 assert all(w.runtime_case(c['nativeArgv'],pr,c)for c in pr['cases'])
 wrapperMutants=[]
 for name,index,value in [('wrong-offset',2,'0'),('arity-zero',3,'0'),('wrong-abi',4,'x86_64'),('effect-grant',5,'35'),('profile-substitution',7,'999'),('wrong-image',1,'/unbound.bin')]:
  c=pr['cases'][0];a=list(c['nativeArgv']);a[index]=value;assert refuses(lambda:w.runtime_case(a,pr,c));wrapperMutants.append(name)
 for name,key,val in [('fuel-off','KEXE_FUEL','off'),('arena-expanded','KEXE_PAIRS','4194304'),('extra-key','KEXE_COMMAND','1')]:
  p=copy.deepcopy(pr);p['environment'][key]=val;assert refuses(lambda:w.runtime_case(p['cases'][0]['nativeArgv'],p,p['cases'][0]));wrapperMutants.append(name)
 structural=[]
 for name,mutate in [('source-digest',lambda p:p['entries'][0]['source'].update(sha256='0'*64)),('profile-change',lambda p:p['entries'][0]['iterations'].__setitem__(0,99)),('arm-reorder',lambda p:p['cases'].__setitem__(0,p['cases'][1])),('export-offset',lambda p:p['cases'][0].update(offset=0)),('oracle-result',lambda p:p['cases'][0].update(expectedResult=1))]:
  p=copy.deepcopy(pr);mutate(p);assert refuses(lambda:source_scope(p,*proofs));structural.append(name)
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
 return {'status':'PASS_PURE_SOURCE_SCOPE_DECODER_WRAPPER_CALLBACK_ONLY','whole190CaseScopePositive':True,'runtimeCasePositives':190,'structuralRefusals':structural,'wrapperRefusals':wrapperMutants,'decoderPositive':answer,'decoderRefusals':decoder,'sampleMaximumWidthRowBytes':len(serialized),'sampleRefusals':callback,'resourceJournalPositive':True,'resourceJournalRefusals':resources,'actualNativeProcessThreadFDPipeGroupNetworkCalls':0,'remainingOperationalPrerequisites':['two exact source reviews','root GO'],'scope':'SOURCE only; no actual lifecycle or memory/performance qualification'}
if __name__=='__main__':print(json.dumps(controls(),indent=2))
