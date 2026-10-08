import ctypes,os,time,json,subprocess,collections
u=os.uname();out=dict(hostname=u.nodename,OS=u.sysname,architecture=u.machine,timingQualified=False)
if u.sysname!='Darwin' or u.machine!='arm64':
 print(json.dumps(out));raise SystemExit(0)
lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib')
lib.sysctlbyname.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p,ctypes.c_size_t]
def info(k):
 b=ctypes.create_string_buffer(4096);n=ctypes.c_size_t(4096);assert lib.sysctlbyname(k.encode(),b,ctypes.byref(n),None,0)==0
 return b.raw[:n.value].rstrip(b'\0').decode()
lib.mach_host_self.restype=ctypes.c_uint32;lib.host_processor_info.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.POINTER(ctypes.c_int32)),ctypes.POINTER(ctypes.c_uint32)]
lib.vm_deallocate.argtypes=[ctypes.c_uint32,ctypes.c_uint64,ctypes.c_uint64]
def ticks():
 n=ctypes.c_uint32();cp=ctypes.c_uint32();d=ctypes.POINTER(ctypes.c_int32)();assert lib.host_processor_info(lib.mach_host_self(),2,ctypes.byref(cp),ctypes.byref(d),ctypes.byref(n))==0
 assert 1<=cp.value<=256 and n.value==4*cp.value
 try:return [sum(int(d[4*i+j])&0xffffffff for i in range(cp.value))&0xffffffff for j in range(4)],cp.value
 finally:assert lib.vm_deallocate(ctypes.c_uint32.in_dll(lib,'mach_task_self_').value,ctypes.cast(d,ctypes.c_void_p).value,n.value*4)==0
out.update(OSVersion=info('kern.osproductversion'),OSBuild=info('kern.osversion'),CPU=info('machdep.cpu.brand_string'))
a,cores=ticks();start=time.monotonic();lb=os.getloadavg();time.sleep(10);b,cores2=ticks();la=os.getloadavg();elapsed=time.monotonic()-start;delta=[(y-x)&0xffffffff for x,y in zip(a,b)];assert sum(delta)>0 and cores==cores2
out.update(logicalCores=cores,loadBefore=lb,loadAfter=la,idlePercent=100*delta[2]/sum(delta),ticksBefore=a,ticksAfter=b,deltaTicks=delta,CPUIntervalSeconds=elapsed)
p=subprocess.run(['/bin/ps','-axo','comm=,pcpu='],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=3);assert len(p.stdout)<=65536 and len(p.stderr)<=1024 and p.returncode==0
counts=collections.Counter();other=0
for row in p.stdout.decode().splitlines():
 try:name,cpu=row.rsplit(None,1);cpu=float(cpu);name=os.path.basename(name)
 except ValueError:continue
 if cpu>=1:
  if name in ['node','python3','Python','clang','amu','java','Google Chrome','Code']:counts[name]+=1
  else:other+=1
out.update(busyProcessThresholdCPUPercent=1,busySafeCommandCounts=dict(counts),busyOtherProcesses=other,processArgumentsRead=False,remoteSurveyChildren=1,quietSurveyEligible=max(lb[0],la[0])<=4 and out['idlePercent']>=90)
print(json.dumps(out))
