#!/usr/bin/env python3
# BOOTSTRAP-TOOL: revalidate recorded native values against padded unchanged C.
import argparse,ctypes,json,pathlib,hashlib
parser=argparse.ArgumentParser();parser.add_argument('recorded',type=pathlib.Path);parser.add_argument('padded',type=pathlib.Path);args=parser.parse_args();p=args.recorded.resolve();q=args.padded.resolve()
r=json.loads((p/'results.json').read_text());assert r['status']=='complete-correctness' and not r['rows']
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
for f in ('slre.kotoba','fixture-audit.kotoba','observe-fixture.bin','batch.bin'):assert sha(p/f)==r['sha256'][f]
assert (p/'fixtures.json').read_bytes()==(q/'fixtures.json').read_bytes()
assert (p/'fixture-audit.kotoba').read_bytes()==(q/'fixture-audit.kotoba').read_bytes()
if (p/'padded-oracle-audit.json').exists():raise SystemExit('refusing to replace evidence')
c=ctypes.CDLL(str(q/'c.dylib'))
for name in ('observe_fixture','fixture_selfcheck','observe','original_result'):
 f=getattr(c,name);f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*8
for item in r['fixtures']:assert c.fixture_selfcheck(item['case'],0,0,0,0,0,0,0)==1
for row in r['cells']:
 v=c.observe_fixture(row['case']*1024+row['cell'],0,0,0,0,0,0,0);assert v==row['Kotoba']==row['C'],row
for row in r['productionCells']:assert c.observe(row['cell'],0,0,0,0,0,0,0)==row['Kotoba']==row['C']
for row in r['batches']:
 if row['iterations']>0:assert c.original_result(row['iterations'],0,0,0,0,0,0,0)==102
proof={'status':'complete-correctness','performanceMeasured':False,'stateResultCells':len(r['cells']),'productionCells':len(r['productionCells']),'unchangedCSelfchecks':len(r['fixtures']),'recordedReportSha256':sha(p/'results.json'),'nativeSha256':r['sha256']['batch.bin'],'paddedBridgeSha256':sha(q/'c-bridge.c'),'paddedCSha256':sha(q/'c.dylib'),'allRecordedValuesMatchPaddedC':True}
(p/'padded-oracle-audit.json').write_text(json.dumps(proof,indent=2)+'\n');print('PASS',len(r['cells']),'native values match padded C')
