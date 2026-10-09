"""Remote standalone installer. Actual filesystem operations only after reviewed root GO."""
from pathlib import Path,PurePosixPath
import base64,hashlib,json,os,stat,sys
MAX_PAYLOAD=8*1024*1024;MAX_LOGICAL=8*1024*1024;MAX_FILES=256
ROOT=Path('/Users/zebulun/github/workspaces/codex/tc-hft-current19-quiet-c-packet-v3-20261009-root')
H=lambda b:hashlib.sha256(b).hexdigest()
def unique(pairs):
 d={}
 for k,v in pairs:assert k not in d;d[k]=v
 return d
def decode(raw,expectedPayload,expectedManifest):
 assert len(raw)<=MAX_PAYLOAD and H(raw)==expectedPayload
 q=json.loads(raw,object_pairs_hook=unique);assert set(q)=={'schema','manifest','files'} and q['schema']=='CURRENT19_INSTALL_ENVELOPE_V1'
 m=q['manifest'];assert H(json.dumps(m,sort_keys=True,separators=(',',':')).encode())==expectedManifest
 assert set(m)=={'schema','remoteRoot','files','exactFiles','exactLogicalBytes','owners','executionCredit'} and m['schema']=='CURRENT19_CORE_CONSUMER_CBUILD_PACKET_V1' and m['remoteRoot']==str(ROOT) and m['executionCredit'] is False
 assert len(m['files'])==m['exactFiles']==len(q['files']) and 1<=m['exactFiles']<=MAX_FILES
 assert sum(x['bytes'] for x in m['files'])==m['exactLogicalBytes']<=MAX_LOGICAL
 out=[];seen=set()
 for r,v in zip(m['files'],q['files']):
  assert set(r)=={'source','relativePath','bytes','sha256','owner'} and r['owner'] in m['owners']
  assert set(v)=={'relativePath','bytes','sha256','base64'} and all(v[k]==r[k] for k in ('relativePath','bytes','sha256'))
  s=v['relativePath'];assert type(s)is str and s and '\\'not in s and '\x00'not in s and len(s)<=256
  p=PurePosixPath(s);assert not p.is_absolute() and '..'not in p.parts and '.'not in s.split('/') and str(p)==s and len(p.parts)<=12 and s not in seen and s!='install-receipt.json'
  assert not any(s.startswith(x+'/')or x.startswith(s+'/') for x in seen);seen.add(s)
  assert type(v['bytes'])is int and 0<=v['bytes']<=MAX_LOGICAL
  b=base64.b64decode(v['base64'],validate=True);assert len(b)==v['bytes'] and H(b)==v['sha256'];out.append((s,b))
 return m,out
def main():
 assert len(sys.argv)==4
 expectedPayload,expectedManifest,runtimeHash=sys.argv[1:]
 executable=Path(sys.executable).resolve();assert H(executable.read_bytes())==runtimeHash
 assert Path.home()==Path('/Users/zebulun') and ROOT.parent.resolve()==ROOT.parent and ROOT.parent.is_dir()
 b=sys.stdin.buffer.read(MAX_PAYLOAD+1);m,files=decode(b,expectedPayload,expectedManifest)
 # Entire payload checked before creating anything. Existing root, including symlink, is refused.
 assert not os.path.lexists(ROOT);ROOT.mkdir(mode=0o700)
 for s,b in files:
  p=ROOT/s;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  assert p.parent.resolve()==p.parent
  fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
  try:
   at=0
   while at<len(b):
    n=os.write(fd,b[at:at+65536]);assert n>0;at+=n
   os.fsync(fd)
  finally:os.close(fd)
  assert stat.S_ISREG(p.lstat().st_mode) and p.read_bytes()==b
 receipt={'status':'CLOSED_CURRENT19_PACKET_INSTALL_ONLY','files':len(files),'logicalBytes':m['exactLogicalBytes'],'payloadSHA256':expectedPayload,'manifestCanonicalSHA256':expectedManifest,'runtimeExecutable':str(executable),'runtimeSHA256':runtimeHash,'nativeCompilerGuestTimingCalls':0}
 rb=(json.dumps(receipt,sort_keys=True)+'\n').encode();fd=os.open(ROOT/'install-receipt.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
 try:assert os.write(fd,rb)==len(rb);os.fsync(fd)
 finally:os.close(fd)
 fd=os.open(ROOT,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
 sys.stdout.buffer.write(rb);sys.stdout.flush()
if __name__=='__main__':main()
