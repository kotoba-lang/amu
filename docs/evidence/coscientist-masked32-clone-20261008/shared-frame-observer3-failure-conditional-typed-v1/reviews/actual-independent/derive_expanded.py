"""Independent finite exact-ASCII source-library scanner; no compiler execution."""
from pathlib import Path
import re,json,hashlib
D=Path('/Users/junkawasaki/github/workspaces/codex/shared-frame-currenttyped-observer3-source-v1-20261009')
def derive():
 primary=(D/'ordinary-current16.kotoba').read_text();src=(D/'nsichneu.kotoba').read_bytes();assert src.isascii()
 def block(name):
  st=primary.index('(defn- '+name+' ');end=primary.find('\n(defn',st+1);return primary[st:end]
 const={k:int(v)for k,v in re.findall(r'\(def (ck-r6[bmf]-g-\S+) ([0-9]+)\)',primary)}
 hm={int(x):const[g]for x,g in re.findall(r'\(= h (-?\d+)\) (ck-r6b-g-\S+)',block('ck-r6b-name-bit'))}
 textmap={x:const[g]for x,g in re.findall(r'\(ck-r6b-is\? S a b "([^"]+)"\) (ck-r6f-g-\S+)',block('ck-r6f-name-bit'))}
 for names,g in re.findall(r'(?m)^      (\([^\n]*?\)|-?\d+) (ck-r6m-g-\S+)',block('ck-r6m-name-bit')):
  for x in re.findall(r'-?\d+',names):hm[int(x)]=const[g]
 def fnv(t):
  v=14695981039346656037
  for b in t:v=((v^b)*1099511628211)&(2**64-1)
  return v-(2**64)if v>=2**63 else v
 def bit(t):
  if len(t)>9 and t.startswith(b'document-'):return const['ck-r6b-g-doc']
  if t in [b'f32-to-bits',b'f32-from-bits']:return const['ck-r6f-g-f32']
  assert t!=b'typed-set-nth','extended keyword typed-set rule absent in this exact input'
  return textmap.get(t.decode(),hm.get(fnv(t),0))
 sym=lambda c:65<=c<=90 or 97<=c<=122 or 48<=c<=57 or c in b'*+!_?<>=/.-&'
 def end(i):
  while i<len(src)and sym(src[i]):i+=1
  return i
 i=0;used=defd=0;pd=False;heads=[];defs=[];calls=[]
 while i<len(src):
  c=src[i]
  if c==59:
   n=src.find(b'\n',i);i=len(src)if n<0 else n;pd=False
  elif c==34:
   i+=1
   while i<len(src):
    if src[i]==92:i+=2
    elif src[i]==34:i+=1;break
    else:i+=1
   pd=False
  elif c==92:i=min(len(src),i+2);pd=False
  elif c==40:
   b=end(i+1)
   if b==i+1:i=b;pd=False;continue
   t=src[i+1:b];g=bit(t);used|=g;heads.append(t.decode());
   if g:calls.append({'byteStart':i+1,'head':t.decode(),'group':g,'signedHash':fnv(t)})
   pd=t in [b'defn',b'defn-',b'def'];i=b
  elif c==58:
   b=end(i+1)
   if src[i:b]==b':document':used|=const['ck-r6b-g-doc']
   i=b;pd=False
  elif sym(c):
   b=end(i);t=src[i:b]
   if pd:defd|=bit(t);defs.append(t.decode())
   i=b;pd=False
  else:
   i+=1;pd=pd if c in [32,10,9,13,44]else False
 r=used&~(defd&~(const['ck-r6b-g-kw']|const['ck-r6b-g-doc']))
 if r&(const['ck-r6b-g-exi']|const['ck-r6f-g-symp']):r|=const['ck-r6b-g-doc']
 if r&(const['ck-r6b-g-doc']|const['ck-r6f-g-kwo']):r|=const['ck-r6b-g-kw']
 assert r==used==64 and defd==0 and all(x['head']=='rem'and x['signedHash']==-8509051109125074585 for x in calls)
 # Decode exact source string literal, including source escaped newline, not guessed text.
 m=re.search(r'\(defn- ck-r6b-t-rem0 \[\] :string\s+("(?:[^"\\]|\\.)*")\)',primary);assert m
 lib=json.loads(m[1]).encode();expanded=src+b'\n'+lib;assert len(src)==30386 and len(expanded)==30443
 return expanded,{'originalBytes':len(src),'expandedBytes':len(expanded),'expandedSHA256':hashlib.sha256(expanded).hexdigest(),'usedGroup':used,'definedGroups':defd,'finalGroup':r,'remCalls':calls,'originalDefinedNames':len(defs),'implicitDefinitions':1,'FNRowsIncludingNull':len(defs)+2,'appendedExactLiteral':lib.decode(),'primaryRoute':'drv-pj-command appends ck-r6b-lib(S0); emptyT scan64 -> leading LF plus ck-r6b-t-rem0 only','scannerScope':'Exact ASCII input, original scan string/comment/char/head/pendingdef rules and primary r6b/F/M mappings; no compiler/typechecker run'}
if __name__=='__main__':print(json.dumps(derive()[1],indent=2))
