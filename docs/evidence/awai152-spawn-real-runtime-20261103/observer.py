import json, os, pathlib, signal, subprocess, time
base=pathlib.Path('/private/tmp/awai152-kernel-check')
def stat(pid):
 try:
  p=pathlib.Path('/proc')/str(pid); s=(p/'stat').read_text().split(); return {'pid':pid,'parent':int(s[3]),'start':s[21],'state':s[2],'cmd':(p/'cmdline').read_bytes().split(b'\0')}
 except (OSError,IndexError,ValueError): return None
def live(p):
 n=stat(p['pid']); return bool(n and n['start']==p['start'] and n['state'] not in 'ZX')
def test(name, expected):
 env=dict(os.environ,KEXE_ALLOW='20,35,37,38',KEXE_CAP_RESOURCES_20='/usr/bin/sleep',KEXE_CAP_RESOURCES_35=str(base))
 guest=subprocess.Popen([str(base/(name+'.elf'))],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 helper=child=None
 try:
  end=time.monotonic()+4
  while time.monotonic()<end:
   if guest.poll() is not None: raise RuntimeError('guest exited: '+str(guest.stderr.read(500)))
   procs=[stat(int(p.name)) for p in pathlib.Path('/proc').iterdir() if p.name.isdigit()]
   helpers=[p for p in procs if p and p['parent']==guest.pid]
   kids=[p for p in procs if p and p['cmd'][:2]==[b'/usr/bin/sleep',b'6'] and any(p['parent']==h['pid'] for h in helpers)]
   if kids: child=kids[0]; helper=next(h for h in helpers if h['pid']==child['parent']); break
   time.sleep(.02)
  if child is None: raise RuntimeError('guest/helper/sleep tree not observed')
  guest.kill(); guest.wait(timeout=3); time.sleep(.5)
  result={'case':name,'guestExit':guest.returncode,'helperAlive':live(helper),'directChildAlive':live(child),'delaySeconds':.5}
  print(json.dumps(result),flush=True)
  if result['directChildAlive']!=expected: raise RuntimeError('unexpected direct-child state')
 finally:
  if guest.poll() is None: guest.kill(); guest.wait(timeout=3)
  for p in (child,helper):
   if p and live(p):
    try: os.kill(p['pid'],signal.SIGKILL)
    except ProcessLookupError: pass
test('baseline',True)
test('candidate',False)
