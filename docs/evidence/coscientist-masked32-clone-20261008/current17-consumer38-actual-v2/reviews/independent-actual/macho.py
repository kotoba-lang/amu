import struct
# Independent Mach-O load-command and symbol-definition decoder; no dylib loading.
def macho(b,symbol):
 assert len(b)<=16777216 and b[:4]==bytes.fromhex('cffaedfe');_,cpu,sub,typ,ncmd,cmdbytes,flags,res=struct.unpack_from('<8I',b);assert cpu==0x100000c and typ==2 and 1<=ncmd<=128 and cmdbytes<=65536
 pos=32; syms=None; sections=[]; libs=[]
 for _ in range(ncmd):
  cmd,size=struct.unpack_from('<II',b,pos);assert size>=8 and size%8==0 and pos+size<=32+cmdbytes
  assert cmd not in {0x18,0x80000018,0x1f,0x8000001f,0x20,0x23,0x80000023,0x8000001c,0x27,0x2d}
  if cmd==12:
   off=struct.unpack_from('<I',b,pos+8)[0];assert 24<=off<size;libs.append(b[pos+off:pos+size].split(b'\0')[0].decode())
  if cmd==2:assert syms is None;syms=struct.unpack_from('<4I',b,pos+8)
  if cmd==0x19:
   nsec=struct.unpack_from('<I',b,pos+64)[0];assert 72+80*nsec==size
   for j in range(nsec):
    off=pos+72+80*j;sect,seg,addr,sz,foff,al,roff,nrel,fl,r1,r2,r3=struct.unpack_from('<16s16sQQ8I',b,off);sections.append((sect.rstrip(b'\0').decode(),seg.rstrip(b'\0').decode(),addr,sz,foff,fl))
  pos+=size
 assert pos==32+cmdbytes and libs==['/usr/lib/libSystem.B.dylib'] and syms is not None
 so,ns,st,ss=syms;assert so+ns*16<=len(b) and st+ss<=len(b);found=[]
 for j in range(ns):
  ix,t,sect,desc,value=struct.unpack_from('<IBBHQ',b,so+j*16);assert ix<ss;name=b[st+ix:st+ss].split(b'\0')[0].decode()
  if name=='_'+symbol:
   assert t&0xe0==0 and t&0x0e==0x0e and t&1 and 1<=sect<=len(sections)
   sec=sections[sect-1];assert sec[1]=='__TEXT' and sec[0]=='__text' and sec[2]<=value<sec[2]+sec[3];found.append(dict(name=name,n_type=t,n_sect=sect,value=value,section=sec[0],segment=sec[1]))
 assert len(found)==1;return found[0]
