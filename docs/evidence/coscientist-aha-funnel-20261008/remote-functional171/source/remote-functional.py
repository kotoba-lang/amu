from pathlib import Path
import json,hashlib,sys,os
R=Path('/Users/zebulun/github/workspaces/codex/vector-aha-funnel-remote-runner-v1-root')
H=lambda b:hashlib.sha256(b).hexdigest()
def main():
 assert Path.home()==Path('/Users/zebulun') and all(not p.is_symlink() for p in [R,*R.parents])
 raw=sys.stdin.buffer.read(1048577);assert len(raw)<=1048576;q=json.loads(raw);assert set(q)=={'go','review','acceptance','inventory'}
 inv=q['inventory'];assert len(inv['members'])==285 and H((json.dumps(inv,indent=2)+'\n').encode())=='e98d0cc8e6ef00d3533be335a5abbc80b1b34a86a40b30feb2769ed237ed4afc'
 def guard():
  for r in inv['members']:
   p=R/r['name'];assert p.is_file() and all(not z.is_symlink() for z in [p,*p.parents]) and p.stat().st_size==r['bytes'] and H(p.read_bytes())==r['sha256']
 guard();g=q['go'];assert g['stage']=='functional' and g['outputRoot']==str(R/'runner-output') and g['maximumFunctionalCalls']==171 and not (R/'runner-output/functional171').exists()
 for field,key,name in [('buildIndependentReview','review','actual-build-independent-review.json'),('buildReviewAcceptance','acceptance','root-build-review-acceptance.json')]:
  e=g[field];p=R/name;b=q[key].encode();assert e=={'path':str(p),'bytes':len(b),'sha256':H(b)} and not p.exists()
  with p.open('xb') as f:f.write(b)
  p.chmod(0o444)
 p=R/'remote-functional-go.json';assert not p.exists()
 with p.open('xb') as f:f.write((json.dumps(g,indent=2)+'\n').encode())
 p.chmod(0o444);os.environ.clear();os.environ.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/zebulun',LANG='C',LC_ALL='C',TZ='UTC',PYTHONDONTWRITEBYTECODE='1')
 driver=R/'plan/functional171.py';sys.argv=[str(driver),str(p)]
 try:exec(compile(driver.read_bytes(),str(driver),'exec'),{'__name__':'__main__','__file__':str(driver)})
 finally:guard()
if __name__=='__main__':main()
