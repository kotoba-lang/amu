from pathlib import Path
import hashlib,json,tarfile,gzip,io
R=Path('/Users/zebulun/github/workspaces/codex/vector-aha-funnel-remote-runner-v1-root')
H=lambda b:hashlib.sha256(b).hexdigest()
def main():
 assert Path.home()==Path('/Users/zebulun') and all(not p.is_symlink() for p in [R,*R.parents])
 O=R/'runner-output';B=O/'functional171';assert B.is_dir() and not B.is_symlink()
 rows=[];content=[];total=0
 for p in sorted(B.rglob('*')):
  assert not p.is_symlink()
  if p.is_dir():
   n=p.relative_to(O).as_posix();assert any(a.startswith(n+'/') for a in ALLOWED);continue
  assert p.is_file();n=p.relative_to(O).as_posix();assert n in ALLOWED;b=p.read_bytes();assert 0<=len(b)<=16777216
  total+=len(b);assert total<=134217728 and len(rows)<349
  rows.append({'name':n,'bytes':len(b),'sha256':H(b)});content.append((n,b))
 # Include exact launched GO; no tmp/toolchain tree, package duplicate, guest execution.
 p=R/'remote-functional-go.json';assert p.is_file() and not p.is_symlink();b=p.read_bytes();assert len(b)<=1048576
 total+=len(b);assert total<=134217728
 rows.append({'name':'remote-functional-go.json','bytes':len(b),'sha256':H(b)});content.append(('remote-functional-go.json',b))
 term=validate_result(dict(content))
 inv=(json.dumps({'members':rows},indent=2)+'\n').encode();assert len(inv)<=1048576
 S=R/'functional171-sealed';assert not S.exists();S.mkdir()
 with (S/'result.tgz').open('xb') as out:
  with gzip.GzipFile(fileobj=out,mode='wb',mtime=0,filename='') as gz:
   with tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as t:
    for n,b in [('inventory.json',inv),*content]:
     z=tarfile.TarInfo(n);z.size=len(b);z.mode=0o444;z.mtime=0;t.addfile(z,io.BytesIO(b))
 a=S/'result.tgz';assert a.stat().st_size<=67108864
 # Recheck every source byte after archive creation.
 for e in rows:
  p=R/e['name'] if e['name']=='remote-functional-go.json' else O/e['name']
  assert p.stat().st_size==e['bytes'] and H(p.read_bytes())==e['sha256']
 a.chmod(0o444)
 print(json.dumps({'status':'SEALED_REGULAR_FUNCTIONAL171_RESULTS_ONLY','archiveSHA256':H(a.read_bytes()),'archiveBytes':a.stat().st_size,'inventorySHA256':H(inv),'members':len(rows),'expandedBytes':total,'functionalTerminal':term,'guests':0,'timing':False}))
if __name__=='__main__':main()
