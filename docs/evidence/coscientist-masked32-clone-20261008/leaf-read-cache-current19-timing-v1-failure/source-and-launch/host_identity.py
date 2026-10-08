"""Fresh Darwin identity reads via libc; import performs no API invocation."""
import ctypes,os,sys
from ledger import need,H
from pathlib import Path
def current(expected):
 need(sys.platform=='darwin' and os.uname().machine=='arm64','native selected Darwin arm64 host')
 lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib');lib.sysctlbyname.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p,ctypes.c_size_t];lib.sysctlbyname.restype=ctypes.c_int
 def read(name,integer=False):
  b=ctypes.create_string_buffer(4096);n=ctypes.c_size_t(4096);need(lib.sysctlbyname(name.encode(),b,ctypes.byref(n),None,0)==0 and 0<n.value<=4096,'fresh sysctl '+name)
  if integer:need(n.value==4,'sysctl int32');return int.from_bytes(b.raw[:4],sys.byteorder,signed=True)
  return b.raw[:n.value].rstrip(b'\0').decode('utf-8')
 values={k:read(k) for k in ['kern.osproductversion','kern.osversion','kern.hostname','machdep.cpu.brand_string']}
 for k in ['hw.logicalcpu','hw.optional.arm.FEAT_CRC32','hw.optional.arm.FEAT_AES']:values[k]=read(k,True)
 need(values['kern.osproductversion']==expected['OS'] and values['kern.osversion']==expected['OSBuild'],'accepted exact OS/build')
 need(values['hw.optional.arm.FEAT_CRC32']==values['hw.optional.arm.FEAT_AES']==1 and 1<=values['hw.logicalcpu']<=256,'fresh CPU eligibility')
 need(str(Path(expected['SDK']).resolve(strict=True))==expected['SDK'],'canonical accepted SDK root')
 return values

def compiler_refs(expected):
 refs=[]
 for p,h in {expected['compiler']:expected['compilerSHA256'],'/usr/bin/clang':expected['usrBinClangSHA256'],**expected['SDKSettings']}.items():
  q=Path(p);need(q.is_file()and not q.is_symlink(),'accepted regular compiler/SDKSettings')
  refs.append(dict(path=p,bytes=q.stat().st_size,sha256=h))
 need(len(refs)<=4 and sum(r['bytes']for r in refs)<=512*1024**2,'separate explicit bounded hostidentity4/512MiB')
 return refs
