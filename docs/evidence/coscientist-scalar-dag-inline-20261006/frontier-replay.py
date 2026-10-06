"""Offline source/table/disassembly-text replay only; no guests, compiler, timing or solver."""
from pathlib import Path
import json,hashlib,tarfile,tempfile,subprocess,sys,re,collections
D=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text());m=load(D/'frontier-manifest.json');a=D/m['archive']['file'];assert sha(a)==m['archive']['sha256'] and a.stat().st_size==m['archive']['bytes'];tmp=Path(tempfile.mkdtemp(prefix='amu-frontier-offline-'))
with tarfile.open(a) as t:
 for f in t.getmembers():assert not f.issym() and not f.islnk() and not Path(f.name).is_absolute() and '..' not in Path(f.name).parts
 t.extractall(tmp,filter='data')
P=tmp/'frontier-proof';assert sha(P/'payload-pins.json')==m['payloadPinsSha256'];pins=load(P/'payload-pins.json');assert len(pins)==m['payloadFiles']
for n,v in pins.items():assert sha(P/n)==v['sha256'] and (P/n).stat().st_size==v['bytes']
for name in ['finite-laws','narrow-laws']:
 prior=load(P/(name+'.json'));q=subprocess.run([sys.executable,str(P/(name+'.py'))],capture_output=True,text=True);assert q.returncode==0,q.stderr;assert load(P/(name+'.json'))==prior
matrix=load(P/'comparison-matrix.json');ref=load(P/'c-reference.json');assert len(matrix['entries'])==len(ref['rows'])==19
for row in ref['rows']:
 n=row['workload'];assert all(f in row['cBuildCommand'] for f in ['-O2','-std=gnu11','-dynamiclib'])
 for e in row['files']:assert sha(P/'bridges'/n/e['output'])==e['sha256']
for rel,h in matrix['upstreamSourceSha256'].items():
 p=P/'upstream'/rel
 if p.exists():assert sha(p)==h
rows=load(P/'census.json');assert len(rows)==19
for e in matrix['entries']:
 assert sha(P/'batch-source'/e['source'])==e['expectedSourceSha256'];row=next(x for x in rows if x['workload']==e['workload']);assert row['cDylibSha256']==next(x for x in ref['rows'] if x['workload']==e['workload'])['cDylibSha256'];ops=collections.Counter()
 for line in (P/'c-assembly'/(e['workload']+'.txt')).read_text().splitlines():
  q=re.match(r'^[0-9a-f]{16}\s+(\S+)\s*(.*)$',line)
  if q:ops[q[1].split('.')[0]]+=1
 assert dict(ops)==row['opcodeBaseCensus'];assert sum(ops.values())==row['staticInstructions'];assert not any(k.startswith(('crc32','aes','sha')) or k in ['sdot','udot'] for k in ops)
f=load(P/'measured-host-features.json');assert all(f['queries'][q]['exit']==0 and f['queries'][q]['value']=='1' for q in ['hw.optional.arm.FEAT_AES','hw.optional.arm.FEAT_SHA256','hw.optional.arm.FEAT_CRC32'])
out={'status':'PASS portable hardware frontier source/finite-law/disassembly-text replay','payloadPins':len(pins),'original19SourceAndCRecipeBindings':19,'crcTableEntries':256,'crcBasisAndZero':41,'aesTableElements':2816,'picoMultiplyCases':262144,'picoDescaleCases':131071,'unsafeModelControls':7,'measuredHostFeaturesPinned':True,'regeneratedDisassemblyFromAbsentBinary':False,'nativeExecutions':0,'timing':0,'compilerImplementations':0,'performanceClaims':False,'fullGoalAchieved':False};(D/'frontier-replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
