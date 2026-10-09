from pathlib import Path
import json,hashlib,re,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-leaf-straight-read-cache-full19-selfbuild40-plan-v1-native-controls';O=D/'run-outputs';A=Path(__file__).resolve().parent;G=W/'vector-leaf-straight-read-cache-full19-selfbuild40-go-v1-root/root-go.json';H=lambda b:hashlib.sha256(b).hexdigest();J=lambda p:json.loads(Path(p).read_bytes());pins={}
def read(p,v=None):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();z={'bytes':len(b),'sha256':H(b)}
 if v:assert z=={k:v[k]for k in ['bytes','sha256']}
 pins[str(p)]=z;return b
def cont(p,v):
 b=read(p,v);head,payload=b.split(b'\n\n',1);ls=head.decode('ascii').splitlines();assert ls[0]==f'KSEED1 {len(payload)} {len(ls)-1}';ex=[]
 for s in ls[1:]:
  m=re.fullmatch(r'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',s);assert m;n,o,a=m.groups();o=int(o);a=int(a);assert o%4==0 and o+4<=len(payload);ex.append([n,o,a])
 assert len(set(x[0]for x in ex))==len(ex);return payload,ex
pr=J(D/'preregistration.json');g=json.loads(read(G));assert pins[str(G)]['sha256']=='dc0420ac00e471b194ba1e30575bef69a6fd3290ff3dbb33bae0a2a6a0a6b340';ip=J(D/'input-pins.json');sp=J(D/'source-pins.json')
for p,v in ip.items():read(p,v)
for n,v in sp.items():read(D/n,v)
for n,key in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256'),('input-pins.json','inputPinsSHA256')]:assert H(read(D/n))==g[key]
for v in g['sourceReviews']:
 q=json.loads(read(v['path'],v));assert q['status']=='PASS_SOURCE_ONLY_LC_FULL19_SELFBUILD40'and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
report=J(O/'report.json');terminal=J(O/'terminal.json');rows=J(O/'attempts.json');images=J(O/'images.json');gens=J(O/'generations.json');env=J(O/'effective-environment.json');assert terminal=={'loaderCalls':40,'allChildrenClosed':True,'failure':False} and len(rows)==40
assert report['images']==images and report['generations']==gens and report['closedLoaderCalls']==40 and report['status']=='COMPLETE_LC_ORIGINAL19_COMPILATION_G1_G2_G3_FIXEDPOINT_ONLY';assert report['sourcePinsSHA256']==g['sourcePinsSHA256']and report['rootGOSHA256']==pins[str(G)]['sha256']
expected=[]
for e in pr['entries']:
 n=e['workload'];image=next(x for x in images if x['workload']==n);assert image['retained']==('retained'in e);payload,exports=cont(image['container']['path'],image['container']);assert payload==read(image['native']['path'],image['native'])and exports==image['exports'] and[e['symbol'],image['offset'],1]in exports
 if 'retained'in e:assert image['container']==e['retained']['container']and image['native']==e['retained']['native']
 else:
  assert read(O/(n+'.kotoba'))==read(e['source']['path'],e['source']);expected.extend([(n+'-compile',pr['producer'],['compile',str(O/(n+'.kotoba')),'--target','aarch64-macos','--output',image['container']['path']],None),(n+'-extract',pr['producer'],['extract-native',image['container']['path'],'--symbol',e['symbol'],'--output',image['native']['path']],image['offset'])])
assert read(O/'unity-lc-on.kotoba')==read(pr['parentSource'],ip[pr['parentSource']]);producer=pr['producer'];previous=None
for i,z in enumerate(gens,1):
 assert z['generation']==i;payload,exports=cont(z['container']['path'],z['container']);assert exports==[['main',0,0]]and payload==read(z['native']['path'],z['native'])and z['offset']==0
 expected.extend([('G'+str(i)+'-compile',producer,['compile',str(O/'unity-lc-on.kotoba'),'--target','aarch64-macos','--output',z['container']['path']],None),('G'+str(i)+'-extract',producer,['extract-native',z['container']['path'],'--symbol','main','--output',z['native']['path']],0)])
 if previous:assert read(previous['container']['path'])==read(z['container']['path'])and read(previous['native']['path'])==payload
 else:
  old=read(pr['producer']);assert z['G0ToG1NativeEquality']==(old==payload)and z['G0ToG1EqualityRequired']is False;first=next((k for k,(a,b)in enumerate(zip(old,payload))if a!=b),None if len(old)==len(payload)else min(len(old),len(payload)));assert first==z['G0ToG1FirstDifferentByte'];assert z['G0ToG1ContainerEquality']==(read(z['G0Container']['path'],z['G0Container'])==read(z['container']['path']))
 previous=z;producer=z['native']['path']
