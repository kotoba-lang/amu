from pathlib import Path
import re,json,hashlib
D=Path(__file__).resolve().parent;R=D/'batch-source';aes=(R/'bench/embench/batch-ports/nettle-aes.kotoba').read_text();crc=(R/'bench/embench/batch-ports/crc32.kotoba').read_text();MASK=(1<<32)-1
def vec(n):
 return sum((list(map(int,re.search(r'\(def '+re.escape(n)+r'-'+str(i)+r' \[([^]]+)\]',aes)[1].split())) for i in [0,1]),[])
def gf(a,b):
 r=0
 for i in range(8):
  if b&1:r^=a
  a=((a<<1)^ (0x11b if a&128 else 0))&255;b>>=1
 return r
def power(a,n):
 r=1
 while n:
  if n&1:r=gf(r,a)
  a=gf(a,a);n>>=1
 return r
def rol8(a,n):return ((a<<n)|(a>>(8-n)))&255
def rol32(a,n):return ((a<<n)|(a>>(32-n)))&MASK
s=[(lambda a:a^rol8(a,1)^rol8(a,2)^rol8(a,3)^rol8(a,4)^99)(power(i,254) if i else 0) for i in range(256)];inv=[s.index(i) for i in range(256)]
assert vec('enc-sbox')==s and vec('dec-sbox')==inv
enc0=[gf(x,2)|(x<<8)|(x<<16)|(gf(x,3)<<24) for x in s];dec0=[gf(x,14)|(gf(x,9)<<8)|(gf(x,13)<<16)|(gf(x,11)<<24) for x in inv];mt=[gf(x,14)|(gf(x,9)<<8)|(gf(x,13)<<16)|(gf(x,11)<<24) for x in range(256)]
for i in range(4):assert vec('enc-t'+str(i))==[rol32(x,8*i) if i else x for x in enc0];assert vec('dec-t'+str(i))==[rol32(x,8*i) if i else x for x in dec0]
assert vec('mt')==mt
line=next(l for l in crc.splitlines() if l.startswith('(defn- table-at'));tables=[list(map(int,x.split())) for x in re.findall(r'\[([\d\s]+)\]',line)];table=sum(tables,[]);assert len(table)==256
def reflected(v,poly=0xedb88320):
 for _ in range(8):v=(v>>1)^(poly if v&1 else 0)
 return v
def old(c,d,t=table):return t[(c^d)&255]^(c>>8)
def hw(c,d,poly=0xedb88320):return reflected((c&MASK)^(d&255),poly)
assert table==[reflected(i) for i in range(256)]
# Both maps are GF(2)-linear for32-bit state+8-bitdata. Equality on all40 basis vectors andzero establishes this model law on the finite domain.
basis=[(1<<i,0) for i in range(32)]+[(0,1<<i) for i in range(8)]+[(0,0)];assert all(old(c,d)==hw(c,d) for c,d in basis)
faults=[{'fault':'unbounded high accumulator','old':old(1<<40,0),'replacement':hw(1<<40,0)},{'fault':'Castagnoli instruction polynomial','old':old(0,1),'replacement':hw(0,1,0x82f63b78)}];mut=table.copy();mut[1]^=1;faults.append({'fault':'mutable/different table','old':old(0,1,mut),'replacement':hw(0,1)});assert all(x['old']!=x['replacement'] for x in faults)
# A round key must be XORed after SubBytes/ShiftRows/MixColumns for this source T-table round; AESE has itskey before S-box. Evenonebyte detectswrongphase.
keyfault={'fault':'key XOR before instead of after substitution','sourceByte':s[0]^1,'wrongByte':s[1]};assert keyfault['sourceByte']!=keyfault['wrongByte']
out={'status':'PASS excluded finite source table/field model certificates; no hardware execution or compiler implementation','crc':{'tableEntries':256,'polynomialReflected':'0xedb88320','polynomialNormal':'0x04c11db7','basisAndZeroCases':41,'law':'u32(c), byte(d): T[(c XOR d)&255] XOR(c>>8) ==8 IEEE reflected shift/XOR steps. LinearGF2 basis completeness explicit; numeric addition is not used.','originRequired':'c remainsu32, inputlow8, tableexactimmutable; no CRC32C substitution','modelFaults':faults},'aes':{'fullTableElementsVerified':2816,'encSbox256':True,'decSbox256':True,'encTables4x256':True,'decTables4x256':True,'inverseMixTable256':True,'sourceByteOrder':'little-endian columnwords: lowbyte row0,T0 coefficients2/1/1/3; Ti=ROL32(T0,8i)','keyPhaseFault':keyfault,'notProved':'Actual NEON instruction mapping, allCFG/liveness/arena/fuel contracts and machine behavior remain future native proof obligations.'}}
(D/'finite-laws.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
