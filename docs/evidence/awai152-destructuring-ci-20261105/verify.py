#!/usr/bin/env python3
"""Low-load check of the updated corpus against the pinned CI-produced compiler."""
import hashlib,os,re,resource,shutil,subprocess,tempfile
from pathlib import Path
compiler=Path('/private/tmp/awai1824-ci-root-41891665699/public-macos-product/commands/provenance/amu-full-root.macho')
pack=Path('/private/tmp/awai154-fs2-darwin-gate/candidate.macho');src=Path('seed/tests/native-destructuring.kotoba').read_bytes()
assert hashlib.sha256(compiler.read_bytes()).hexdigest()=='703709f8bc10efe3b50ac23e5a80e48655049891bf66b13211745ce9aeb9fe50'
assert hashlib.sha256(pack.read_bytes()).hexdigest()=='f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d'
subprocess.run(['/usr/bin/codesign','--verify','--strict',str(compiler)],check=True,capture_output=True)
with tempfile.TemporaryDirectory(prefix='awai1824-destruct-',dir='/private/tmp') as d:
 root=Path(d);binary=root/'compiler';shutil.copyfile(compiler,binary);binary.chmod(0o700);(root/'source.kotoba').write_bytes(src)
 (root/'missing.kotoba').write_text('(defn main [] :i64 (let [{:keys [nope] :or {nope 1}} {:other 2}] nope))')
 fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
 if fd!=3:os.dup2(fd,3)
 def run(args,expected=0):
  p=subprocess.run([str(x) for x in args],cwd=root,pass_fds=(3,),env={'PATH':'/nonexistent'},capture_output=True,timeout=12,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CPU,(3,3)))
  if p.returncode!=expected:raise RuntimeError((args,p.returncode,p.stdout[-500:],p.stderr[-500:]))
  if expected==0 and p.stderr:raise RuntimeError(p.stderr[-500:])
  return p.stdout+p.stderr
 print('CHECK',run([binary,'check','source.kotoba']).decode().strip(),flush=True)
 out=run([binary,'check','missing.kotoba'],1)
 if b'E2111' not in out:raise RuntimeError(out[-500:])
 print('PASS absent record destructuring key refused E2111',flush=True)
 run([binary,'compile','source.kotoba','--target','aarch64-macos','--output','source.kseed']);out=run([binary,'extract-native','source.kseed','--symbol','main','--output','source.raw']);m=re.search(rb':offset (\d+), :length (\d+), :arity 0}',out)
 if not m or int(m[2])!=(root/'source.raw').stat().st_size:raise RuntimeError('extract')
 run([pack,'out.macho','source.raw','fs2-cli-stdio-general',m[1].decode()]);img=root/'signed.macho';shutil.copyfile(root/'out.macho',img);img.chmod(0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(img)],check=True,capture_output=True);run([img])
 print('PASS native corpus including present record default',hashlib.sha256(src).hexdigest(),flush=True)
 os.close(3)
 if fd!=3:os.close(fd)
