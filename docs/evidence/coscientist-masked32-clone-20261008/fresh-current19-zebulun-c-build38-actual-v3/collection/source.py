from pathlib import Path
import json,hashlib,base64,sys,stat,signal
signal.alarm(60)
root=Path('/Users/zebulun/github/workspaces/codex/tc-hft-current19-quiet-c-packet-v3-20261009-root');report=root/'C-build-outputs/report.json';assert report.is_file()
q=json.loads(report.read_bytes());assert q['status']=='COMPLETE_CURRENT19_FRESH_C_BUILD38_SOURCE_IDENTITY_ONLY' and q['closedCompilerCalls']==38 and q['CBuildCalls']==19 and q['guestCalls']==0
assert hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()=='6b24be8ba00c4abc8b3e7e2620bd710e2cf7a4312d00c147f8f05fbb6f3d297a'
rows=[];total=0
for d in [root/'C-build-outputs',root/'root-C-build-GO']:
 for p in sorted(d.rglob('*')):
  assert not p.is_symlink()
  if p.is_dir():continue
  a=p.lstat();assert stat.S_ISREG(a.st_mode) and a.st_size<=16777216
  b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns) and len(b)==a.st_size
  total+=len(b);assert total<=67108864 and len(rows)<512
  rows.append(dict(path=str(p.relative_to(root)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),base64=base64.b64encode(b).decode('ascii')))
b=(json.dumps(dict(status='READ_ONLY_CURRENT19_C_BUILD38_CLOSED_OUTPUT_COLLECTION',root=str(root),files=rows,logicalBytes=total),separators=(',',':'))+'\n').encode();assert len(b)<=100663296
sys.stdout.buffer.write(b);sys.stdout.flush()
