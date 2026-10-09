#!/usr/bin/env python3
# BOOTSTRAP-TOOL: Darwin host CPU tick evidence around a runner invocation.
import ctypes,sys,time,math
_lib=None
_host=None

def snapshot():
 global _lib,_host
 if sys.platform!='darwin':raise RuntimeError('Darwin CPU counters required')
 if _lib is None:
  _lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib')
  _lib.mach_host_self.restype=ctypes.c_uint32
  _lib.mach_host_self.argtypes=[]
  _lib.host_processor_info.restype=ctypes.c_int
  _lib.host_processor_info.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.POINTER(ctypes.c_int32)),ctypes.POINTER(ctypes.c_uint32)]
  _lib.vm_deallocate.restype=ctypes.c_int
  _lib.vm_deallocate.argtypes=[ctypes.c_uint32,ctypes.c_uint64,ctypes.c_uint64]
  _host=_lib.mach_host_self()
 count=ctypes.c_uint32();processors=ctypes.c_uint32();data=ctypes.POINTER(ctypes.c_int32)()
 code=_lib.host_processor_info(_host,2,ctypes.byref(processors),ctypes.byref(data),ctypes.byref(count))
 if code!=0:raise RuntimeError('PROCESSOR_CPU_LOAD_INFO failed: '+str(code))
 try:
  if not data or processors.value==0 or count.value!=4*processors.value:raise RuntimeError('invalid processor CPU array')
  ticks=[sum(int(data[i*4+j])&0xffffffff for i in range(processors.value))&0xffffffff for j in range(4)]
  return {'ticks':ticks,'monotonicNs':time.monotonic_ns(),'processors':processors.value,'api':'host_processor_info/PROCESSOR_CPU_LOAD_INFO'}
 finally:
  if data:
   task=ctypes.c_uint32.in_dll(_lib,'mach_task_self_').value
   code=_lib.vm_deallocate(task,ctypes.cast(data,ctypes.c_void_p).value,count.value*ctypes.sizeof(ctypes.c_int32))
   if code!=0:raise RuntimeError('CPU array deallocation failed: '+str(code))

def interval(before,after):
 for point in (before,after):
  if len(point['ticks'])!=4 or any(type(x)!=int or not 0<=x<=0xffffffff for x in point['ticks']):raise ValueError('invalid CPU ticks')
 if after['monotonicNs']<=before['monotonicNs']:raise ValueError('nonpositive CPU envelope')
 delta=[(b-a)&0xffffffff for a,b in zip(before['ticks'],after['ticks'])];total=sum(delta)
 if total==0:raise ValueError('CPU counters did not advance')
 return {'before':before,'after':after,'deltaTicks':delta,'idlePercent':100*delta[2]/total,'envelopeNs':after['monotonicNs']-before['monotonicNs'],'scope':'runner invocation including process setup and warmup, enclosing timed interval'}

def background_activity(activity,child_cpu_ns,cpu_count):
 # The measured child is deliberately busy; retain raw host idle separately.
 if type(child_cpu_ns)!=int or child_cpu_ns<0:raise ValueError('invalid child CPU time')
 if type(cpu_count)!=int or cpu_count<=0:raise ValueError('invalid CPU count')
 envelope=activity['envelopeNs'];idle=activity['idlePercent']
 if envelope<=0 or not math.isfinite(idle) or not 0<=idle<=100:raise ValueError('invalid CPU envelope')
 measured_percent=100*child_cpu_ns/(envelope*cpu_count)
 if measured_percent>100:raise ValueError('child CPU exceeds host capacity')
 return {**activity,'childCpuNs':child_cpu_ns,'logicalCpuCount':cpu_count,
         'estimatedBackgroundIdlePercent':min(100,idle+measured_percent),
         'backgroundEstimateScope':'raw tick idle plus waited child user/system CPU share of enclosing host capacity'}
