/usr/bin/ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 zebulun@100.66.28.79 'exec /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/Users/zebulun LANG=C LC_ALL=C TZ=UTC /Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9 -I -c '"'"'from pathlib import Path
import json,hashlib,base64,sys,stat,signal
signal.alarm(60)
root=Path('"'"'"'"'"'"'"'"'/Users/zebulun/github/workspaces/codex/tc-hft-current19-quiet-c-packet-v3-20261009-root'"'"'"'"'"'"'"'"');q=json.loads((root/'"'"'"'"'"'"'"'"'consumer-qualification-v2-outputs/report.json'"'"'"'"'"'"'"'"').read_bytes());assert q['"'"'"'"'"'"'"'"'status'"'"'"'"'"'"'"'"']=='"'"'"'"'"'"'"'"'COMPLETE_CURRENT17_CONSUMER342_V2_FUNCTIONAL_DIAGNOSTIC_ONLY'"'"'"'"'"'"'"'"' and q['"'"'"'"'"'"'"'"'consumerCalls'"'"'"'"'"'"'"'"']==342 and q['"'"'"'"'"'"'"'"'warmupAndBodyCalls'"'"'"'"'"'"'"'"']==741
t=json.loads((root/'"'"'"'"'"'"'"'"'consumer-qualification-v2-outputs/terminal.json'"'"'"'"'"'"'"'"').read_bytes());assert t['"'"'"'"'"'"'"'"'allChildrenClosed'"'"'"'"'"'"'"'"'] and not t['"'"'"'"'"'"'"'"'failure'"'"'"'"'"'"'"'"']
assert hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()=='"'"'"'"'"'"'"'"'6b24be8ba00c4abc8b3e7e2620bd710e2cf7a4312d00c147f8f05fbb6f3d297a'"'"'"'"'"'"'"'"'
rows=[];total=0
for d in [root/'"'"'"'"'"'"'"'"'consumer-qualification-v2-outputs'"'"'"'"'"'"'"'"',root/'"'"'"'"'"'"'"'"'root-current17-qualification-v2-GO'"'"'"'"'"'"'"'"']:
 for p in sorted(d.rglob('"'"'"'"'"'"'"'"'*'"'"'"'"'"'"'"'"')):
  assert not p.is_symlink()
  if p.is_dir():continue
  a=p.lstat();assert stat.S_ISREG(a.st_mode) and a.st_size<=16777216
  b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns) and len(b)==a.st_size
  total+=len(b);assert total<=67108864 and len(rows)<4096
  rows.append(dict(path=str(p.relative_to(root)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),base64=base64.b64encode(b).decode('"'"'"'"'"'"'"'"'ascii'"'"'"'"'"'"'"'"')))
b=(json.dumps(dict(status='"'"'"'"'"'"'"'"'READ_ONLY_CURRENT17_CONSUMER342_V2_CLOSED_OUTPUT_COLLECTION'"'"'"'"'"'"'"'"',root=str(root),files=rows,logicalBytes=total),separators=('"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'))+'"'"'"'"'"'"'"'"'\n'"'"'"'"'"'"'"'"').encode();assert len(b)<=100663296
sys.stdout.buffer.write(b);sys.stdout.flush()
'"'"'' > /Users/junkawasaki/github/workspaces/codex/current17-consumer-qualify342-v2-collection-root-20261009/actual.stdout 2> /Users/junkawasaki/github/workspaces/codex/current17-consumer-qualify342-v2-collection-root-20261009/actual.stderr
