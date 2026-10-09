"""Import-inert owned-group memory adapter. No scans outside the passed owned group."""
import ctypes,os,sys
THRESHOLD=4294967296
CONTEXT_VERSION='owned-group-sampling-failure-context-v1'
class SamplingFault(Exception):
 def __init__(self,context):super().__init__(str(context));self.context=context

class Refusal(Exception):pass
def need(x,m):
 if not x:raise Refusal(m)
class RUsageV0(ctypes.Structure):
 _fields_=[('ri_uuid',ctypes.c_uint8*16)]+[(n,ctypes.c_uint64)for n in ['ri_user_time','ri_system_time','ri_pkg_idle_wkups','ri_interrupt_wkups','ri_pageins','ri_wired_size','ri_resident_size','ri_phys_footprint','ri_proc_start_abstime','ri_proc_exit_abstime']]
class DarwinOwnedGroupAPI:
 def __init__(self,invocation):
  need(sys.platform=='darwin','Darwin API required')
  need(ctypes.sizeof(ctypes.c_int)==4 and ctypes.sizeof(RUsageV0)==96,'pinned SDK V0 ABI')
  self.invocation=invocation;self.queryOrdinal=0;self.lastAttempt=None;self.getpgid=os.getpgid
  self.lib=ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
  self.listfn=self.lib.proc_listpgrppids;self.listfn.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int];self.listfn.restype=ctypes.c_int
  self.usagefn=self.lib.proc_pid_rusage;self.usagefn.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_void_p];self.usagefn.restype=ctypes.c_int
 def attempt(self,stage,pid,fn,*args):
  self.queryOrdinal+=1;self.lastAttempt={'contextVersion':CONTEXT_VERSION,'typedOrigin':'fresh-owned-group-api-v1','invocation':self.invocation,'stage':stage,'pid':pid,'queryOrdinal':self.queryOrdinal}
  try:return fn(*args)
  except OSError as ex:
   raise SamplingFault(dict(self.lastAttempt,errno=ex.errno,failureClass='kernel-oserror'))from ex
 def return_failure(self,errno):
  raise SamplingFault(dict(self.lastAttempt,errno=errno,failureClass='kernel-failed-return'))
 def group(self,owned):
  need(self.attempt('leader-getpgid',owned,self.getpgid,owned)==owned,'owned leader lost group identity')
  pids=(ctypes.c_int*4)();ctypes.set_errno(0);count=self.attempt('group-list',owned,self.listfn,owned,ctypes.byref(pids),ctypes.sizeof(pids));err=ctypes.get_errno()
  if count<1 and err: self.return_failure(err)
  # libproc wrapper returns PID COUNT, not bytes; buffer exhaustion refuses.
  need(1<=count<=2 and err==0,'owned group inventory failed/extra/truncated')
  return list(pids[:count])
 def member(self,pid,owned):
  need(self.attempt('member-getpgid',pid,self.getpgid,pid)==owned,'member left owned group')
  row=RUsageV0();ctypes.set_errno(0);rc=self.attempt('member-rusage',pid,self.usagefn,pid,0,ctypes.byref(row));err=ctypes.get_errno()
  if rc!=0 and err: self.return_failure(err)
  need(rc==0 and err==0,'member rusage read failure')
  if int(row.ri_proc_exit_abstime)>0:
   raise SamplingFault(dict(self.lastAttempt,errno=0,failureClass='kernel-observed-exited',observedBirth=int(row.ri_proc_start_abstime),observedExit=int(row.ri_proc_exit_abstime)))
  return {'pid':pid,'start':int(row.ri_proc_start_abstime),'exit':int(row.ri_proc_exit_abstime),'physicalFootprintBytes':int(row.ri_phys_footprint),'uuid':bytes(row.ri_uuid).hex()}
class OwnedGroupSampler:
 def __init__(self,api,owned_pid):
  need(type(owned_pid)is int and 0<owned_pid<2**31,'owned PID bound')
  self.api=api;self.owned=owned_pid;self.starts={};self.samples=0
 def inventory(self):
  ids=self.api.group(self.owned)
  need(1<=len(ids)<=2 and all(type(p)is int and 0<p<2**31 for p in ids),'finite inventory')
  need(len(set(ids))==len(ids)and self.owned in ids,'unique inventory contains owner')
  return sorted(ids)
 def sample(self):
  need(self.samples<90502,'finite sample budget');before=self.inventory();records=[]
  for pid in before:
   q=self.api.member(pid,self.owned)
   need(q['pid']==pid and type(q['start'])is int and q['start']>0 and q['exit']==0,'live PID birth identity')
   need(type(q['physicalFootprintBytes'])is int and 0<=q['physicalFootprintBytes']<2**64,'footprint width')
   need(pid not in self.starts or self.starts[pid]==q['start'],'PID reused')
   records.append(q)
  need(self.inventory()==before,'membership changed across sample')
  for q in records:
   again=self.api.member(q['pid'],self.owned)
   need(again['pid']==q['pid']and again['start']==q['start']and again['exit']==0,'member identity changed across sample')
  new=dict(self.starts);new.update({q['pid']:q['start']for q in records});need(len(new)<=2,'unexpected lifetime process replacement')
  total=sum(q['physicalFootprintBytes']for q in records);need(total<=THRESHOLD,'soft aggregate physical-footprint threshold exceeded')
  self.starts=new;self.samples+=1
  return {'sample':self.samples,'ownedPGID':self.owned,'metric':'sum-ri_phys_footprint','aggregateBytes':total,'thresholdBytes':THRESHOLD,'members':records,'hardMemoryCapEstablished':False}
