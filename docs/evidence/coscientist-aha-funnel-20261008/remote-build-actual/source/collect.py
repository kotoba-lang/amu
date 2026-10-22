import sys,gzip,io,tarfile
from pathlib import Path,PurePosixPath
D=Path(__file__).resolve().parent
exec(compile((D/'local-common.py').read_bytes(),str(D/'local-common.py'),'exec'),globals())
exec(compile((D/'result-contract.py').read_bytes(),str(D/'result-contract.py'),'exec'),globals())
def main():
 assert len(sys.argv)==2;gp=Path(sys.argv[1]);gh=H(gp.read_bytes());g=guard(gp,'collect-build');assert g['maximumTransportProcesses']==2
 l=Ledger(D/'collect-outputs',2)
 try:
  o,e=l.call(remote('remote-seal.py'),180);assert not e and len(o)<=1048576;s=json.loads(o)
  assert s['status']=='SEALED_REGULAR_RUNNER_BUILD_RESULTS_ONLY' and s['guests']==0 and s['timing'] is False and 1<=s['members']<=256 and 0<s['archiveBytes']<=67108864 and 0<s['expandedBytes']<=134217728
  save(l.O/'seal-receipt.json',s);assert H(gp.read_bytes())==gh;guard(gp,'collect-build')
  a=l.O/'result.tgz';l.call(['scp',*OPTS,HOST+':'+R+'/runner-build-sealed/result.tgz',str(a)],180)
  assert a.is_file() and not a.is_symlink() and a.stat().st_size==s['archiveBytes'] and H(a.read_bytes())==s['archiveSHA256']
  with gzip.open(a,'rb') as f:raw=f.read(134217728+256*1024+10241)
  assert len(raw)<=134217728+256*1024+10240
  content=parse_ustar(raw)
  inv=content.pop('inventory.json');assert len(inv)<=1048576 and H(inv)==s['inventorySHA256'];rows=json.loads(inv)['members'];assert len(rows)==s['members'] and len(rows)==len(content) and len({r['name'] for r in rows})==len(rows)
  total=0
  for r in rows:
   assert set(r)=={'name','bytes','sha256'} and r['name'] in content;b=content[r['name']];assert len(b)==r['bytes'] and H(b)==r['sha256'];total+=len(b)
  assert total==s['expandedBytes'] and total<=134217728
  go=json.loads(content['remote-build-go.json']);assert go==read(D/'remote-build-go-proposal.json')
  t=validate_result(content);assert t==s['buildTerminal']
  O=l.O/'collected';assert not O.exists();O.mkdir()
  for n,b in content.items():
   p=O/n;p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb') as f:f.write(b)
   p.chmod(0o444)
  (O/'inventory.json').write_bytes(inv);assert H(gp.read_bytes())==gh;guard(gp,'collect-build')
  save(l.O/'report.json',{'status':'PASS_SEALED_RAW_COLLECTION_ONLY_NOT_BUILD_OR_FUNCTIONAL_CERTIFICATION','calls':2,'archiveSHA256':s['archiveSHA256'],'members':len(rows),'buildFailurePreserved':t['failure'],'guests':0,'timing':False})
 except BaseException as e:save(l.O/'failure.json',{'error':repr(e),'noRetry':True});raise
 finally:l.terminal()
if __name__=='__main__':main()
