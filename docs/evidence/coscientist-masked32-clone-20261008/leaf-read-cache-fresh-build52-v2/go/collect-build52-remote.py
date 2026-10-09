from pathlib import Path
import sys,json,hashlib,tarfile,io,gzip,signal
root=Path('/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-v2-root')
signal.alarm(120)
assert root.is_dir() and not root.is_symlink()
assert hashlib.sha256((root/'package/source-pins.json').read_bytes()).hexdigest()=='b12caa329a1532399cab8b2ee94b5096bb1811d952aa76c3287b672b05917b4b'
files={}
for dirname in ['build52','control']:
 for p in sorted((root/dirname).rglob('*')):
  if p.is_dir():continue
  assert p.is_file() and not p.is_symlink() and p.stat().st_size<=16777216
  files[str(p.relative_to(root))]=p.read_bytes()
for name in ['package/manifest.json','package/source-pins.json']:
 files[name]=(root/name).read_bytes()
assert len(files)<=4096 and sum(map(len,files.values()))<=67108864
receipt=dict(status='READONLY_BUILD52_RECEIPT_COLLECTION_ONLY',members=[dict(path=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in sorted(files.items())],sourcePinsSHA256='b12caa329a1532399cab8b2ee94b5096bb1811d952aa76c3287b672b05917b4b',root=str(root),compilerCalls=0,nativeCalls=0)
files['collection-receipt.json']=json.dumps(receipt,indent=2).encode()+b'\n'
with gzip.GzipFile(fileobj=sys.stdout.buffer,mode='wb',mtime=0) as z,tarfile.open(fileobj=z,mode='w|',format=tarfile.USTAR_FORMAT) as t:
 for n,b in sorted(files.items()):
  q=tarfile.TarInfo(n);q.size=len(b);q.mode=0o444;q.mtime=0;t.addfile(q,io.BytesIO(b))
