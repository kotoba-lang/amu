from pathlib import Path
import json,hashlib,tarfile,tempfile,subprocess
e=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,z in json.loads((e/'archive-manifest.json').read_text()).items():assert sha(e/name)==z['sha256'] and (e/name).stat().st_size==z['bytes']
root=Path(tempfile.mkdtemp(prefix='amu-fuel-census-replay-'))
with tarfile.open(e/'native-diagnostic.tgz') as t:t.extractall(root,filter='data')
w=root/'amu-statemate-fuel-census-20261006'
for name,digest in json.loads((w/'snapshot-pins.json').read_text()).items():assert sha(w/'source-snapshot'/name)==digest
assert sha(w/'quiet-statemate.bin')==sha(w/'product-statemate.bin')=='5500419beb37f71f0c2ee09c64233170bc853378b082b694025b45ccbe32152d';assert (w/'quiet-statemate.offset').read_text().strip()=='85576'
q=subprocess.run(['python3',str(w/'replay-analysis.py')],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr;assert (w/'summary.json').read_bytes()==(e/'summary.json').read_bytes()
for name,count in [('transaction-proof.json',10),('masked-transaction-proof.json',12)]:
 z=json.loads((w/name).read_text());assert z['groups']==count
 for v in z['rows']:
  assert sum(c[1] for c in v['counts'])==v['expectedCompletedCharges'];assert ':remaining '+str(v['expectedRemaining'])+'}' in v['observation']['report']
result={'status':'complete-extracted-archive-source-site-counter-state-replay','archiveChecksums':True,'allSnapshotInputsHashed':True,'disabledProductBytesAndEntryExact':True,'summaryExact':True,'originalStateGroups':30,'independentCalibrationGroups':42,'transactionGroups':22,'nativeExecutionsRetained':248,'freshNativeExecutionsInReplay':0,'productChanged':False,'performanceClaim':False};(e/'replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
