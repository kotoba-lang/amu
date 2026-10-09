"""Offline real header kernel controls; no compiler, guest, SSH or children."""
from pathlib import Path
import json,hashlib,re,struct
from header import header
D=Path(__file__).resolve().parent
pr=json.loads((D/'preregistration.json').read_text())
origins=json.loads((D/'input-origins.json').read_text())
assert pr['totalChildren']==52 and len(pr['entries'])==19
assert len(origins)<=4096 and sum(r['bytes'] for r in origins.values())<=469762048
cases={}
for n in ['vector-leaf-straight-read-cache-functional30-plan-v2-controls','vector-leaf-straight-read-cache-functional255-plan-v1-width']:
 cases.update({r['workload']:r for r in json.loads((D.parent/n/'preregistration.json').read_text())['cases']})
rows=[]
for row in pr['entries']:
 off=Path(row['OFF']['path']).read_bytes();lc=Path(row['LC']['path']).read_bytes()
 # Existing arm is only an offline complete-image fixture; never emitted as fresh header.
 c=Path(cases[row['workload']]['C']['path']).read_bytes()
 h=header(row,off,lc,c).decode()
 def arr(name):
  m=re.search(r'static const unsigned char '+name+r'\[\] = \{([^}]*)\};',h)
  assert m;return bytes(int(x) for x in m[1].split(','))
 assert arr('known_baseline')==off and arr('known_candidate')==lc and arr('timing_known_c_bytes')==c
 assert '#define TIMING_KNOWN_C_SYMBOL '+json.dumps(row['CSymbol']) in h
 negatives=0
 for ob,lb,cb in [(off+b'\0',lc,c),(off,lc+b'\0',c),(off,lc,b'\0'*len(c)),(off,lc,c[:12]+struct.pack('<I',2)+c[16:])]:
  try:header(row,ob,lb,cb)
  except AssertionError:negatives+=1
  else:raise AssertionError('mutation accepted')
 assert negatives==4
 rows.append(dict(workload=row['workload'],wholeOFFLCAndCHeaderAnchors=True,rejections=negatives,fixtureCIsHistoricalOnly=True))
out=dict(status='PASS_PURE_SOURCE_HEADER_BYTE_ANCHORS_AND_76_MUTATION_REJECTIONS',entries=rows,futureFreshCNotBuilt=True,processChildren=0,nativeCalls=0,SSHCalls=0,compilerCalls=0,timingCalls=0)
(D/'pure-controls-result.json').write_text(json.dumps(out,indent=2)+'\n')
