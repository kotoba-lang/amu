import json,hashlib
WORKLOADS=['aha-mont64','crc32','depthconv','edn','huffbench','matmult-int','md5sum','nettle-aes','nettle-sha256','nsichneu','picojpeg','qrduino','sglib-combined','slre','statemate','tarfind','ud','wikisort','xgboost']
QLABELS=[p+'-'+n for p in ['before','after'] for n in ['resolved-clang','sdk-path','sdk-version','clang-version','clang-target','OS-version','OS-build']]
TOP={'terminal.json','failure.json','identity-before.json','identity-after.json','effective-environment.json','images.json','report.json'}
ALLOWED={'remote-build-go.json'}|{'runner-build/'+n for n in TOP}|{'runner-build/'+a+'/attempts.json' for a in ['compiles','queries']}|{'runner-build/queries/'+n+ext for n in QLABELS for ext in ['.stdout','.stderr']}|{'runner-build/compiles/'+n+ext for n in WORKLOADS for ext in ['.stdout','.stderr']}|{'runner-build/'+n+'/runner' for n in WORKLOADS}
def validate_result(content):
 assert set(content)<=ALLOWED and 'runner-build/terminal.json' in content
 t=json.loads(content['runner-build/terminal.json']);assert set(t)=={'allBuildsClosed','allQueriesClosed','builds','identityQueries','failure'}
 assert t['allBuildsClosed'] is True and t['allQueriesClosed'] is True and type(t['failure']) is bool
 for k,cap in [('builds',19),('identityQueries',14)]:assert type(t[k]) is int and 0<=t[k]<=cap
 for folder,k,labels in [('compiles','builds',WORKLOADS),('queries','identityQueries',QLABELS)]:
  ap='runner-build/'+folder+'/attempts.json'
  if ap in content:rows=json.loads(content[ap])
  else:assert t[k]==0;rows=[]
  assert type(rows) is list and len(rows)==t[k]
  for i,r in enumerate(rows):
   assert r['index']==i+1 and type(r['index']) is int and r['label']==labels[i] and r['state']=='terminal' and type(r['returncode']) is int and type(r['timeout']) is bool
   for ext,key in [('.stdout','stdoutSHA256'),('.stderr','stderrSHA256')]:
    p='runner-build/'+folder+'/'+r['label']+ext;assert p in content and hashlib.sha256(content[p]).hexdigest()==r[key]
  # No stdout/stderr without matching attempted label.
  allowed=({ap} if ap in content else set())|{'runner-build/'+folder+'/'+r['label']+e for r in rows for e in ['.stdout','.stderr']}
  assert {n for n in content if n.startswith('runner-build/'+folder+'/')}==allowed
 assert {n for n in content if n.endswith('/runner')}<= {'runner-build/'+n+'/runner' for n in WORKLOADS[:t['builds']]}
 assert ('runner-build/failure.json' in content)==t['failure']
 if t['failure']:
  f=json.loads(content['runner-build/failure.json']);assert f['builds']==t['builds'] and f['identityQueries']==t['identityQueries'] and f['policy']=='STOP_FIRST_FAILURE_NO_RERUN'
 if not t['failure']:
  assert t['builds']==19 and t['identityQueries']==14 and {'runner-build/report.json','runner-build/images.json','runner-build/identity-before.json','runner-build/identity-after.json','runner-build/effective-environment.json'}<=set(content)
  assert all('runner-build/'+n+'/runner' in content for n in WORKLOADS)
 return t

def parse_ustar(raw):
 assert len(raw)<=134217728+256*1024+10240
 out={};at=0
 def take(n):
  nonlocal at
  assert type(n) is int and 0<=n<=16777216 and at+n<=len(raw);b=raw[at:at+n];at+=n;return b
 def octal(b):
  s=b.rstrip(b'\0 ').lstrip(b' ');assert s and all(48<=x<=55 for x in s);return int(s,8)
 while True:
  z=take(512)
  if z==bytes(512):assert take(512)==bytes(512) and not any(raw[at:]);break
  assert z[257:263]==b'ustar\0' and z[263:265]==b'00' and z[156:157]==b'0' and not any(z[157:257])
  assert octal(z[148:156])==sum(z[:148])+8*32+sum(z[156:])
  leaf=z[:100].split(b'\0',1)[0].decode('ascii');prefix=z[345:500].split(b'\0',1)[0].decode('ascii');n=(prefix+'/' if prefix else '')+leaf
  assert n in ALLOWED|{'inventory.json'} and n not in out and len(out)<257
  size=octal(z[124:136]);assert size<=16777216;out[n]=take(size);assert not any(take((-size)%512))
 return out
