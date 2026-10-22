import json,hashlib
LABELS=['aha-mont64-baseline-n0', 'aha-mont64-candidate-n0', 'aha-mont64-C-n0', 'aha-mont64-baseline-n1', 'aha-mont64-candidate-n1', 'aha-mont64-C-n1', 'aha-mont64-baseline-n32', 'aha-mont64-candidate-n32', 'aha-mont64-C-n32', 'crc32-baseline-n0', 'crc32-candidate-n0', 'crc32-C-n0', 'crc32-baseline-n1', 'crc32-candidate-n1', 'crc32-C-n1', 'crc32-baseline-n32', 'crc32-candidate-n32', 'crc32-C-n32', 'depthconv-baseline-n0', 'depthconv-candidate-n0', 'depthconv-C-n0', 'depthconv-baseline-n1', 'depthconv-candidate-n1', 'depthconv-C-n1', 'depthconv-baseline-n2000', 'depthconv-candidate-n2000', 'depthconv-C-n2000', 'edn-baseline-n0', 'edn-candidate-n0', 'edn-C-n0', 'edn-baseline-n1', 'edn-candidate-n1', 'edn-C-n1', 'edn-baseline-n32', 'edn-candidate-n32', 'edn-C-n32', 'huffbench-baseline-n0', 'huffbench-candidate-n0', 'huffbench-C-n0', 'huffbench-baseline-n1', 'huffbench-candidate-n1', 'huffbench-C-n1', 'huffbench-baseline-n32', 'huffbench-candidate-n32', 'huffbench-C-n32', 'matmult-int-baseline-n0', 'matmult-int-candidate-n0', 'matmult-int-C-n0', 'matmult-int-baseline-n1', 'matmult-int-candidate-n1', 'matmult-int-C-n1', 'matmult-int-baseline-n32', 'matmult-int-candidate-n32', 'matmult-int-C-n32', 'md5sum-baseline-n0', 'md5sum-candidate-n0', 'md5sum-C-n0', 'md5sum-baseline-n1', 'md5sum-candidate-n1', 'md5sum-C-n1', 'md5sum-baseline-n32', 'md5sum-candidate-n32', 'md5sum-C-n32', 'nettle-aes-baseline-n0', 'nettle-aes-candidate-n0', 'nettle-aes-C-n0', 'nettle-aes-baseline-n1', 'nettle-aes-candidate-n1', 'nettle-aes-C-n1', 'nettle-aes-baseline-n32', 'nettle-aes-candidate-n32', 'nettle-aes-C-n32', 'nettle-sha256-baseline-n0', 'nettle-sha256-candidate-n0', 'nettle-sha256-C-n0', 'nettle-sha256-baseline-n1', 'nettle-sha256-candidate-n1', 'nettle-sha256-C-n1', 'nettle-sha256-baseline-n32', 'nettle-sha256-candidate-n32', 'nettle-sha256-C-n32', 'nsichneu-baseline-n0', 'nsichneu-candidate-n0', 'nsichneu-C-n0', 'nsichneu-baseline-n1', 'nsichneu-candidate-n1', 'nsichneu-C-n1', 'nsichneu-baseline-n32', 'nsichneu-candidate-n32', 'nsichneu-C-n32', 'picojpeg-baseline-n0', 'picojpeg-candidate-n0', 'picojpeg-C-n0', 'picojpeg-baseline-n1', 'picojpeg-candidate-n1', 'picojpeg-C-n1', 'picojpeg-baseline-n32', 'picojpeg-candidate-n32', 'picojpeg-C-n32', 'qrduino-baseline-n0', 'qrduino-candidate-n0', 'qrduino-C-n0', 'qrduino-baseline-n1', 'qrduino-candidate-n1', 'qrduino-C-n1', 'qrduino-baseline-n32', 'qrduino-candidate-n32', 'qrduino-C-n32', 'sglib-combined-baseline-n0', 'sglib-combined-candidate-n0', 'sglib-combined-C-n0', 'sglib-combined-baseline-n1', 'sglib-combined-candidate-n1', 'sglib-combined-C-n1', 'sglib-combined-baseline-n32', 'sglib-combined-candidate-n32', 'sglib-combined-C-n32', 'slre-baseline-n0', 'slre-candidate-n0', 'slre-C-n0', 'slre-baseline-n1', 'slre-candidate-n1', 'slre-C-n1', 'slre-baseline-n32', 'slre-candidate-n32', 'slre-C-n32', 'statemate-baseline-n0', 'statemate-candidate-n0', 'statemate-C-n0', 'statemate-baseline-n1', 'statemate-candidate-n1', 'statemate-C-n1', 'statemate-baseline-n32', 'statemate-candidate-n32', 'statemate-C-n32', 'tarfind-baseline-n0', 'tarfind-candidate-n0', 'tarfind-C-n0', 'tarfind-baseline-n1', 'tarfind-candidate-n1', 'tarfind-C-n1', 'tarfind-baseline-n32', 'tarfind-candidate-n32', 'tarfind-C-n32', 'ud-baseline-n0', 'ud-candidate-n0', 'ud-C-n0', 'ud-baseline-n1', 'ud-candidate-n1', 'ud-C-n1', 'ud-baseline-n32', 'ud-candidate-n32', 'ud-C-n32', 'wikisort-baseline-n0', 'wikisort-candidate-n0', 'wikisort-C-n0', 'wikisort-baseline-n1', 'wikisort-candidate-n1', 'wikisort-C-n1', 'wikisort-baseline-n32', 'wikisort-candidate-n32', 'wikisort-C-n32', 'xgboost-baseline-n0', 'xgboost-candidate-n0', 'xgboost-C-n0', 'xgboost-baseline-n1', 'xgboost-candidate-n1', 'xgboost-C-n1', 'xgboost-baseline-n32', 'xgboost-candidate-n32', 'xgboost-C-n32']
ALLOWED={'remote-functional-go.json'}|{'functional171/'+n for n in ['attempts.json','effective-environment.json','comparisons.json','report.json','failure.json','terminal.json']}|{'functional171/'+n+e for n in LABELS for e in ['.stdout','.stderr']}
def validate_result(content):
 assert set(content)<=ALLOWED
 t=json.loads(content['functional171/terminal.json']);assert set(t)=={'allCallsClosed','calls','failure'} and t['allCallsClosed'] is True and type(t['failure']) is bool and type(t['calls']) is int and 0<=t['calls']<=171
 ap='functional171/attempts.json'
 rows=json.loads(content[ap]) if ap in content else []
 assert type(rows) is list and len(rows)==t['calls']
 raw=set()
 for i,r in enumerate(rows):
  assert type(r['index']) is int and r['index']==i+1 and r['label']==LABELS[i] and r['state']=='terminal' and type(r['returncode']) is int and type(r['timeout']) is bool
  for ext,key in [('.stdout','stdoutSHA256'),('.stderr','stderrSHA256')]:
   n='functional171/'+r['label']+ext;raw.add(n);assert n in content and hashlib.sha256(content[n]).hexdigest()==r[key]
 assert {n for n in content if n.endswith('.stdout') or n.endswith('.stderr')}==raw
 assert ('functional171/failure.json' in content)==t['failure']
 if t['failure']:
  f=json.loads(content['functional171/failure.json']);assert f['calls']==t['calls'] and f['policy']=='STOP_FIRST_FAILURE_NO_RETRY' and type(f['completedTriples']) is int and 0<=f['completedTriples']<=t['calls']//3
 else:
  assert t['calls']==171 and 'functional171/report.json' in content and 'functional171/comparisons.json' in content
  r=json.loads(content['functional171/report.json']);assert r['status']=='PASS_FINITE_FULL_ORIGINAL19_171_FUNCTIONAL_ONLY' and r['calls']==171 and r['workloads']==19
 return t

def parse_ustar(raw):
 assert len(raw)<=134217728+350*1024+10240
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
  assert n in ALLOWED|{'inventory.json'} and n not in out and len(out)<351
  size=octal(z[124:136]);assert size<=16777216;out[n]=take(size);assert not any(take((-size)%512))
 return out
