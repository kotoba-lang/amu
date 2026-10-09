"""Saved-file generated producer guard. No process or native operations."""
from pathlib import Path
import hashlib,json,stat,re

def checked(p,r,cap=16777216):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and 0<s.st_size<=cap
 b=p.read_bytes();t=p.lstat();assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns)
 assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256'];return b

def validate_producer(pr,go,spSHA,prSHA):
 from artifact_admission import accept_artifact_observation
 O=Path(pr['freshOutputRoot']);p=O/'observer-producer.json';s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and 0<s.st_size<=16384
 raw=p.read_bytes();r=json.loads(raw)
 assert set(r)=={'format','rootGO','sourcePinsSHA256','preregistrationSHA256','source','native','container','evidence'}
 assert r['format']=='ctx-observer-generated-producer/v2'and r['rootGO']==go and r['sourcePinsSHA256']==spSHA and r['preregistrationSHA256']==prSHA
 checked(go['path'],go)
 assert r['source']['path']==str(O/'unity-observer.kotoba')and r['source']['sha256']==pr['sourceSHA256'];checked(r['source']['path'],r['source'],4194560)
 assert r['native']['path']==str(O/'observer.bin')and r['container']['path']==str(O/'observer.kseed')and r['evidence']['path']==str(O/'observer-producer-evidence.json')
 native=checked(r['native']['path'],r['native'],4194304);container=checked(r['container']['path'],r['container'],4194560)
 m=re.match(rb'KSEED1 ([1-9][0-9]{0,9}) 1\nmain 0 0\n\n',container);assert m and len(native)==int(m[1])and container[m.end():]==native
 rows=json.loads(checked(r['evidence']['path'],r['evidence']));assert len(rows)==2
 for i,row in enumerate(rows):
  case=pr['cases'][i];assert row['index']==i+1 and row['label']==case['label']and row['nativeArgv']==case['nativeArgv']and row['environment']==pr['environment']
  assert row['state']=='terminal'and row['returncode']==0 and row['waitEntered']is True and row['waitUncertain']is False and row['failure']is None and row['captureStopAcknowledged']is True and row['signalingAuthorityRetired']is True and not row['watchdogErrors']
  assert accept_artifact_observation(row['controllerObservation'])is True
  for name,cap in [('stdout',8388608),('stderr',1048576),('limitJournal',65536),('memoryJournal',16777216)]:
   suffix={'limitJournal':'.limit-journal.jsonl','memoryJournal':'.memory-journal.jsonl'}.get(name,'.'+name)
   checked(O/(case['label']+suffix),row[name],cap)
  sealPath=O/(case['label']+'.admission.json');seal=json.loads(sealPath.read_bytes());assert seal['nativeArgv']==case['nativeArgv']and seal['rootGO']==go and seal['sourcePinsSHA256']==spSHA and seal['preregistrationSHA256']==prSHA
  assert row['argv'][5]==hashlib.sha256(sealPath.read_bytes()).hexdigest()
 return r
