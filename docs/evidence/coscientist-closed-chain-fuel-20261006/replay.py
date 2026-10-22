from pathlib import Path
import json,hashlib,tarfile,tempfile,subprocess
e=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,z in json.loads((e/'archive-manifest.json').read_text()).items():assert sha(e/name)==z['sha256'] and (e/name).stat().st_size==z['bytes']
root=Path(tempfile.mkdtemp(prefix='amu-closed-fuel-replay-'))
for name in ['native-proof.tgz','timing.tgz']:
 with tarfile.open(e/name) as t:t.extractall(root,filter='data')
w=root/'amu-closed-chain-fuel-20261006';(root/'remote-evidence').rename(w/'remote-evidence')
for name,digest in json.loads((w/'snapshot-pins.json').read_text())['files'].items():assert sha(w/'source-snapshot'/name)==digest
for name,digest in json.loads((w/'source-pins.json').read_text()).items():assert sha(w/name)==digest
assert len({sha(w/f'seed-{g}.bin') for g in [2,3,4]})==1;assert sha(w/'seed-4.bin')=='da56b44a5f5cd9736009016e2cd85b1b37613b9c51717c2623a326fc18f72500'
for script in ['instruction-audit.py','timing-audit.py']:
 before=(w/script.replace('.py','.json')).read_bytes()
 s=(w/script).read_text().replace('/private/tmp/amu-static-vector-chain-20261006',str(w/'baseline-snapshot')).replace('/Users/junkawasaki/github/wt/amu-seed17/seed',str(w/'source-snapshot/seed')).replace('/private/tmp/amu-closed-chain-fuel-20261006',str(w));exec(compile(s,str(w/script),'exec'),{'__file__':str(w/script),'__name__':'__main__'})
 assert (w/script.replace('.py','.json')).read_bytes()==before
 assert before==(e/script.replace('.py','.json')).read_bytes()
q=subprocess.run(['python3',str(w/'replay-analysis.py')],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr;assert (w/'state-replay.json').read_bytes()==(e/'state-replay.json').read_bytes()
out={'status':'complete-extracted-archive-independent-native-CFG-state-oracle-raw-timing-replay','archiveHashes':True,'allSnapshotAndSourcePinsVerified':True,'threeGenerationFixedPointVerified':True,'nativeInstructionAndBranchAuditRecomputed':True,'handStateOraclesRecomputed':11052,'nativeMutationRefusalsRetained':3,'permanentNativeRunsRetained':25658,'rawTimingAuditExact':True,'acceptedTriples':30,'freshNativeExecutionsInReplay':0,'productPromoted':False,'COrBetterAchieved':False};(e/'replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
