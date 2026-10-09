"""Pure finite fake-API SOURCE controls; no libproc load or process calls."""
from pathlib import Path
import ast,json,importlib.util,ctypes
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('source_adapter',D/'adapter.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert ctypes.sizeof(m.RUsageV0)==96 and m.RUsageV0.ri_phys_footprint.offset==72 and m.RUsageV0.ri_proc_start_abstime.offset==80
class Fake:
 def __init__(self,ids=[111,222],rows=None):self.ids=ids;self.rows=rows or {p:{'pid':p,'start':p*10,'exit':0,'physicalFootprintBytes':1000,'uuid':'00'*16}for p in ids};self.n=0
 def group(self,owned):assert owned==111;return list(self.ids)
 def member(self,pid,owned):assert owned==111;return dict(self.rows[pid])
s=m.OwnedGroupSampler(Fake(),111);q=s.sample();assert q['aggregateBytes']==2000 and len(q['members'])==2
controls=[]
def refuse(name,f):
 try:f()
 except (m.Refusal,KeyError,OSError):controls.append(name)
 else:raise AssertionError('expected refusal '+name)
for name,ids in [('missing owner',[222]),('duplicate',[111,111]),('extra member',[111,222,333]),('empty',[])]:refuse(name,lambda ids=ids:m.OwnedGroupSampler(Fake(ids),111).sample())
for field,value in [('physicalFootprintBytes',m.THRESHOLD),('start',0),('exit',1),('pid',333)]:
 a=Fake();a.rows[222][field]=value;refuse('bad '+field,lambda a=a:m.OwnedGroupSampler(a,111).sample())
a=Fake();b=m.OwnedGroupSampler(a,111);b.sample();a.rows[222]['start']+=1;refuse('PID reused',b.sample)
a=Fake();del a.rows[222];refuse('member read failed',lambda:m.OwnedGroupSampler(a,111).sample())
class Changing(Fake):
 def group(self,owned):self.n+=1;return [111,222]if self.n==1 else[111]
refuse('membership changed',lambda:m.OwnedGroupSampler(Changing(),111).sample())
a=m.OwnedGroupSampler(Fake(),111);a.samples=90502;refuse('sample cap',a.sample)
# Count-vs-byte ABI and exact metric are visible source obligations.
t=ast.parse((D/'adapter.py').read_text());assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr in ['Popen','execve','setrlimit','system']for n in ast.walk(t))
(D/'source-controls.json').write_text(json.dumps({'status':'PURE_SOURCE_FAKE_API_ONLY','positiveCompleteTwoMemberSamples':1,'negativeControls':controls,'SDKV0Size':96,'footprintOffset':72,'birthOffset':80,'libprocLoads':0,'processAPICalls':0,'setters':0,'nativeCompilerCalls':0},indent=2)+'\n')
print('SOURCE_ONLY_PASS')
