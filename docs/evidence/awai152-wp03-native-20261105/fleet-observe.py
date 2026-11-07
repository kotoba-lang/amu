import hashlib,importlib.util,os,resource,subprocess,tempfile
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(3,4));root=Path(__file__).resolve().parent;image=root/'watch.macho';pin='df75083415f92ace3f37fffb69115256e184a98b08cbad766ca0dc57306274d7'
if hashlib.sha256(image.read_bytes()).hexdigest()!=pin:raise RuntimeError('pin mismatch')
subprocess.run(['/usr/bin/codesign','--verify','--strict',str(image)],check=True,capture_output=True,timeout=8)
s=importlib.util.spec_from_file_location('watch',root/'check-macos-watch-helper.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='awai152-wp03-observe-',dir='/private/tmp') as d:
 for mode in ('zero','seven','signal'):m.status_case(image,Path(d),mode)
 for mode in ('exec','fork'):m.transition_case(image,Path(d),mode,b'WP03')
