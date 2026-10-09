/usr/bin/ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 zebulun@100.66.28.79 'exec /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/Users/zebulun LANG=C LC_ALL=C TZ=UTC /Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9 -I -c '"'"'ROOT='"'"'"'"'"'"'"'"'/Users/zebulun/github/workspaces/codex/tc-hft-current19-quiet-c-packet-v3-20261009-root'"'"'"'"'"'"'"'"'
PHASE='"'"'"'"'"'"'"'"'/Users/zebulun/github/workspaces/codex/tc-hft-current19-quiet-c-packet-v3-20261009-root/source/current17-qualification'"'"'"'"'"'"'"'"'
GODIR='"'"'"'"'"'"'"'"'/Users/zebulun/github/workspaces/codex/tc-hft-current19-quiet-c-packet-v3-20261009-root/root-current17-qualification-GO'"'"'"'"'"'"'"'"'
LENGTH=441022
DIGEST='"'"'"'"'"'"'"'"'adf92f9af4c636d55f529719036a102e10a7d58792838debc1a7549d1f9a482e'"'"'"'"'"'"'"'"'
PYTHON='"'"'"'"'"'"'"'"'/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9'"'"'"'"'"'"'"'"'
GOPATH='"'"'"'"'"'"'"'"'/Users/zebulun/github/workspaces/codex/tc-hft-current19-quiet-c-packet-v3-20261009-root/root-current17-qualification-GO/root-go.json'"'"'"'"'"'"'"'"'
from pathlib import Path
import os,sys,json,hashlib,base64
root=Path(ROOT); phase=Path(PHASE); out=Path(GODIR)
assert root.resolve()==root and root.is_dir()
assert json.loads((root/'"'"'"'"'"'"'"'"'install-receipt.json'"'"'"'"'"'"'"'"').read_bytes())['"'"'"'"'"'"'"'"'status'"'"'"'"'"'"'"'"']=='"'"'"'"'"'"'"'"'CLOSED_CURRENT19_PACKET_INSTALL_ONLY'"'"'"'"'"'"'"'"'
raw=sys.stdin.buffer.read(1048577);assert len(raw)==LENGTH and hashlib.sha256(raw).hexdigest()==DIGEST
files=json.loads(raw);decoded={}
for name,r in files.items():
 p=Path(name);assert p.parent in (phase,out) and p.name not in ('"'"'"'"'"'"'"'"''"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'.'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'..'"'"'"'"'"'"'"'"')
 b=base64.b64decode(r['"'"'"'"'"'"'"'"'base64'"'"'"'"'"'"'"'"'],validate=True);assert len(b)==r['"'"'"'"'"'"'"'"'bytes'"'"'"'"'"'"'"'"'] and hashlib.sha256(b).hexdigest()==r['"'"'"'"'"'"'"'"'sha256'"'"'"'"'"'"'"'"'];decoded[p]=b
assert not phase.exists() and not out.exists()
phase.mkdir(mode=0o700);out.mkdir(mode=0o700)
for p,b in decoded.items():
 with p.open('"'"'"'"'"'"'"'"'xb'"'"'"'"'"'"'"'"') as f:f.write(b);f.flush();os.fsync(f.fileno())
 p.chmod(0o400);assert p.read_bytes()==b
argv=[PYTHON,str(phase/'"'"'"'"'"'"'"'"'run.py'"'"'"'"'"'"'"'"'),GOPATH]
os.execve(PYTHON,argv,{'"'"'"'"'"'"'"'"'PATH'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'/usr/bin:/bin:/usr/sbin:/sbin'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'HOME'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'/Users/zebulun'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'LANG'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'C'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'LC_ALL'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'C'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'TZ'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'UTC'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'PYTHONNOUSERSITE'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'1'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'PYTHONDONTWRITEBYTECODE'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'1'"'"'"'"'"'"'"'"'})
'"'"'' < /Users/junkawasaki/github/workspaces/codex/current17-consumer-qualify342-v1-dispatch-root-20261009/payload.json > /Users/junkawasaki/github/workspaces/codex/current17-consumer-qualify342-v1-dispatch-root-20261009/actual.stdout 2> /Users/junkawasaki/github/workspaces/codex/current17-consumer-qualify342-v1-dispatch-root-20261009/actual.stderr
