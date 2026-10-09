"""Pure source-buffer/metadata controls only; no main or process invocation."""
from pathlib import Path
import hashlib,json,ast
D=Path(__file__).resolve().parent;s=(D/'run.py').read_bytes();ast.parse(s);ns={'__file__':str(D/'run.py'),'__name__':'pure_g3_source_controls'};exec(compile(s,str(D/'run.py'),'exec'),ns)
pr=json.loads((D/'preregistration.json').read_bytes());assert pr['maximumLoaderCalls']==38 and len(pr['entries'])==19 and all('retained'not in e for e in pr['entries'])and pr['selfbuildCalls']==0
for e in pr['entries']:
 z=e['baseline'];payload,exports=ns['parse_container'](Path(z['container']['path']).read_bytes());assert payload==Path(z['native']['path']).read_bytes()and [list(q)for q in exports]==z['exports']and next(q[1]for q in exports if q[0]==e['symbol'])==z['offset'];assert hashlib.sha256(Path(e['source']['path']).read_bytes()).hexdigest()==e['source']['sha256']
old=Path(pr['callLedgerOrigin']['path']).read_bytes();assert len(old)==pr['callLedgerOrigin']['bytes']and hashlib.sha256(old).hexdigest()==pr['callLedgerOrigin']['sha256'];a=old.decode();b=s.decode();origin=a[a.index(' def call('):a.index('\n try:\n  def build')];actual=b[b.index(' def call('):b.index('\n try:\n  for e')];assert actual==origin.replace('len(rows)<40','len(rows)<38').replace('finite40 no retry','finite38 no retry')
valid=b'KSEED1 8 1\nbench 0 1\n\n'+bytes(8);assert ns['parse_container'](valid)==(bytes(8),[('bench',0,1)])
for m in [valid[:-1],valid.replace(b'8 1',b'7 1'),valid.replace(b'bench 0 1',b'bench 8 1'),valid.replace(b'bench 0 1',b'bench 1 1'),valid.replace(b'8 1',b'8 2')]:
 try:ns['parse_container'](m)
 except AssertionError:pass
 else:raise AssertionError('bad container accepted')
assert b"STOP_G3_G0_WHOLE_CONTAINER_MISMATCH_BEFORE_EXTRACT"in s and s.index(b"STOP_G3_G0_WHOLE_CONTAINER_MISMATCH_BEFORE_EXTRACT")<s.index(b"raw2=call(label+'-extract'")
print('PASS pure19 baseline/whole source+container, Ledger reversal, 5 parser rejects; native0')
