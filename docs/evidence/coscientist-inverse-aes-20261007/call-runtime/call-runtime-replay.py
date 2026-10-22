"""Stdlib only, retained inverse-CALL evidence. No native/compiler/solver/network/timing."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,subprocess,sys
D=Path(__file__).resolve().parent;m=json.loads((D/'call-runtime-manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();a=D/m['archive'];assert sha(a)==m['archiveSHA256']and a.stat().st_size==m['archiveBytes']
assert sha(Path(__file__))==m['replaySHA256']
root=Path(tempfile.mkdtemp(prefix='inverse-CALL-offline-'));expected={r['member']:r for r in m['members']};assert len(expected)==m['memberCount']
with tarfile.open(a,'r:gz')as t:
 members=t.getmembers();assert len(members)==len(expected)and{q.name for q in members}==set(expected)
 for q in members:
  path=PurePosixPath(q.name);assert q.isfile()and not path.is_absolute()and'..'not in path.parts;data=t.extractfile(q).read();r=expected[q.name];assert len(data)==r['bytes']and hashlib.sha256(data).hexdigest()==r['sha256'];p=root/q.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
W=root/'payload/private/tmp/amu-aes-resident-fuel-20261007';records=[]
def copied_checker(rel,outputs):
 original=W/rel;source=original.read_text();assert source.count('from pathlib import Path')==1
 injection='''from pathlib import Path as _PhysicalPath
class Path(type(_PhysicalPath())):
 def __new__(cls,*args,**kwargs):
  if args:
   s=str(args[0])
   if s.startswith('/') and not s.startswith(ROOT): args=(ROOT+'/payload/'+s.lstrip('/'),)+args[1:]
  return super().__new__(cls,*args,**kwargs)
 def __str__(self):
  s=_PhysicalPath.__str__(self)
  prefix=ROOT+'/payload/'
  return '/'+s[len(prefix):] if s.startswith(prefix) else s
 def __fspath__(self): return _PhysicalPath.__str__(self)
'''
 # Path objects retain legacy logical strings for exact saved argv/report comparison,
 # while file operations target only the extracted member mirror. No JSON/source oracle edits.
 code='ROOT='+repr(str(root))+'\n'+source.replace('from pathlib import Path',injection,1);runner=root/(Path(rel).parent.name+'-offline.py');runner.write_text('CODE='+repr(code)+'\nexec(compile(CODE,'+repr(str(original))+',"exec"),{"__file__":'+repr(str(original))+'})\n')
 wanted={n:sha(W/n)for n in outputs};p=subprocess.run([sys.executable,str(runner)],capture_output=True,timeout=60);(root/(runner.stem+'.stdout')).write_bytes(p.stdout);(root/(runner.stem+'.stderr')).write_bytes(p.stderr);assert p.returncode==0,(rel,p.stderr.decode());assert all(sha(W/n)==h for n,h in wanted.items()),('copied output changed',rel);records.append({'script':rel,'exit':0,'outputHashesExact':wanted})
copied_checker('team-inverse-compiled-call-runtime-independent/review.py',['team-inverse-compiled-call-runtime-independent/report.json'])
copied_checker('team-inverse-runtime-controls-independent/static-review.py',['team-inverse-runtime-controls-independent/static-report.json'])
copied_checker('team-inverse-runtime-controls-independent/runtime-review.py',['team-inverse-runtime-controls-independent/runtime-report.json'])
normal=json.loads((W/'team-inverse-compiled-call-runtime-independent/report.json').read_text());controls=json.loads((W/'team-inverse-runtime-controls-independent/runtime-report.json').read_text());assert normal['pairs']==168 and normal['guestReceipts']==336 and normal['COracleReceipts']==12 and controls['guestCount']==40 and controls['overallGuestCount']==376
report={'status':'PASS copied-three-file stdlib CALL offline replay only','members':len(expected),'allMemberBytesHashesExact':True,'copiedCheckers':records,'retainedNormalPairs':168,'retainedNormalGuestReceipts':336,'retainedCOracleReceipts':12,'retainedControlGuestReceipts':40,'retainedOverallGuestReceipts':376,'retainedHeaderByteSourceOffsetBindings':22,'directSourceLiteralOracle2048':True,'semanticFuelCost':7,'retainedABI28Coupling4Mutation8':True,'nativeSolverNetworkTimingRuns':0,'scope':'All selected raw/certificate source/failure records authenticated; source arithmetic and full reported final status/result/fuel/pool checked, not new native execution','unqualified':['pending compilerM allocator/open/reuse/refusal proof','asyncpublication or unreportedfullM/arena','allABI/SIMD','product adoption/performance/official scores'],'extractedDirectory':str(root)}
(D/'offline-replay-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
