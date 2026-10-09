"""Pure immutable per-workload header generator. Does not build or execute anything."""
import hashlib,json,struct
from pathlib import PurePosixPath
def receipt(b,r):
 assert isinstance(r,dict) and len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
def relative(p):
 q=PurePosixPath(p);assert not q.is_absolute() and '..' not in q.parts and q.parts and str(q)==p
 return p
def header(row,off,on,c,fresh_c_proof):
 for arm,b in [('OFF',off),('ON',on)]:
  receipt(b,row[arm]['native']);assert type(row[arm]['offset']) is int and 0<=row[arm]['offset']<len(b) and row[arm]['offset']%4==0
 assert type(row['workload']) is str and row['workload'] and all(x in 'abcdefghijklmnopqrstuvwxyz0123456789-' for x in row['workload'])
 assert row['symbol'] in ('bench','batch')
 assert fresh_c_proof['status']=='PASS_INDEPENDENT_FRESH_CURRENT19_C_BUILD_SOURCE_IDENTITY_ONLY'
 assert fresh_c_proof['workload']==row['workload'] and fresh_c_proof['symbol']==row['symbol'] and fresh_c_proof['bridgeABI']=='I64_8ARGS'
 receipt(c,fresh_c_proof['artifact'])
 assert len(c)>=32 and c[:4]==b'\xcf\xfa\xed\xfe' and struct.unpack_from('<I',c,4)[0]==0x100000c and struct.unpack_from('<I',c,12)[0]==6
 def arr(n,b):return 'static const unsigned char '+n+'[]={'+','.join(map(str,b))+'};\n'
 stem='inputs/'+row['workload']+'/'
 for path in [stem+'OFF.bin',stem+'ON.bin',stem+'C.dylib']:relative(path)
 s='#include <stdint.h>\n#include <stddef.h>\n#define TIMING_PACKET_ISA "aarch64"\n#define TIMING_MAX_N '+str(max(row['profiles']))+'ULL\n#define TIMING_C_SYMBOL '+json.dumps(row['symbol'])+'\n#define TIMING_C_PATH '+json.dumps(stem+'C.dylib')+'\n'
 s+=arr('timing_off',off)+arr('timing_on',on)+arr('timing_c_bytes',c)
 s+='static const unsigned char *const timing_images[]={timing_off,timing_on};\n'
 s+='static const size_t timing_sizes[]={sizeof(timing_off),sizeof(timing_on)};\n'
 s+='static const uint64_t timing_offsets[]={'+str(row['OFF']['offset'])+','+str(row['ON']['offset'])+'};\n'
 s+='static const char *const timing_paths[]={'+json.dumps(stem+'OFF.bin')+','+json.dumps(stem+'ON.bin')+'};\n'
 return s.encode()
