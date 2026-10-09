"""Pure generated-header source; C must be freshly built on selected host first."""
import hashlib,struct,json
def header(row, off, lc, fresh_c):
 def checked(b,r):
  assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
 checked(off,row['OFF']);checked(lc,row['LC'])
 # C result must be thin ARM64 dylib. Identity and recipe acceptance are independent.
 assert len(fresh_c)>=32 and fresh_c[:4]==b'\xcf\xfa\xed\xfe'
 assert struct.unpack_from('<I',fresh_c,4)[0]==0x100000c
 assert struct.unpack_from('<I',fresh_c,12)[0]==6
 def arr(n,b):return 'static const unsigned char '+n+'[] = {'+','.join(map(str,b))+'};\n'
 mask=row['nativeFeatureRequirements']['OFF']|row['nativeFeatureRequirements']['LC']
 s='#include <stddef.h>\n#include <stdint.h>\n#define KEXE_EMBEDDED 1\n#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES '+str(mask)+'ULL\n#define KEXE_EMBEDDED_ISA "aarch64"\n#define TIMING_KNOWN_IMAGES 2\n'
 s+=arr('known_baseline',off)+arr('known_candidate',lc)
 s+='static const unsigned char *const timing_known_images[] = {known_baseline,known_candidate};\n'
 s+='static const size_t timing_known_sizes[] = {'+str(len(off))+','+str(len(lc))+'};\n'
 s+='static const uint64_t timing_known_offsets[] = {'+str(row['OFF']['offset'])+','+str(row['LC']['offset'])+'};\n'
 s+='#define TIMING_KNOWN_DYLIB 1\n#define TIMING_KNOWN_C_SYMBOL '+json.dumps(row['CSymbol'])+'\n'
 s+=arr('timing_known_c_bytes',fresh_c)
 return s.encode()
