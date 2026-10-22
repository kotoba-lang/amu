from pathlib import Path
import gzip, hashlib, io, json, tarfile

HERE = Path(__file__).resolve().parent
W = HERE.parent
R = Path('/Users/junkawasaki/github/wt/amu-seed17')
D = R/'docs/evidence/coscientist-inverse-aes-20261007/vector-local-bounds'
folders = [
 'vector-emitter-local-bounds-v1-controls',
 'vector-emitter-local-bounds-native-build-v1-root',
 'vector-emitter-local-bounds-positive-v1-controls',
 'vector-emitter-local-bounds-positive-review-v1-width',
 'vector-emitter-local-bounds-positive-review-v1-native-controls',
 'vector-emitter-local-bounds-positive-actual-review-v1-width',
 'vector-emitter-original19-plan-v2-width',
 'vector-emitter-original19-native-v1-root',
 'vector-emitter-original19-actual-review-v1-width',
 'vector-emitter-original19-eligibility-census-v1-controls',
 'vector-emitter-param-result-context-design-v1-controls',
 'vector-emitter-param-result-context-review-v1-native-controls',
 'vector-emitter-param-result-design-review-v1-native-controls',
 'vector-emitter-param-result-context-design-v2-controls',
 'vector-emitter-fixedpoint-plan-v1-width',
 'vector-emitter-fixedpoint-review-v1-native-controls',
 'vector-emitter-fixedpoint-executed-driver-v1-width',
 'vector-emitter-fixedpoint-actual-review-v1-controls',
 'vector-emitter-fixedpoint-native-v1-root',
]
sha = lambda b: hashlib.sha256(b).hexdigest()
assert not D.exists(), 'new immutable checkpoint only'
for folder in ['vector-emitter-local-bounds-positive-v1-controls',
               'vector-emitter-original19-native-v1-root',
               'vector-emitter-fixedpoint-native-v1-root']:
 p = W/folder
 assert (p/'terminal.json').exists() and not (p/'failure.json').exists()
objects = {}
for folder in folders:
 p = W/folder
 assert p.is_dir(), folder
 for f in sorted(p.rglob('*')):
  assert not f.is_symlink(), str(f)
  if f.is_file() and '__pycache__' not in f.parts:
   objects[str(f.relative_to(W))] = f.read_bytes()
assert len(objects) <= 600 and sum(map(len, objects.values())) <= 48*1024*1024
rows = [{'path':k,'bytes':len(v),'sha256':sha(v)} for k,v in sorted(objects.items())]
manifest = {'format':'amu.vector-local-bounds-capture/v1','files':rows,
            'captureOnly':True,'portableNativeReplay':False,
            'claims':'single positive actual omission; original19 byte regression; three candidate generations; no timing/C gain/shared CID cache/product adoption',
            'limits':{'maxFiles':600,'maxExpandedBytes':48*1024*1024}}
D.mkdir(parents=True)
with (D/'capture.tar.gz').open('wb') as out:
 with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0) as zipped:
  with tarfile.open(fileobj=zipped,mode='w|') as archive:
   for k,v in sorted(objects.items()):
    info=tarfile.TarInfo(k);info.size=len(v);info.mode=0o644;info.mtime=0
    archive.addfile(info,io.BytesIO(v))
manifest['archiveSHA256']=sha((D/'capture.tar.gz').read_bytes())
manifest['archiveBytes']=(D/'capture.tar.gz').stat().st_size
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for folder,label in [('vector-emitter-local-bounds-positive-v1-controls','positive'),
                     ('vector-emitter-original19-native-v1-root','original19'),
                     ('vector-emitter-fixedpoint-native-v1-root','fixedpoint')]:
 (D/(label+'-report.json')).write_bytes((W/folder/'report.json').read_bytes())
(D/'capture.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'directory':str(D),'files':len(rows),'expandedBytes':sum(r['bytes']for r in rows),'archiveBytes':manifest['archiveBytes'],'archiveSHA256':manifest['archiveSHA256']}))
