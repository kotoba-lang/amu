/usr/bin/ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 zebulun@100.66.28.79 'exec /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/Users/zebulun LANG=C LC_ALL=C TZ=UTC /Library/Developer/CommandLineTools/usr/bin/python3 -I -c '"'"'"""Read-only selected host identity; no compiler/guest execution or mutations."""
from pathlib import Path
import os,sys,json,hashlib,platform,signal,stat
signal.alarm(20)
MAX_FILE=512*1024*1024
CHUNK=1024*1024
supplied={'"'"'"'"'"'"'"'"'PATH'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'/usr/bin:/bin:/usr/sbin:/sbin'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'HOME'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'/Users/zebulun'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'LANG'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'C'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'LC_ALL'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'C'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'TZ'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'UTC'"'"'"'"'"'"'"'"'}
def snapshot(s):
 return {k:getattr(s,k) for k in ('"'"'"'"'"'"'"'"'st_dev'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'st_ino'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'st_mode'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'st_uid'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'st_gid'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'st_size'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'st_mtime_ns'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'st_ctime_ns'"'"'"'"'"'"'"'"')}
def pin(alias):
 alias=Path(alias);p=alias.resolve(strict=True);before=p.lstat()
 assert stat.S_ISREG(before.st_mode) and 0<=before.st_size<=MAX_FILE
 h=hashlib.sha256();total=0;reads=0
 with p.open('"'"'"'"'"'"'"'"'rb'"'"'"'"'"'"'"'"')as f:
  assert snapshot(os.fstat(f.fileno()))==snapshot(before)
  while True:
   b=f.read(CHUNK);reads+=1;assert reads<=513
   if not b:break
   total+=len(b);assert total<=before.st_size<=MAX_FILE;h.update(b)
  assert snapshot(os.fstat(f.fileno()))==snapshot(before)
 after=p.lstat();assert snapshot(before)==snapshot(after) and total==before.st_size and alias.resolve(strict=True)==p
 return {'"'"'"'"'"'"'"'"'pin'"'"'"'"'"'"'"'"':{'"'"'"'"'"'"'"'"'path'"'"'"'"'"'"'"'"':str(p),'"'"'"'"'"'"'"'"'bytes'"'"'"'"'"'"'"'"':total,'"'"'"'"'"'"'"'"'sha256'"'"'"'"'"'"'"'"':h.hexdigest()},'"'"'"'"'"'"'"'"'alias'"'"'"'"'"'"'"'"':str(alias),'"'"'"'"'"'"'"'"'before'"'"'"'"'"'"'"'"':snapshot(before),'"'"'"'"'"'"'"'"'after'"'"'"'"'"'"'"'"':snapshot(after),'"'"'"'"'"'"'"'"'streamReads'"'"'"'"'"'"'"'"':reads,'"'"'"'"'"'"'"'"'maximumFileBytes'"'"'"'"'"'"'"'"':MAX_FILE}
