# Source-operation model only: no code generation, machine execution or kernel calls.
import re,struct,sys,hashlib
from pathlib import Path
src=Path(sys.argv[1]).read_text();assert hashlib.sha256(src.encode()).hexdigest()=='43e5eebcbc7c3d0ee86d2175b8ab4c01c94de7f5e693da4a8bcd4f641a75b9d3','source pin mismatch';body=src[src.index('(defn- watcher-words'):src.index('(defn- body-at')]
def parse(text):
 text=re.sub(r';;[^\n]*','',text)
 ops=[(n,[int(x,0) for x in a.split()]) for n,a in re.findall(r'\((ds-[a-z]+)\s+([^()]*)\)',text)]
 labels={a[0]:i for i,(n,a) in enumerate(ops) if n=='ds-label'}
 assert len(labels)==1 and 9 in labels
 return ops,labels
req=struct.pack('<4sIQQII',b'WP01',1234,1700000000,42,5678,10)
expected=b'WO01'+b'\0'*4+req
class Term(Exception):
 def __init__(self,rc):self.rc=rc

def run(text,fail='',request=req):
 ops,labels=parse(text);mem=bytearray(2048);x=[0]*32;sp=2048;pc=0;carry=False;z=False;c=False;output=b'';nproc=0
 def reg(n,base=False):return sp if n==31 and base else 0 if n==31 else x[n]
 def store(offset,size,value):
  assert 0<=offset<=len(mem)-size,(offset,size)
  mem[offset:offset+size]=int(value).to_bytes(size,'little',signed=False)
 def call(num):
  nonlocal carry,output,nproc
  carry=False
  if num==3:
   assert x[0]==3 and x[1]==0 and x[2]==32
   if fail=='read-error':carry=True;x[0]=5;return
   val=request[:31] if fail=='read-short' else request[:32];mem[0:len(val)]=val;x[0]=len(val);return
  if num==336:
   nproc+=1;which='before' if nproc==1 else 'after';assert nproc<=2 and x[:4]==[2,1234,3,0] and x[4] in (256,768) and x[5]==136
   if fail==which+'-error':carry=True;x[0]=3;return
   if fail==which+'-short':x[0]=135;return
   start=x[4];b=bytearray(136);struct.pack_into('<I',b,12,1235 if fail==which+'-pid' else 1234);struct.pack_into('<Q',b,120,1700000001 if fail==which+'-sec' else 1700000000);struct.pack_into('<Q',b,128,43 if fail==which+'-usec' else 42);mem[start:start+136]=b;x[0]=136;return
  if num==362:
   if fail=='kqueue-error':carry=True;x[0]=5;return
   x[0]=7;return
  if num==369:
   assert x[0]==7
   if x[2]==1:
    assert x[1]==512 and x[3:7]==[0,0,0,0]
    assert bytes(mem[512:560])==struct.pack('<QhHIqQQQ',1234,-5,0x11,0x80000000,0,5678,0,0)
    if fail=='registration-error':carry=True;x[0]=3;return
    if fail=='registration-count':x[0]=1;return
    x[0]=0;return
   assert x[1:7]==[0,0,1024,1,0,1104] and struct.unpack_from('<QQ',mem,1104)==(10,0)
   if fail=='wait-error':carry=True;x[0]=4;return
   if fail=='wait-timeout':x[0]=0;return
   if fail=='wait-count':x[0]=2;return
   pid=1235 if fail=='event-pid' else 1234;flt=-4 if fail=='event-filter' else -5
   flags=0xc031 if fail=='event-error' else 0x0031 if fail=='event-no-eof' else 0x8031
   note=0 if fail=='event-no-exit' else 0x80000000;tok=5679 if fail=='event-token' else 5678
   mem[1024:1072]=struct.pack('<QhHIqQQQ',pid,flt,flags,note,0,tok,0,0);x[0]=1;return
  if num==4:
   assert x[0]==1 and x[1]==1200 and x[2]==40
   if fail=='write-error':carry=True;x[0]=5;return
   count=10 if fail=='write-short' else 40;output=bytes(mem[1200:1200+count]);x[0]=count;return
  if num==1:raise Term(x[0])
  raise AssertionError(('unexpected syscall',num))
 try:
  for _ in range(1000):
   n,a=ops[pc];pc+=1
   if n=='ds-label':continue
   if n=='ds-imm':x[a[0]]=a[1]
   elif n=='ds-sub':assert a[0]==31 and a[1]==31;sp-=a[2]
   elif n=='ds-add':x[a[0]]=reg(a[1],True)+a[2]
   elif n in ('ds-lw','ds-lh','ds-ldr'):
    size={'ds-lw':4,'ds-lh':2,'ds-ldr':8}[n];off=reg(a[1],True)+a[2];assert 0<=off<=len(mem)-size;x[a[0]]=int.from_bytes(mem[off:off+size],'little')
   elif n in ('ds-sw','ds-str'):
    size={'ds-sw':4,'ds-str':8}[n];store(reg(a[1],True)+a[2],size,reg(a[0])&((1<<(size*8))-1))
   elif n=='ds-and':x[a[0]]=reg(a[1])&reg(a[2])
   elif n in ('ds-cmp','ds-cmpi'):
    left=reg(a[0]);right=reg(a[1]) if n=='ds-cmp' else a[1];z=left==right;c=left>=right
   elif n=='ds-i':
    word=a[0]
    if word==0xaa1303e1:x[1]=x[19]
    elif word==0xaa0003f7:x[23]=x[0]
    elif word==0xaa1703e0:x[0]=x[23]
    else:raise AssertionError(('unhandled raw word',hex(word)))
   elif n=='ds-b':
    cond=a[0]&15
    branch={0:z,1:not z,2:carry,8:c and not z}.get(cond)
    assert branch is not None,('condition',cond)
    if branch:pc=labels[a[1]]
   elif n=='ds-sys':call(a[0])
   else:raise AssertionError(('unknown operation',n))
  raise AssertionError('nonterminating source model')
 except Term as t:return t.rc,output

