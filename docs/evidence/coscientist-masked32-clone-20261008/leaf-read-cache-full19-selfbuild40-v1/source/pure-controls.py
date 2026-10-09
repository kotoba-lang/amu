"""Pinned buffer data tests only. No main/child/guest/compiler invocation."""
from pathlib import Path
import json,hashlib,ast
D=Path(__file__).resolve().parent
s=(D/'run.py').read_bytes();ast.parse(s);ns={'__file__':str(D/'run.py'),'__name__':'pure_buffer_controls'};exec(compile(s,str(D/'run.py'),'exec'),ns)
payload=b'\x1f\x20\x03\xd5'*2;valid=b'KSEED1 8 1\nmain 0 0\n\n'+payload;assert ns['parse_container'](valid)==(payload,[('main',0,0)])
mutants=[valid[:-1],valid.replace(b'8 1',b'7 1'),valid.replace(b'main 0 0',b'main 8 0'),valid.replace(b'main 0 0',b'main 1 0'),valid.replace(b'8 1',b'8 2'),valid.replace(b'main 0 0',b'main 0 33'),b'KSEED1 8 2\nmain 0 0\nmain 4 0\n\n'+payload]
for m in mutants:
 try:ns['parse_container'](m)
 except AssertionError:pass
 else:raise AssertionError('accepted bad container')
pr=json.loads((D/'preregistration.json').read_bytes());old=Path(pr['callLedgerOrigin']['path']).read_bytes();assert len(old)==pr['callLedgerOrigin']['bytes']and hashlib.sha256(old).hexdigest()==pr['callLedgerOrigin']['sha256'];a=old.decode();b=s.decode();origin=a[a.index(' def call('):a.index('\n try:\n  decoderPath')];actual=b[b.index(' def call('):b.index('\n try:\n  def build')];assert actual==origin.replace('len(rows)<10','len(rows)<40').replace('finite18 no retry','finite40 no retry')
assert len(pr['entries'])==19 and sum('retained'not in e for e in pr['entries'])==17 and 17*2+3*2==40
for e in pr['entries']:
 if 'retained'in e:
  p,x=ns['parse_container'](Path(e['retained']['container']['path']).read_bytes());assert p==Path(e['retained']['native']['path']).read_bytes()and any(q[0]==e['symbol']and q[2]==1 for q in x)
print('PASS pure metadata/container/ledger controls only; no native calls')
