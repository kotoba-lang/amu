"""Read-only saved-evidence collector; never imports or runs functional driver."""
from pathlib import Path
import sys,json,hashlib,tarfile,io,gzip,signal,stat
root=Path('/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-fresh-consumer-functional285-v1-root')
SP='120c90f7823f649fae7f6998c5daa314396d0da97998db88ebf7676d04a191d8'
H=lambda b:hashlib.sha256(b).hexdigest()
signal.alarm(120)
assert root.is_dir() and not root.is_symlink()
assert H((root/'source/source-pins.json').read_bytes())==SP
files={};present=[];absent=[]
for dirname in ['source','control','functional285']:
 parent=root/dirname
 if not parent.exists():
  assert dirname=='functional285';absent.append(dirname);continue
 present.append(dirname)
 assert stat.S_ISDIR(parent.lstat().st_mode) and not parent.is_symlink()
 for p in sorted(parent.rglob('*')):
  st=p.lstat();assert not p.is_symlink()
  if stat.S_ISDIR(st.st_mode):continue
  assert stat.S_ISREG(st.st_mode) and st.st_size<=16777216
  assert len(files)<4095 and sum(map(len,files.values()))+st.st_size<=67108864
  b=p.read_bytes();assert len(b)==st.st_size;files[str(p.relative_to(root))]=b
registry=json.loads(files['source/source-pins.json'])
assert {n.removeprefix('source/') for n in files if n.startswith('source/')}==set(registry)|{'source-pins.json'}
for n,r in registry.items():assert len(files['source/'+n])==r['bytes'] and H(files['source/'+n])==r['sha256']
receipt=dict(status='READONLY_FRESH_FUNCTIONAL285_RECEIPT_COLLECTION_ONLY',members=[dict(path=n,bytes=len(b),sha256=H(b)) for n,b in sorted(files.items())],sourcePinsSHA256=SP,root=str(root),presentSubtrees=present,absentSubtrees=absent,functionalTerminalPresent='functional285/terminal.json' in files,functionalReportPresent='functional285/report.json' in files,compilerCalls=0,nativeCalls=0,guestCalls=0,timingCalls=0)
files['collection-receipt.json']=json.dumps(receipt,indent=2).encode()+b'\n'
assert len(files)<=4096 and sum(map(len,files.values()))<=67108864
buf=io.BytesIO()
with gzip.GzipFile(fileobj=buf,mode='wb',mtime=0) as z,tarfile.open(fileobj=z,mode='w|',format=tarfile.USTAR_FORMAT) as t:
 for n,b in sorted(files.items()):
  q=tarfile.TarInfo(n);q.size=len(b);q.mode=0o444;q.mtime=0;t.addfile(q,io.BytesIO(b))
assert len(buf.getvalue())<=67108864
sys.stdout.buffer.write(buf.getvalue());sys.stdout.buffer.flush()
