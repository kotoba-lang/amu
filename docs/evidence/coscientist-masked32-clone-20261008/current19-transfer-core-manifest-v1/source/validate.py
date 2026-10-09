"""Read-only file/core manifest checks, no archive/transfer/build API."""
from pathlib import Path
import json,hashlib,stat,copy,re
D=Path(__file__).resolve().parent
W=D.parent
OFF=W/'tc-current7618-off18-compile36-actual-review-independent-20261009/report.json';ON=W/'tc-hft-compose511-bound-hoist-g4-original19-compile38-actual-review-independent-20261009-dense/report.json';CP=W/'tc-original19-saved-c95-semantic-oracle-independent-20261009/provenance.json'
def validate(m):
 assert m['exactRegularFiles']==len(m['files'])==156 and m['exactLogicalBytes']==sum(z['bytes']for z in m['files'])==4299692
 assert len(m['entries'])==19 and sum(len(z['profiles'])for z in m['entries'])==95 and m['archiveCreated']is False and m['transferPerformed']is False
 mapped={}
 for f in m['files']:
  dest=Path(f['relativePath']);assert not dest.is_absolute()and '..'not in dest.parts and f['relativePath']not in mapped;mapped[f['relativePath']]=f
  src=Path(f['source']);s=src.lstat();assert stat.S_ISREG(s.st_mode)and not src.is_symlink();b=src.read_bytes();t=src.lstat();assert(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns);assert len(b)==f['bytes']and hashlib.sha256(b).hexdigest()==f['sha256']
 off=json.loads(OFF.read_text())['joinedOriginal19Images'];on=json.loads(ON.read_text())['original19Images'];provenance=json.loads(CP.read_text())['cInputSourceManifestReceipts'];cmap={z['path'][len('package/c-inputs/'):]:z for z in provenance if z['path'].startswith('package/c-inputs/')}
 for f in m['files']:
  if f['role']=='original-C-owned-source-or-header':assert f['relativePath']in cmap and f['bytes']==cmap[f['relativePath']]['bytes']and f['sha256']==cmap[f['relativePath']]['sha256']
 for e in m['entries']:
  for arm,bank in [('OFF',off),('ON',on)]:
   im=next(z for z in bank if z['workload']==e['workload']);a=e['arms'][arm];assert a['offset']==(im['offset']if arm=='OFF'else im['selectedExport'][1])and any(x[0]==e['symbol']and x[1]==a['offset']and x[2]==1 for x in im['exports'])and e['profiles']==im['iterations']
   for k in ['native','container']:
    f=mapped[a[k]];assert f['source']==im[k]['path']and f['sha256']==im[k]['sha256']and f['bytes']==im[k]['bytes']
   raw=Path(im['container']['path']).read_bytes();native=Path(im['native']['path']).read_bytes();assert raw.endswith(native)and len(native)>a['offset']>=0
  assert e['C']['freshArtifactAvailable']is False and e['C']['futureFreshArtifact']=='inputs/'+e['workload']+'/C.dylib'
 assert all(not x['relativePath'].endswith(('.dylib','.a','.so'))for x in m['files'])
 assert not any('SDKs' in x['source']or '/LC.bin' in x['relativePath']or '/LC.kseed'in x['relativePath']for x in m['files'])
 return True
if __name__=='__main__':
 m=json.loads((D/'manifest.json').read_text());assert validate(m);neg=[]
 def refuse(name,fn):
  try:fn()
  except(AssertionError,KeyError,ValueError,FileNotFoundError):neg.append(name)
  else:raise AssertionError('mutant admitted:'+name)
 for name,change in [('stale-count',lambda z:z.update(exactRegularFiles=155)),('wrong-bytes',lambda z:z.update(exactLogicalBytes=0)),('traversal',lambda z:z['files'][0].update(relativePath='../outside')),('stale-native-hash',lambda z:next(f for f in z['files']if f['role']=='current-ON-native-whole').update(sha256='0'*64)),('fake-C-artifact',lambda z:z['entries'][0]['C'].update(freshArtifactAvailable=True)),('wrong-profile',lambda z:z['entries'][0]['profiles'].__setitem__(0,42)),('wrong-export',lambda z:z['entries'][0]['arms']['ON'].update(offset=0)),('duplicate-map',lambda z:z['files'][1].update(relativePath=z['files'][0]['relativePath']))]:
  z=copy.deepcopy(m);change(z);refuse(name,lambda:validate(z))
 print(json.dumps({'status':'PASS_PURE_SOURCE_CURRENT19_PACKET_CORE_ONLY','files':156,'logicalBytes':4299692,'CSourceFilesMatchedSavedC95Provenance':53,'refusals':neg,'archiveTransferBuildOperations':0},indent=2))
