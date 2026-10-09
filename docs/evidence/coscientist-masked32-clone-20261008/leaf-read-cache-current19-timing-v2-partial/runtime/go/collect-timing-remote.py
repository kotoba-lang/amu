"""Read-only finite saved-output streaming collector. Never imports timing driver."""
from pathlib import Path
import json,hashlib,sys,stat,tarfile,gzip,signal,io
ROOT=Path('/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-timing-v2-root');CAP=805306368;COUNT=65536;H=lambda b:hashlib.sha256(b).hexdigest()
def main():
 signal.alarm(600);assert ROOT.is_dir()and not ROOT.is_symlink();registry=json.loads((ROOT/'source/source-pins.json').read_bytes());files=[];total=0
 for dirname in ['source','control','timing']:
  folder=ROOT/dirname
  if not folder.exists():assert dirname=='timing';continue
  for p in sorted(folder.rglob('*')):
   s=p.lstat();assert not p.is_symlink()
   if stat.S_ISDIR(s.st_mode):continue
   assert stat.S_ISREG(s.st_mode)and s.st_size<=16777216
   total+=s.st_size;assert total<=CAP and len(files)<COUNT-1;files.append((p,str(p.relative_to(ROOT)),s.st_size))
 assert {n.removeprefix('source/')for _,n,_ in files if n.startswith('source/')}==set(registry)|{'source-pins.json'}
 members=[];hashed={}
 for p,n,size in files:
  b=p.read_bytes();assert len(b)==size
  r=dict(path=n,bytes=size,sha256=H(b));members.append(r);hashed[n]=r['sha256']
  if n.startswith('source/')and n!='source/source-pins.json':assert {k:r[k]for k in ['bytes','sha256']}==registry[n[7:]]
 receipt=(json.dumps(dict(status='READONLY_TIMING_COLLECTION_ONLY_NOT_ACTUAL_ACCEPTANCE',root=str(ROOT),sourcePinsSHA256=H((ROOT/'source/source-pins.json').read_bytes()),members=members,maximumMembers=COUNT,maximumExpandedBytes=CAP,compilerCalls=0,nativeCalls=0,timingCalls=0),indent=2)+'\n').encode();assert len(receipt)<=16777216 and total+len(receipt)<=CAP
 assert sum(512+((size+511)//512)*512 for _,_,size in files)+512+((len(receipt)+511)//512)*512+10240<=872415232
 class Bounded:
  def __init__(self,out):self.out=out;self.n=0
  def write(self,b):self.n+=len(b);assert self.n<=872415232;return self.out.write(b)
  def flush(self):self.out.flush()
 with gzip.GzipFile(fileobj=Bounded(sys.stdout.buffer),mode='wb',mtime=0)as z,tarfile.open(fileobj=z,mode='w|',format=tarfile.USTAR_FORMAT)as tar:
  for p,n,size in files:
   b=p.read_bytes();assert len(b)==size and H(b)==hashed[n];q=tarfile.TarInfo(n);q.size=size;q.mode=0o444;q.mtime=0;tar.addfile(q,io.BytesIO(b))
  q=tarfile.TarInfo('collection-receipt.json');q.size=len(receipt);q.mode=0o444;q.mtime=0;tar.addfile(q,io.BytesIO(receipt))
if __name__=='__main__':main()
