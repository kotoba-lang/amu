from pathlib import Path
import json,hashlib,re,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-leaf-straight-read-cache-g3-original19-compile38-plan-v1-native-controls';O=D/'run-outputs';A=Path(__file__).resolve().parent;G=W/'vector-leaf-straight-read-cache-g3-original19-compile38-go-v1-root/root-go.json';H=lambda b:hashlib.sha256(b).hexdigest();J=lambda p:json.loads(Path(p).read_bytes());pins={}
def read(p,v=None):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();z={'bytes':len(b),'sha256':H(b)}
 if v:assert z=={k:v[k]for k in ['bytes','sha256']}
 pins[str(p)]=z;return b
def cont(p,v):
 b=read(p,v);head,payload=b.split(b'\n\n',1);ls=head.decode('ascii').splitlines();assert ls[0]==f'KSEED1 {len(payload)} {len(ls)-1}';ex=[]
 for s in ls[1:]:
  m=re.fullmatch(r'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',s);assert m;n,o,a=m.groups();o=int(o);a=int(a);assert o%4==0 and o+4<=len(payload);ex.append([n,o,a])
 assert len(set(x[0]for x in ex))==len(ex);return payload,ex
pr=J(D/'preregistration.json');g=json.loads(read(G));assert pins[str(G)]['sha256']=='5a83413e37f84a3748240da72994d7aae6666286f367b1996b8b09f79917b1da';ip=J(D/'input-pins.json');sp=J(D/'source-pins.json')
for p,v in ip.items():read(p,v)
for n,v in sp.items():read(D/n,v)
for n,key in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256'),('input-pins.json','inputPinsSHA256')]:assert H(read(D/n))==g[key]
for v in g['sourceReviews']:
 q=json.loads(read(v['path'],v));assert q['status']=='PASS_SOURCE_ONLY_LC_G3_ORIGINAL19_COMPILE38'and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])
report=J(O/'report.json');terminal=J(O/'terminal.json');rows=J(O/'attempts.json');images=J(O/'images.json');env=J(O/'effective-environment.json');assert terminal=={'loaderCalls':38,'allChildrenClosed':True,'failure':False} and len(rows)==38
assert report['images']==images and report['closedLoaderCalls']==38 and report['status']=='COMPLETE_LC_G3_ORIGINAL19_COMPILE_EXTRACT38_WHOLE_G0_IDENTITY_ONLY';assert report['sourcePinsSHA256']==g['sourcePinsSHA256']and report['rootGOSHA256']==pins[str(G)]['sha256']
assert report['producer']['sha256']=='5f4f591a1eb3bb46d3042a3463805a5cfb0897b766ee2de4909088be3369e1af' and report['producer']['bytes']==966824 and report['producer']['path']==pr['producer'];read(pr['producer'],report['producer'])
expected=[]
for e,image in zip(pr['entries'],images):
 n=e['workload'];assert image['workload']==n and image['baseline']==e['baseline'];payload,exports=cont(image['container']['path'],image['container']);assert payload==read(image['native']['path'],image['native'])and exports==image['exports'] and[e['symbol'],image['offset'],1]in exports
 old=e['baseline'];assert read(image['container']['path'])==read(old['container']['path'],old['container']) and read(image['native']['path'])==read(old['native']['path'],old['native']) and image['exports']==old['exports']and image['offset']==old['offset'] and image['wholeG0ContainerNativeEqual']is True
 assert read(O/(n+'.kotoba'))==read(e['source']['path'],e['source']);expected.extend([(n+'-compile',pr['producer'],['compile',str(O/(n+'.kotoba')),'--target','aarch64-macos','--output',image['container']['path']],None),(n+'-extract',pr['producer'],['extract-native',image['container']['path'],'--symbol',e['symbol'],'--output',image['native']['path']],image['offset'])])
assert len(images)==19 and report['wholeOriginal19G3G0ContainerNativeExportOffsetEqual']is True
fields=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'];rx=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in fields)+'}\n').encode())
assert len(expected)==38
for i,(r,(label,producer,args,offset))in enumerate(zip(rows,expected),1):
 assert r['index']==i and r['label']==label and r['argv']==[pr['loader'],producer,'0','0','aarch64','35,37,38,39','--',*args]and r['effectiveEnvironment']==env;assert r['state']=='terminal'and r['reaped']is True and r['spawned']is True and r['returncode']==0 and r['error']is None and r['terminationReason']is None and r['cleanupExceptions']==[]
 out=read(O/(label+'.stdout'),r['stdout']);err=read(O/(label+'.stderr'),r['stderr']);assert b':ok true'in out and b':ok false'not in out;m=rx.fullmatch(err);assert m;u=dict(zip(fields,map(int,m.groups())));assert all(0<=v<2**64 for v in u.values())and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items'];assert r['counterObservation']=={'status':'valid','values':u,'entireStderrIsCounterLine':True}
 if offset is not None:assert [int(x)for x in re.findall(rb':offset ([0-9]+)\b',out)]==[offset]
assert env['KEXE_FUEL']=='off'and env['KEXE_CAP_RESOURCES_35']==str(O)and env['KEXE_ARENA_USE']=='1'
for folder in [O,G.parent]:
 for p in sorted(folder.rglob('*')):
  if p.is_file():read(p)
for p,v in list(pins.items()):assert H(Path(p).read_bytes())==v['sha256']
(A/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n');q={'status':'PASS_INDEPENDENT_ACTUAL_LC_G3_ORIGINAL19_COMPILE_EXTRACT38_IDENTITY_ONLY','sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':H((A/'input-pins.json').read_bytes()),'rootGOSHA256':pins[str(G)]['sha256'],'counts':{'closedLoaderCalls':38,'compileCalls':19,'extractCalls':19,'originalWorkloads':19,'retainedSkips':0,'inputFiles':len(pins),'inputLogicalBytes':sum(v['bytes']for v in pins.values())},'checks':{'exactArgvEnvironmentRawSourceHashes':True,'allChildrenClosedNoRetry':True,'fullContainerNativeExportOffsetsExact':True,'readOnlyFullOriginalSourceCopies':True,'strict17ResourceCounters':True,'all19G3G0WholeContainerNativeExportOffsetIdentity':True},'producer':report['producer'],'images':images,'wholeOriginal19G3G0ContainerNativeExportOffsetEqual':True,'nativeCallsByAuditor':0,'participation':'Reviewer authored prior actual40 saved-raw audit and functional255 SOURCE; did not author G3compile38 driver or source reviews and did not execute children. Saved raw bytes only.','limitations':['Whole19 byte correspondence supports reuse of finite G0 evidence for these exact G3 artifacts; no new workload execution occurred.','17 counters are source-bound capacity/copy observations, not simultaneous RSS peaks or timing.','No ABI/register canary, C performance, official score, universal resource proof or full selfhost-goal qualification.'],'runtimeWorkloadExecution':False,'performanceQualified':False,'officialScore':False,'fullSelfhostGoalAchieved':False}
(A/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({'reportSHA256':H((A/'report.json').read_bytes()),'inputPinsSHA256':q['inputPinsSHA256'],'counts':q['counts']}))