base=Path('"'"'"'"'"'"'"'"'/Library/Developer/CommandLineTools'"'"'"'"'"'"'"'"');sdkAlias=base/'"'"'"'"'"'"'"'"'SDKs/MacOSX.sdk'"'"'"'"'"'"'"'"';sdk=sdkAlias.resolve(strict=True);resource=(base/'"'"'"'"'"'"'"'"'usr/lib/clang/17'"'"'"'"'"'"'"'"').resolve(strict=True)
assert platform.system()=='"'"'"'"'"'"'"'"'Darwin'"'"'"'"'"'"'"'"' and platform.machine()=='"'"'"'"'"'"'"'"'arm64'"'"'"'"'"'"'"'"' and resource.is_dir() and sdk.is_dir()
dirs={str(p):snapshot(p.stat())for p in (sdk,resource)}
roles={'"'"'"'"'"'"'"'"'runtime'"'"'"'"'"'"'"'"':pin(sys.executable),'"'"'"'"'"'"'"'"'compiler'"'"'"'"'"'"'"'"':pin(base/'"'"'"'"'"'"'"'"'usr/bin/clang'"'"'"'"'"'"'"'"'),'"'"'"'"'"'"'"'"'linker'"'"'"'"'"'"'"'"':pin(base/'"'"'"'"'"'"'"'"'usr/bin/ld'"'"'"'"'"'"'"'"'),'"'"'"'"'"'"'"'"'libSystemTBD'"'"'"'"'"'"'"'"':pin(sdk/'"'"'"'"'"'"'"'"'usr/lib/libSystem.tbd'"'"'"'"'"'"'"'"')}
assert all(snapshot(Path(p).stat())==s for p,s in dirs.items())
env=dict(os.environ)
result={'"'"'"'"'"'"'"'"'status'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'READ_ONLY_SELECTED_ZEBULUN_HOST_IDENTITY_V2'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'host'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'zebulun@100.66.28.79'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'runtime'"'"'"'"'"'"'"'"':roles['"'"'"'"'"'"'"'"'runtime'"'"'"'"'"'"'"'"']['"'"'"'"'"'"'"'"'pin'"'"'"'"'"'"'"'"'],'"'"'"'"'"'"'"'"'environment'"'"'"'"'"'"'"'"':env,'"'"'"'"'"'"'"'"'environmentWitness'"'"'"'"'"'"'"'"':{'"'"'"'"'"'"'"'"'suppliedKeyNames'"'"'"'"'"'"'"'"':sorted(supplied),'"'"'"'"'"'"'"'"'missingKeyNames'"'"'"'"'"'"'"'"':sorted(set(supplied)-set(env)),'"'"'"'"'"'"'"'"'changedExpectedKeyNames'"'"'"'"'"'"'"'"':sorted(k for k in supplied if env.get(k)!=supplied[k]),'"'"'"'"'"'"'"'"'runtimeExtraKeyNames'"'"'"'"'"'"'"'"':sorted(set(env)-set(supplied)),'"'"'"'"'"'"'"'"'CFGeneratedKeyNames'"'"'"'"'"'"'"'"':sorted(k for k in env if k.startswith('"'"'"'"'"'"'"'"'__CF'"'"'"'"'"'"'"'"'))},'"'"'"'"'"'"'"'"'hostBinding'"'"'"'"'"'"'"'"':{'"'"'"'"'"'"'"'"'machine'"'"'"'"'"'"'"'"':'"'"'"'"'"'"'"'"'arm64'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'compiler'"'"'"'"'"'"'"'"':roles['"'"'"'"'"'"'"'"'compiler'"'"'"'"'"'"'"'"']['"'"'"'"'"'"'"'"'pin'"'"'"'"'"'"'"'"'],'"'"'"'"'"'"'"'"'interpreter'"'"'"'"'"'"'"'"':roles['"'"'"'"'"'"'"'"'runtime'"'"'"'"'"'"'"'"']['"'"'"'"'"'"'"'"'pin'"'"'"'"'"'"'"'"'],'"'"'"'"'"'"'"'"'linker'"'"'"'"'"'"'"'"':roles['"'"'"'"'"'"'"'"'linker'"'"'"'"'"'"'"'"']['"'"'"'"'"'"'"'"'pin'"'"'"'"'"'"'"'"'],'"'"'"'"'"'"'"'"'sdkAlias'"'"'"'"'"'"'"'"':str(sdkAlias),'"'"'"'"'"'"'"'"'sdk'"'"'"'"'"'"'"'"':str(sdk),'"'"'"'"'"'"'"'"'resourceDirectory'"'"'"'"'"'"'"'"':str(resource),'"'"'"'"'"'"'"'"'libraryPins'"'"'"'"'"'"'"'"':[roles['"'"'"'"'"'"'"'"'libSystemTBD'"'"'"'"'"'"'"'"']['"'"'"'"'"'"'"'"'pin'"'"'"'"'"'"'"'"']]},'"'"'"'"'"'"'"'"'stableFileSnapshots'"'"'"'"'"'"'"'"':roles,'"'"'"'"'"'"'"'"'directorySnapshots'"'"'"'"'"'"'"'"':dirs,'"'"'"'"'"'"'"'"'maximumPinnedFiles'"'"'"'"'"'"'"'"':4,'"'"'"'"'"'"'"'"'maximumFileBytes'"'"'"'"'"'"'"'"':MAX_FILE,'"'"'"'"'"'"'"'"'maximumTotalBytes'"'"'"'"'"'"'"'"':4*MAX_FILE,'"'"'"'"'"'"'"'"'nativeCompilerGuestCalls'"'"'"'"'"'"'"'"':0,'"'"'"'"'"'"'"'"'readOnly'"'"'"'"'"'"'"'"':True}
b=(json.dumps(result,sort_keys=True)+'"'"'"'"'"'"'"'"'\n'"'"'"'"'"'"'"'"').encode();assert len(b)<=65536
sys.stdout.buffer.write(b);sys.stdout.flush()
'"'"'' > /Users/junkawasaki/github/workspaces/codex/selected-zebulun-host-identity-source-v2-20261009-crc/actual.stdout 2> /Users/junkawasaki/github/workspaces/codex/selected-zebulun-host-identity-source-v2-20261009-crc/actual.stderr
