import hashlib,os,re,resource,shutil,subprocess,tempfile
from pathlib import Path
repo=Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute');compiler=Path('/tmp/codex-amu-1762/seed/bootstrap/aarch64-macos/amu-full-root.macho');packager=Path('/private/tmp/awai-oci-range/candidate.macho')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for path,pin in [(compiler,'920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6'),(packager,'df0e94211a35d84901ebcf2a8620cb653140d957732474ff77bd0cdd5b5bf4c5')]:
 if sha(path)!=pin:raise ValueError('pin mismatch')
with tempfile.TemporaryDirectory(prefix='awai152-wp03-build-',dir='/private/tmp') as d:
 root=Path(d);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
 if fd!=3:os.dup2(fd,3)
 def run(cmd):
  x=subprocess.run([str(q) for q in cmd],cwd=root,pass_fds=(3,),capture_output=True,timeout=15,env={'PATH':'/nonexistent'},preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CPU,(3,3)))
  if x.returncode or x.stderr:raise RuntimeError((x.returncode,x.stdout[-300:],x.stderr[-300:]))
  return x.stdout
 src=(repo/'seed/macos-process-watch-packager.kotoba').read_text();assert src.count('(ds-imm 10 1) (ds-and 9 25 10) (ds-cmpi 9 1) (ds-b 0x54000001 9)')==1;src=src.replace('(ds-imm 10 1) (ds-and 9 25 10) (ds-cmpi 9 1) (ds-b 0x54000001 9)','(ds-cmpi 25 0) (ds-b 0x54000001 9)');(root/'e.kotoba').write_text(src);run([compiler,'compile','e.kotoba','--target','aarch64-macos','--output','e.kseed']);out=run([compiler,'extract-native','e.kseed','--symbol','main','--output','e.raw']);m=re.search(rb':offset (\d+), :length (\d+), :arity 0}',out)
 if not m or int(m[2])!=(root/'e.raw').stat().st_size:raise RuntimeError('extract')
 run([packager,'e-unsigned.macho','e.raw','fs2-cli-stdio-general',m[1].decode()]);em=root/'e.macho';shutil.copyfile(root/'e-unsigned.macho',em);em.chmod(0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(em)],check=True,capture_output=True);run([em,'watch-unsigned.macho']);img=root/'watch.macho';shutil.copyfile(root/'watch-unsigned.macho',img);img.chmod(0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(img)],check=True,capture_output=True);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(img)],check=True,capture_output=True)
 dest=Path('/private/tmp/awai152-wp04-no-repeat.macho');
 if dest.exists():raise RuntimeError('output exists')
 shutil.copyfile(img,dest);dest.chmod(0o700);print('source',hashlib.sha256(src.encode()).hexdigest(),'emitter',sha(em),'watcher',sha(dest),flush=True)