fields=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'];rx=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in fields)+'}\n').encode())
assert len(expected)==40
for i,(r,(label,producer,args,offset))in enumerate(zip(rows,expected),1):
 assert r['index']==i and r['label']==label and r['argv']==[pr['loader'],producer,'0','0','aarch64','35,37,38,39','--',*args]and r['effectiveEnvironment']==env;assert r['state']=='terminal'and r['reaped']is True and r['spawned']is True and r['returncode']==0 and r['error']is None and r['terminationReason']is None and r['cleanupExceptions']==[]
 out=read(O/(label+'.stdout'),r['stdout']);err=read(O/(label+'.stderr'),r['stderr']);assert b':ok true'in out and b':ok false'not in out;m=rx.fullmatch(err);assert m;u=dict(zip(fields,map(int,m.groups())));assert all(0<=v<2**64 for v in u.values())and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items'];assert r['counterObservation']=={'status':'valid','values':u,'entireStderrIsCounterLine':True}
 if offset is not None:assert [int(x)for x in re.findall(rb':offset ([0-9]+)\b',out)]==[offset]
assert env['KEXE_FUEL']=='off'and env['KEXE_CAP_RESOURCES_35']==str(O)and env['KEXE_ARENA_USE']=='1'
for folder in [O,G.parent]:
 for p in sorted(folder.rglob('*')):
  if p.is_file():read(p)
for p,v in list(pins.items()):assert H(Path(p).read_bytes())==v['sha256']
(A/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n');q={'status':'PASS_INDEPENDENT_ACTUAL_LC_FULL19_SELFBUILD40_IDENTITY_ONLY','sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':H((A/'input-pins.json').read_bytes()),'rootGOSHA256':pins[str(G)]['sha256'],'counts':{'closedLoaderCalls':40,'compileCalls':20,'extractCalls':20,'originalWorkloads':19,'newWorkloads':17,'retainedWorkloads':2,'joinedOriginal19CompileExtractCalls':38,'selfbuildCalls':6,'inputFiles':len(pins),'inputLogicalBytes':sum(v['bytes']for v in pins.values())},'checks':{'exactArgvEnvironmentRawSourceHashes':True,'allChildrenClosedNoRetry':True,'fullContainerNativeExportOffsetsExact':True,'readOnlyFullOriginalSourceCopies':True,'strict17ResourceCounters':True,'G1G2G3WholeContainerAndNativeByteFixedpoint':True},'images':images,'generations':gens,'G0G1WholeNativeEqual':gens[0]['G0ToG1NativeEquality'],'G0G1DifferenceAllowedByPreregistration':True,'G1G2G3WholeContainerAndNativeByteFixedpoint':True,'nativeCallsByAuditor':0,'participation':'Independently reviewed this SOURCE driver and earlier LC functional30 raw; did not author driver or execute children. Uses saved raw bytes only.','limitations':['Original19 images were emitted by G0; no presumed G3-generated original19 byte correspondence.','17 counters are source-bound capacity/copy observations, not simultaneous RSS peaks or timing.','No new workload guest execution, ABI/register canary, C performance, official score, universal resource proof or full selfhost-goal qualification.'],'runtimeWorkloadQualified':False,'performanceQualified':False,'officialScore':False,'fullSelfhostGoalAchieved':False}
(A/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({'reportSHA256':H((A/'report.json').read_bytes()),'inputPinsSHA256':q['inputPinsSHA256'],'counts':q['counts']}))
