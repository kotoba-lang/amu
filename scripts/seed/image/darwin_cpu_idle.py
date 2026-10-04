#!/usr/bin/env python3
# BOOTSTRAP-TOOL: Darwin host CPU tick evidence around a runner invocation.
import ctypes,sys,time
_lib=None
_host=None

def snapshot():
 global _lib,_host
 if sys.platform!='darwin':raise RuntimeError('Darwin CPU counters required')
 if _lib is None:
  _lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib')
  _lib.mach_host_self.restype=ctypes.c_uint32
  _lib.mach_host_self.argtypes=[]
  _lib.host_statistics.restype=ctypes.c_int
  _lib.host_statistics.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.POINTER(ctypes.c_int32),ctypes.POINTER(ctypes.c_uint32)]
  _host=_lib.mach_host_self()
 ticks=(ctypes.c_int32*4)();count=ctypes.c_uint32(4)
 code=_lib.host_statistics(_host,3,ticks,ctypes.byref(count))
 if code!=0 or count.value!=4:raise RuntimeError('HOST_CPU_LOAD_INFO failed: '+str((code,count.value)))
 return {'ticks':[int(x)&0xffffffff for x in ticks],'monotonicNs':time.monotonic_ns()}

def interval(before,after):
 for point in (before,after):
  if len(point['ticks'])!=4 or any(type(x)!=int or not 0<=x<=0xffffffff for x in point['ticks']):raise ValueError('invalid CPU ticks')
 if after['monotonicNs']<=before['monotonicNs']:raise ValueError('nonpositive CPU envelope')
 delta=[(b-a)&0xffffffff for a,b in zip(before['ticks'],after['ticks'])];total=sum(delta)
 if total==0:raise ValueError('CPU counters did not advance')
 return {'before':before,'after':after,'deltaTicks':delta,'idlePercent':100*delta[2]/total,'envelopeNs':after['monotonicNs']-before['monotonicNs'],'scope':'runner invocation including process setup and warmup, enclosing timed interval'}
