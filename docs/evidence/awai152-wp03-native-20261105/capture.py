import importlib.util,json,os,resource,select,signal,struct,subprocess,sys,tempfile,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(3,4));repo=Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute');p=repo/'scripts/seed/check-macos-watch-helper.py';s=importlib.util.spec_from_file_location('h',p);h=importlib.util.module_from_spec(s);s.loader.exec_module(h);image=Path('/private/tmp/awai152-wp03-watch.macho');records=[]
with tempfile.TemporaryDirectory(prefix='awai152-wp03-capture-',dir='/private/tmp') as d:
 for mode in ('zero','seven','signal'):
  code="import os,sys; print('READY',flush=True); os.read(0,1); sys.exit("+('7' if mode=='seven' else '0')+")"
  child=subprocess.Popen([sys.executable,'-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);watch=None;reaped=False
  try:
   if not select.select([child.stdout],[],[],4)[0] or child.stdout.readline()!=b'READY\n':raise RuntimeError('child ready')
   sec,usec=h.identity(child.pid);req=struct.pack('<4sIQQII',b'WP03',child.pid,sec,usec,12345,4);watch=h.launch_watcher(image,Path(d),req)
   ready=b''
   while len(ready)<40:
    if not select.select([watch.stdout],[],[],4)[0]:raise TimeoutError('watch ready')
    part=os.read(watch.stdout.fileno(),40-len(ready))
    if not part:raise RuntimeError('EOF')
    ready+=part
   if ready!=b'WR01\0\0\0\0'+req:raise RuntimeError('bad ready')
   if mode=='signal':os.kill(child.pid,signal.SIGKILL)
   else:child.stdin.write(b'x');child.stdin.flush()
   out,err=watch.communicate(timeout=5);pid,status=os.waitpid(child.pid,0);reaped=True
   if pid!=child.pid or watch.returncode or err or out!=b'WS01'+struct.pack('<I',status)+req:raise RuntimeError('bad final')
   records.append({'request':list(req),'ready':list(ready),'frame':list(out),'status':status});print(mode,status,flush=True)
  finally:
   if watch and watch.poll() is None:watch.kill();watch.wait(timeout=3)
   if not reaped:
    try:child.kill();child.wait(timeout=3)
    except ProcessLookupError:pass
Path('/private/tmp/awai152-wp03-records.json').write_text(json.dumps(records))