assert run(body)==(0,expected)
failures=['read-error','read-short','before-error','before-short','before-pid','before-sec','before-usec','kqueue-error','registration-error','registration-count','after-error','after-short','after-pid','after-sec','after-usec','wait-error','wait-timeout','wait-count','event-pid','event-filter','event-error','event-no-eof','event-no-exit','event-token','write-error','write-short']
for name in failures:
 rc,out=run(body,name);assert rc==1 and out!=expected,(name,rc,out)
invalid=[struct.pack('<4sIQQII',m,p,s,u,t,w) for m,p,s,u,t,w in [(b'bad!',1234,1700000000,42,5678,10),(b'WP01',0,1700000000,42,5678,10),(b'WP01',2147483648,1700000000,42,5678,10),(b'WP01',1234,0,42,5678,10),(b'WP01',1234,1700000000,1000000,5678,10),(b'WP01',1234,1700000000,42,0,10),(b'WP01',1234,1700000000,42,2147483648,10),(b'WP01',1234,1700000000,42,5678,0),(b'WP01',1234,1700000000,42,5678,901)]]
for i,raw in enumerate(invalid):assert run(body,request=raw)==(1,b''),i
old='(ds-ldr 8 31 1048) (ds-cmp 8 22) (ds-b 0x54000001 9)';assert body.count(old)==1
mut=body.replace(old,'(ds-ldr 8 31 1048) (ds-cmp 8 22)')
assert run(mut,'event-token')==(0,expected)
print('source_sha256',hashlib.sha256(src.encode()).hexdigest(),'positive',1,'failure_cases',len(failures),'invalid_requests',len(invalid),'token_branch_mutant','accepted_as_expected')
print('source-operation simulation with stub syscalls; raw instructions, native binary, kernel behavior and races NOT tested')
