import re
def need(c,s):
 if not c:raise AssertionError(s)
def container(b):
 need(len(b)<=4194560 and b.count(b'\n\n')>=1,'bounded container');head,payload=b.split(b'\n\n',1);ls=head.decode('ascii').split('\n');m=re.fullmatch(r'KSEED1 ([0-9]+) ([0-9]+)',ls[0]);need(m is not None,'KSEED1 header');n,k=map(int,m.groups());need(0<n<=4194304 and len(payload)==n and len(ls)==k+1 and 1<=k<=128,'header lengths');exports=[]
 for line in ls[1:]:
  m=re.fullmatch(r'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',line);need(m is not None,'export syntax');s,off,a=m.groups();off=int(off);a=int(a);need(off%4==0 and off+4<=n and 0<=a<=32,'export range');exports.append({'name':s,'offset':off,'arity':a})
 need(len({r['name']for r in exports})==k,'unique exports');return exports,payload

FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
PAT=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in FIELDS)+'}\n').encode())
def counters(err):
 matches=[PAT.fullmatch(line)for line in err.splitlines(keepends=True)];matches=[m for m in matches if m is not None]
 if len(matches)!=1:return {'status':'unavailable-or-not-exactly-one-counter-line','matchingLines':len(matches),'values':None,'entireStderrIsCounterLine':False}
 u=dict(zip(FIELDS,map(int,matches[0].groups())));valid=all(type(v)is int and 0<=v<2**64 for v in u.values()) and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items'] and u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
 return {'status':'valid'if valid else 'invalid','matchingLines':1,'values':u,'entireStderrIsCounterLine':PAT.fullmatch(err)is not None}

