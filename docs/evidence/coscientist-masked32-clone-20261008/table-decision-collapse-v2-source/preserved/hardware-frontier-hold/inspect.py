"""Finite source-data inspection only: no compiler, guest, solver or CPU probe."""
from pathlib import Path
import hashlib, json, re

R = Path('/Users/junkawasaki/github/wt/amu-seed17')
W = Path(__file__).resolve().parent
O = Path('/Users/junkawasaki/github/workspaces/codex/vector-typed-observer-native-v8')
def pin(p):
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
source = R / 'bench/embench/batch-ports/crc32.kotoba'
text = source.read_text()
line = next(x for x in text.splitlines() if x.startswith('(defn- table-at'))
tables = [list(map(int,x.split())) for x in re.findall(r'\[([\d\s]+)\]',line)]
table = sum(tables, [])
def reflected(v):
    for _ in range(8):
        v = (v >> 1) ^ (0xedb88320 if v & 1 else 0)
    return v
assert len(tables) == 16 and all(len(t) == 16 for t in tables)
assert table == [reflected(i) for i in range(256)]
def original(c,d): return table[(c ^ d) & 255] ^ (c >> 8)
def narrow(c,d): return reflected((c & 0xffffffff) ^ (d & 255))
def wide(c,d): return narrow(c,d) ^ ((c >> 32) << 24)
basis = [(0,0)] + [(1 << i,0) for i in range(32)] + [(0,1 << i) for i in range(8)]
assert all(original(c,d) == narrow(c,d) for c,d in basis)
wide_basis = [(0,0)] + [(1 << i,0) for i in range(64)] + [(0,1 << i) for i in range(8)]
assert all(original(c,d) == wide(c,d) for c,d in wide_basis)
records = json.loads((O/'ports/crc32/observer-records.json').read_text())
sir = [x['fields'] for x in records if x['tag'] == 'SIR']
frec = [x['fields'] for x in records if x['tag'] == 'FREC']
assert source.read_bytes() == (O/'sources/crc32.kotoba').read_bytes()
tabs = [x for x in sir if x[1] == 21]
assert len(tabs) == 16 and all(x[-1] == 16 for x in tabs)
out = {
  'status': 'SOURCE-MODEL HOLD: direct complete recurrence emitter not authored',
  'execution': {'compiler': 0, 'native': 0, 'ssh': 0, 'solver': 0, 'cpuProbe': 0},
  'pins': [pin(source), pin(R/'seed/41-a64gen.kotoba'), pin(R/'seed/30-lower.kotoba'), pin(R/'seed/SIR'),
           pin(O/'ports/crc32/observer-records.json'), pin(O/'sources/crc32.kotoba'), pin(W/'finite-laws.py'), pin(W/'finite-laws.json')],
  'model': {'immutableTableElements': 256, 'literalSlices': 16, 'u32BasisAndZero': len(basis),
            'u64CorrectedBasisAndZero': len(wide_basis),
            'u64DirectCounterexample': {'c': 1<<40, 'd': 0, 'original': original(1<<40,0), 'narrow': narrow(1<<40,0)}},
  'savedTypedSourceSnapshot': {'sourceBytesMatchCurrent': True, 'producerMatchesCurrent41Proved': False,
      'sirTabs': tabs, 'frec': frec,
      'recurrenceRows': [x for x in sir if 213 <= x[0] <= 225],
      'fuelRows': [x for x in sir if x[1] == 18]},
  'currentSourceApplicability': {'completeSemanticRecurrence': True,
      'completeClosedLocalScalarDAG': False, 'crossCallCFGProofImplemented': False,
      'explicitCRC32FeatureAuthorityImplemented': False,
      'directRuleNativeCandidateAdmitted': False},
  'historicalModelRole': 'Copied frozen model and saved result; neither historical Python model nor hardware probe executed.'
}
(W/'inspection.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'status':out['status'],'model':out['model'],'tabs':len(tabs),'inspectionSha256':pin(W/'inspection.json')['sha256']},indent=2))
