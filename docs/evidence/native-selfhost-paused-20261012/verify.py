#!/usr/bin/env python3
"""Offline custody check only: never executes compiler, guest, SSH or benchmarks."""
import hashlib,json,pathlib,subprocess,tarfile
root=pathlib.Path(__file__).resolve().parent
repo=root.parents[2]
checkpoint=json.loads((root/'checkpoint.json').read_text())
assert checkpoint['goal_status']=='paused' and not checkpoint['goal_achieved']
archive=root/checkpoint['evidence_archive']['path']
assert archive.stat().st_size==checkpoint['evidence_archive']['bytes']
assert hashlib.sha256(archive.read_bytes()).hexdigest()==checkpoint['evidence_archive']['sha256']
reintegration=json.loads((root/'reintegration.json').read_text())
raw=root/'reintegration-raw.tgz'
assert raw.stat().st_size==reintegration['rawArchiveBytes']
assert hashlib.sha256(raw.read_bytes()).hexdigest()==reintegration['rawArchiveSHA256']
old_images=root/'main-pre-policy-native19.tgz'
assert old_images.stat().st_size==reintegration['mainBaselineArchiveBytes']
assert hashlib.sha256(old_images.read_bytes()).hexdigest()==reintegration['mainBaselineArchiveSHA256']
inventory=json.loads((root/'inventory.json').read_text())
with tarfile.open(archive,'r:gz') as t:
 members=t.getmembers(); assert len(members)==len(inventory)
 assert {m.name for m in members}=={i['path'] for i in inventory}
 for row in inventory:
  path=pathlib.PurePosixPath(row['path']);assert not path.is_absolute() and '..' not in path.parts
  m=t.getmember(row['path']);assert m.isfile()
  data=t.extractfile(m).read();assert len(data)==row['bytes']
  assert hashlib.sha256(data).hexdigest()==row['sha256'],row['path']
 prefix='workspace/held-compiler-cli30-bounded-balanced-byte-tree-token-capacity-picojpeg-fixedpoint6-source-v4-20261012-next/run-outputs/'
 for suffix,key in [('bin','native_sha256'),('kseed','container_sha256')]:
  bodies=[t.extractfile(prefix+generation+'.'+suffix).read() for generation in ['G2','G3','G4']]
  assert bodies[0]==bodies[1]==bodies[2]
  assert hashlib.sha256(bodies[0]).hexdigest()==checkpoint['fixed_point'][key]
 for row in checkpoint['source_modules']:
  data=t.extractfile('source/'+row['path']).read()
  assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],row['path']
print('PASS: 634 archived files, 16 adopted source modules, G2/G3/G4 native + containers byte-identical; goal remains paused. No native work executed.')
