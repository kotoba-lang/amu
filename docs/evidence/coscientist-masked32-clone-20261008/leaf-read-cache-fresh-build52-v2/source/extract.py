"""Finite strict extractor derived from reviewed regular-package extractor."""
import os,sys,json,hashlib,tarfile,stat,signal,gzip,io
from pathlib import Path,PurePosixPath
ROOT=Path('/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-v2-root');STAGE=Path(str(ROOT)+'-stage')
H=lambda b:hashlib.sha256(b).hexdigest()
def main():
 assert len(sys.argv)==2 and Path.home()==Path('/Users/zebulun')
 gp=Path(sys.argv[1]);assert gp==STAGE/'transfer-go.json' and gp.is_file() and not gp.is_symlink() and gp.stat().st_size<=1048576;g=json.loads(gp.read_text())
 assert g['phase']=='transfer' and g['authorized'] is True and g['maximumChildren']==3 and g['remoteRoot']==str(ROOT) and g['destination']=='zebulun@100.66.28.79' and g['functionalAuthorized'] is False and g['timingAuthorized'] is False
 assert H(Path(__file__).read_bytes())==g['extractorSHA256'] and not ROOT.exists()
 assert all(not p.is_symlink() for p in ROOT.parents if p.exists())
 signal.alarm(240)
 a=STAGE/'package.tgz';assert stat.S_ISREG(a.lstat().st_mode) and not a.is_symlink() and a.stat().st_size==g['archive']['bytes']<=268435456 and H(a.read_bytes())==g['archive']['sha256']
 # Cap decompression before parsing any metadata. 528MiB manual USTAR ceiling.
 with gzip.open(a,'rb') as f:raw=f.read(553648129)
 assert len(raw)<=553648128
 payload={};total=0
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tf:
  for ti in tf:
   q=PurePosixPath(ti.name)
   assert ti.isfile() and not ti.pax_headers and not ti.issym() and not ti.islnk() and not ti.sparse and str(q)==ti.name and q.parts[0]=='package' and not q.is_absolute() and '..' not in q.parts and ti.name not in payload and len(payload)<49152 and 0<=ti.size<=67108864
   total+=ti.size;assert total<=536870912
   b=tf.extractfile(ti).read(67108865);assert len(b)==ti.size;payload[ti.name]=b
 assert H(payload['package/manifest.json'])==g['manifestBytesSHA256']
 m=json.loads(payload['package/manifest.json']);assert m['schema']=='LC_REGULAR_PACKAGE/v2' and m['remoteRoot']==str(ROOT) and m['sourcePinsSHA256']==g['sourcePinsSHA256']
 expected={z['path']:z for z in m['members']};assert len(expected)==len(m['members']) and set(payload)==set(expected)|{'package/manifest.json'}
 for n,z in expected.items():assert len(payload[n])==z['bytes'] and H(payload[n])==z['sha256']
 origins=json.loads(payload['package/input-origins.json']);originmap=json.loads(payload['package/origin-map.json']);assert set(origins)==set(originmap) and len(origins)<=4096 and sum(r['bytes'] for r in origins.values())<=469762048
 for p,r in origins.items():
  m=originmap[p]
  if isinstance(m,str):assert len(payload[m])==r['bytes'] and H(payload[m])==r['sha256']
  else:
   assert m['bytes']==r['bytes'] and m['sha256']==r['sha256'];hh=hashlib.sha256();count=0
   for part in m['chunks']:
    bb=payload[part['path']];assert len(bb)==part['bytes'] and H(bb)==part['sha256'];hh.update(bb);count+=len(bb)
   assert count==r['bytes'] and hh.hexdigest()==r['sha256']
 assert H(payload['package/root-functional285-acceptance.json'])==g['rootFunctional285AcceptanceSHA256']
 bank=json.loads(payload['package/source-pins.json']);assert H(payload['package/source-pins.json'])==g['sourcePinsSHA256']
 for n,r in bank.items():assert len(payload['package/'+n])==r['bytes'] and H(payload['package/'+n])==r['sha256']
 ROOT.mkdir()
 for n,b in payload.items():
  p=ROOT/n;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(b)
  p.chmod(0o444);assert H(p.read_bytes())==H(b)
 signal.alarm(0)
 receipt=dict(status='PASS_REMOTE_EXTRACT_ONLY',regularMembers=len(payload),expandedBytes=total,archiveSHA256=g['archive']['sha256'],manifestSHA256=H(payload['package/manifest.json']),sourcePinsSHA256=g['sourcePinsSHA256'],rootFunctional285AcceptanceSHA256=g['rootFunctional285AcceptanceSHA256'],compilerCalls=0,nativeCalls=0)
 (STAGE/'extract-terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
if __name__=='__main__':
 try:main()
 except BaseException as ex:
  if STAGE.exists():(STAGE/'extract-failure.json').write_text(json.dumps(dict(exception=repr(ex),noRetry=True))+'\n')
  raise
