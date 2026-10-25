from pathlib import Path
import json,re,struct,hashlib,bisect

def sx(x,n):return x-(1<<n)if x&(1<<(n-1))else x

def ref(w,p):
 if w&0x7c000000==0x14000000:return('BL'if w&0x80000000 else'B',p+4*sx(w&0x3ffffff,26),0xfc000000)
 if w&0xff000010==0x54000000:return('BC',p+4*sx(w>>5&0x7ffff,19),0xff00001f)
 if w&0x7e000000==0x34000000:return('CB',p+4*sx(w>>5&0x7ffff,19),0xff00001f)
 if w&0x7e000000==0x36000000:return('TB',p+4*sx(w>>5&0x3fff,14),0xfff8001f)
 if w&0x3b000000==0x18000000:return('LIT',p+4*sx(w>>5&0x7ffff,19),0xff00001f)
 if w&0x9f000000==0x10000000:return('ADR',p+sx(((w>>5&0x7ffff)<<2)|(w>>29&3),21),0x9f00001f)
 assert w&0x9f000000!=0x90000000,('UNKNOWN_ADRP',p)
 return None

def payload(a):
 b=Path(a['native']['path']).read_bytes();h,v=Path(a['container']['path']).read_bytes().split(b'\n\n',1);ls=h.decode().splitlines();m,n,c=ls[0].split()
 assert m=='KSEED1'and int(n)==len(b)and int(c)==len(ls)-1 and v==b
 ex={}
 for row in ls[1:]:
  name,p,k=row.split();assert name not in ex;ex[name]=[int(p),int(k)];assert int(p)%4==0 and 0<=int(p)<len(b)
 if 'exports'in a:assert ex=={k:list(v)for k,v in a['exports'].items()}
 for kind,data in [('native',b),('container',Path(a['container']['path']).read_bytes())]:
  if 'sha256'in a[kind]:assert hashlib.sha256(data).hexdigest()==a[kind]['sha256']
 return b,ex

def source_pool(source):
 import importlib.util
 p=Path(__file__).with_name('source-pool.py')
 spec=importlib.util.spec_from_file_location('current_source_owned_pool',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return m.source_pool(source)

