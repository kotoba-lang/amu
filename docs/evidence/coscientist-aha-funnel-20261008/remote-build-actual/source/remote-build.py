from pathlib import Path
import json,hashlib,sys,os
R=Path('/Users/zebulun/github/workspaces/codex/vector-aha-funnel-remote-runner-v1-root')
H=lambda b:hashlib.sha256(b).hexdigest()
def main():
 assert Path.home()==Path('/Users/zebulun') and all(not p.is_symlink() for p in [R,*R.parents])
 raw=sys.stdin.buffer.read(1048577);assert len(raw)<=1048576
 q=json.loads(raw);assert set(q)=={'go','inventory'}
 inv=q['inventory'];assert set(inv)=={'members'} and len(inv['members'])==285
 assert H((json.dumps(inv,indent=2)+'\n').encode())=='e98d0cc8e6ef00d3533be335a5abbc80b1b34a86a40b30feb2769ed237ed4afc'
 def guard():
  seen=set()
  for e in inv['members']:
   n=e['name'];p=R/n;assert n not in seen and not Path(n).is_absolute() and '..' not in Path(n).parts;seen.add(n)
   assert all(not z.is_symlink() for z in [p,*p.parents]) and p.is_file() and p.stat().st_size==e['bytes'] and H(p.read_bytes())==e['sha256']
  assert len(json.loads((R/'plan/relocation-input-manifest.json').read_text())['members'])==470
 guard();g=q['go'];assert g['outputRoot']==str(R/'runner-output') and g['stage']=='build'
 assert g['maximumTotalProcesses']==33 and g['maximumBuilds']==19 and g['maximumIdentityQueries']==14 and g['maximumClangInvocations']==23
 assert not (R/'runner-output').exists()
 p=R/'remote-build-go.json';assert not p.exists()
 with p.open('xb') as f:f.write((json.dumps(g,indent=2)+'\n').encode())
 p.chmod(0o444);os.environ.clear();os.environ.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/zebulun',LANG='C',LC_ALL='C',TZ='UTC',PYTHONDONTWRITEBYTECODE='1')
 driver=R/'plan/build19.py';sys.argv=[str(driver),str(p)]
 try:exec(compile(driver.read_bytes(),str(driver),'exec'),{'__name__':'__main__','__file__':str(driver)})
 finally:guard()
if __name__=='__main__':main()
