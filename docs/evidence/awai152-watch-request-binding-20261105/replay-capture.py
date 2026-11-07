import hashlib,importlib.util,os,select,struct,subprocess,tempfile,time,resource
resource.setrlimit(resource.RLIMIT_CPU,(3,4))
from pathlib import Path
repo=Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute')
spec=importlib.util.spec_from_file_location('watch',repo/'scripts/seed/check-macos-watch-helper.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
image=Path('/private/tmp/awai152-heartbeat-r8ld4r9s/run/watch.macho')
assert hashlib.sha256(image.read_bytes()).hexdigest()=='1fdff12c551e847948096c96bf4037d91aee540310ca9947f43c9dda20d3869b'
subprocess.run(['/usr/bin/codesign','--verify','--strict',str(image)],check=True,capture_output=True,timeout=10)
with tempfile.TemporaryDirectory(prefix='awai152-clock-replay-',dir='/private/tmp') as td:
 child=subprocess.Popen(['/bin/sleep','4']);watcher=None
 try:
  sec,usec=w.identity(child.pid);req=struct.pack('<4sIQQII',b'WP02',child.pid,sec,usec,12345,1)
  start=time.monotonic_ns()//1000000;watcher=w.launch_watcher(image,Path(td),req)
  events=[];buffer=b'';terminal=None;end=time.monotonic()+8
  while time.monotonic()<end:
   readable,_,_=select.select([watcher.stdout],[],[],0.25)
   now=time.monotonic_ns()//1000000
   if not readable:
    if watcher.poll() is not None: raise RuntimeError('watcher exited without EOF')
    events.append(('poll',b'',now));continue
   chunk=os.read(watcher.stdout.fileno(),4096)
   if not chunk: break
   buffer+=chunk
   while len(buffer)>=40:
    frame,buffer=buffer[:40],buffer[40:]
    typ={b'WR01':'ready',b'WH01':'heartbeat',b'WO01':'exit'}.get(frame[:4])
    if typ is None or frame[8:]!=req:raise RuntimeError('bad frame')
    if typ=='exit':terminal=(typ,frame,now)
    elif terminal:raise RuntimeError('frame after exit')
    else:events.append((typ,frame,now))
  else:raise TimeoutError('watcher EOF')
  rc=watcher.wait(timeout=2);err=watcher.stderr.read();childrc=child.wait(timeout=2)
  if buffer or not terminal or rc!=0 or childrc!=0 or err:raise RuntimeError((len(buffer),terminal,rc,childrc,err))
  events.append(terminal)
  def vec(b):return '['+' '.join(map(str,b))+']'
  source=(repo/'seed/darwin-watch-reply.kotoba').read_text();decl='(ns amu.darwin-watch-reply (:export [darwin-watch-ready? darwin-watch-heartbeat? darwin-watch-exit-class darwin-watch-monitor-start darwin-watch-monitor-step darwin-watch-reply-class]))';assert source.count(decl)==1
  bindings=['req '+vec(req),f's0 (darwin-watch-monitor-start req {start} 2500)'];checks=[]
  for i,(kind,frame,now) in enumerate(events,1):
   bindings.append(f's{i} (darwin-watch-monitor-step req s{i-1} "{kind}" {vec(frame)} {0 if kind=="exit" else -1} {"true" if kind=="exit" else "false"} {now} {"false" if kind=="exit" else "true"})')
   checks.append(f'(= (vector-at s{i} 0) {2 if kind=="exit" else 1 if kind!="poll" or any(e[0]=="ready" for e in events[:i]) else 0})')
  main='(defn main [] :i64 (let ['+' '.join(bindings)+'] (if (and '+' '.join(checks)+') 0 1)))'
  code='(ns watcher-replay (:export [main]))\n'+source.replace(decl,'')+'\n'+main+'\n'
  Path('/private/tmp/awai152-bound-watch-replay.kotoba').write_text(code)
  print('captured',len(events),'events',sum(e[0]=='heartbeat' for e in events),'heartbeats',sum(e[0]=='poll' for e in events),'polls','elapsed-ms',events[-1][2]-start,'sha256',hashlib.sha256(code.encode()).hexdigest())
 finally:
  if watcher and watcher.poll() is None:watcher.kill();watcher.wait()
  if child.poll() is None:child.kill();child.wait()
