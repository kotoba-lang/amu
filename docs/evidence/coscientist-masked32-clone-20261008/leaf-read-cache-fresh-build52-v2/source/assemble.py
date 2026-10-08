"""Fresh bounded in-process archive assembly, gated independently; zero children."""
from common import *
import tarfile,io,gzip,sys
def main():
 need(len(sys.argv)==2,'assembly GO');gp=Path(sys.argv[1]);g=authorize('assembly',gp);gh=sha(gp)
 O=D/'assembly-outputs';need(not O.exists(),'fresh local assembly, no retry');O.mkdir()
 try:
  origins=load(D/'input-origins.json');need(len(origins)<=4096 and sum(r['bytes'] for r in origins.values())<=CAP,'whole logical evidence cap')
  payload={};roles={};originmap={}
  for i,(p,r) in enumerate(sorted(origins.items())):
   q=pin(dict(r,path=p));name='package/evidence/'+str(i).zfill(4);b=q.read_bytes()
   if len(b)<=67108864:payload[name]=b;originmap[p]=name
   else:
    chunks=[]
    for j,start in enumerate(range(0,len(b),67108864)):
     part=name+'.part'+str(j).zfill(3);pb=b[start:start+67108864];payload[part]=pb;chunks.append(dict(path=part,bytes=len(pb),sha256=H(pb)))
    originmap[p]=dict(chunks=chunks,bytes=r['bytes'],sha256=r['sha256'],role='lossless large historical evidence only; not a compiler operand')
  cp=Path(load(D/'preregistration.json')['canonicalCPackage'])
  for p in sorted(cp.rglob('*')):
   if p.is_file():
    need(not p.is_symlink() and str(p) in origins,'declared canonical C package inputs');payload['package/c-inputs/'+str(p.relative_to(cp))]=p.read_bytes()
  for name in ['build52.py','common.py','header.py','preregistration.json','source-pins.json','input-origins.json','root-functional285-acceptance-ref.json']:
   payload['package/'+name]=(D/name).read_bytes()
  # Source registry guards complete SOURCE on remote; package copies every pinned member.
  for name in load(D/'source-pins.json'):payload['package/'+name]=(D/name).read_bytes()
  acceptance=load(D/'root-functional285-acceptance-ref.json');payload['package/root-functional285-acceptance.json']=pin(acceptance,1048576).read_bytes()
  cs=load(D/'preregistration.json')['consumerSource'];payload['package/sources/timing-host-telemetry.c']=pin(cs).read_bytes()
  payload['package/origin-map.json']=json.dumps(originmap,indent=2).encode()+b'\n'
  payload['package/assembly-go.json']=gp.read_bytes()
  for i,r in enumerate(g['sourceReviews']):payload['package/assembly-review'+str(i)+'.json']=pin(r,1048576).read_bytes()
  manifest=dict(schema='LC_REGULAR_PACKAGE/v2',remoteRoot=str(ROOT),sourcePinsSHA256=g['sourcePinsSHA256'],members=[dict(path=n,bytes=len(b),sha256=H(b)) for n,b in sorted(payload.items())])
  payload['package/manifest.json']=json.dumps(manifest,indent=2).encode()+b'\n'
  need(len(payload)<=49152 and sum(map(len,payload.values()))<=536870912 and all(len(b)<=67108864 for b in payload.values()),'archive expanded/member/file caps')
  need(sum(512+((len(b)+511)//512)*512 for b in payload.values())+10240<=553648128,'manual USTAR framing cap')
  archive=O/'package.tgz'
  with archive.open('xb') as f,gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z,tarfile.open(mode='w|',fileobj=z,format=tarfile.USTAR_FORMAT) as tf:
   for n,b in sorted(payload.items()):
    t=tarfile.TarInfo(n);t.size=len(b);t.mode=0o444;t.mtime=0;t.uid=t.gid=0;t.uname=t.gname='';tf.addfile(t,io.BytesIO(b))
  save(O/'manifest.json',manifest)
  need(archive.stat().st_size<=268435456,'compressed cap')
  need(sha(gp)==gh and sourceguard()==g['sourcePinsSHA256'],'GO/source stable after assembly')
  for p,r in origins.items():pin(dict(r,path=p))
  save(O/'report.json',dict(status='PASS_ASSEMBLY_ONLY',archive=ref(archive),manifest=ref(O/'manifest.json'),logicalOrigins=len(origins),logicalBytes=sum(r['bytes'] for r in origins.values()),regularMembers=len(payload),expandedBytes=sum(map(len,payload.values())),sourcePinsSHA256=g['sourcePinsSHA256'],rootFunctional285AcceptanceSHA256=acceptance['sha256'],children=0,compilerCalls=0,nativeCalls=0))
 except BaseException as ex:save(O/'failure.json',dict(exception=repr(ex),noRetry=True));raise
 finally:save(O/'terminal.json',dict(children=0,allClosed=True,failure=(O/'failure.json').exists()))
if __name__=='__main__':main()
