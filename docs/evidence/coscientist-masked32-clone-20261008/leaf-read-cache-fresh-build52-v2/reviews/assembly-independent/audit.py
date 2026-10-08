"""Independent streaming, read-only archive audit. No project imports/execution."""
from pathlib import Path, PurePosixPath
import gzip, hashlib, json

S=Path('/Users/junkawasaki/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-source-v2-lc-remote')
O=Path(__file__).resolve().parent
A=S/'assembly-outputs/package.tgz'
AH='3b099c22196af6ba53fae99c3696284e405714abacefef6015d39edcc210077a'
MH='67f00b5dae259c4a077ad104534a7a075f438127ab845513eaeb7ec7e865455b'
SH='b12caa329a1532399cab8b2ee94b5096bb1811d952aa76c3287b672b05917b4b'
RH='2a4379322134f28ff101f20e829058495f3246366565b815dd86252ff77e49eb'
H=lambda b:hashlib.sha256(b).hexdigest()
def filehash(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
assert A.is_file() and not A.is_symlink() and A.stat().st_size==121263001<=268435456 and filehash(A)==AH
assert H((S/'source-pins.json').read_bytes())==SH
bank=json.loads((S/'source-pins.json').read_text())
for n,r in bank.items():assert (S/n).stat().st_size==r['bytes'] and filehash(S/n)==r['sha256']
members={};data={};rawbytes=0;total=0
def stream(callback):
 count=0
 with gzip.open(A,'rb') as f:
  def read(n):
   nonlocal count
   b=f.read(n);assert len(b)==n;count+=n;assert count<=553648128;return b
  names=set();expanded=0
  while True:
   block=read(512)
   if block==bytes(512):
    assert read(512)==bytes(512)
    while b:=f.read(1048576):
     count+=len(b);assert count<=553648128 and not any(b)
    break
   assert block[156:157]==b'0' and block[257:263]==b'ustar\0' and block[263:265]==b'00'
   octal=lambda a:int(a.rstrip(b'\0 ').lstrip(b' ') or b'0',8)
   assert octal(block[148:156])==sum(block[:148])+8*32+sum(block[156:])
   name=block[:100].split(b'\0',1)[0].decode();prefix=block[345:500].split(b'\0',1)[0].decode()
   if prefix:name=prefix+'/'+name
   q=PurePosixPath(name);assert str(q)==name and q.parts[0]=='package' and '..' not in q.parts and not q.is_absolute() and name not in names
   names.add(name);assert len(names)<=49152
   assert not block[157:257].rstrip(b'\0') and octal(block[100:108])==0o444 and octal(block[108:116])==0 and octal(block[116:124])==0 and octal(block[136:148])==0
   size=octal(block[124:136]);assert 0<=size<=67108864;expanded+=size;assert expanded<=536870912
   h=hashlib.sha256();keep=size<=16777216 and name.endswith(('.json','.py','.md'));buf=[];remain=size
   while remain:
    b=read(min(remain,1048576));h.update(b);callback(name,b);remain-=len(b)
    if keep:buf.append(b)
   pad=(-size)%512
   if pad:assert read(pad)==bytes(pad)
   if callback is first:
    members[name]={'bytes':size,'sha256':h.hexdigest()}
    if keep:data[name]=b''.join(buf)
  return count,expanded
def first(name,b):pass
rawbytes,total=stream(first)
assert H(data['package/manifest.json'])==MH and data['package/manifest.json']==(S/'assembly-outputs/manifest.json').read_bytes()
m=json.loads(data['package/manifest.json']);assert m['schema']=='LC_REGULAR_PACKAGE/v2' and m['sourcePinsSHA256']==SH
expected={r['path']:{k:r[k] for k in ['bytes','sha256']} for r in m['members']}
assert len(expected)==len(m['members']) and set(members)==set(expected)|{'package/manifest.json'}
for n,r in expected.items():assert members[n]==r
assert H(data['package/source-pins.json'])==SH and json.loads(data['package/source-pins.json'])==bank
for n,r in bank.items():assert members['package/'+n]==r
assert H(data['package/root-functional285-acceptance.json'])==RH
ra=json.loads(data['package/root-functional285-acceptance.json']);assert ra['status']=='ROOT_ACCEPTED_FINITE_LC_ORIGINAL19_FUNCTIONAL285_ONLY' and ra['originalWorkloads']==19 and ra['profiles']==95 and ra['totalCalls']==285 and ra['performanceQualified'] is False
rr=json.loads(data['package/root-functional285-acceptance-ref.json']);assert rr['sha256']==RH and rr['bytes']==len(data['package/root-functional285-acceptance.json'])
g=json.loads(data['package/assembly-go.json']);assert g['phase']=='assembly' and g['authorized'] is True and g['sourcePinsSHA256']==SH and g['rootFunctional285AcceptanceSHA256']==RH
assert g['functionalAuthorized'] is False and g['timingAuthorized'] is False and g['remoteRoot']==m['remoteRoot']
assert len(g['sourceReviews'])==2 and g['sourceReviews'][0]['sha256']!=g['sourceReviews'][1]['sha256']
for i,r in enumerate(g['sourceReviews']):
 b=data['package/assembly-review'+str(i)+'.json'];q=json.loads(b)
 assert len(b)==r['bytes'] and H(b)==r['sha256'] and q['sourcePinsSHA256']==SH and str(q['status']).startswith('PASS')
orig=json.loads(data['package/input-origins.json']);omap=json.loads(data['package/origin-map.json'])
assert set(orig)==set(omap) and len(orig)==3493<=4096 and sum(r['bytes'] for r in orig.values())==415361908<=469762048
chunkmap={};states={};chunkreports=[]
for p,r in orig.items():
 target=omap[p]
 if isinstance(target,str):assert members[target]==r
 else:
  assert target['bytes']==r['bytes'] and target['sha256']==r['sha256']
  states[p]={'h':hashlib.sha256(),'bytes':0,'seen':[]}
  for index,c in enumerate(target['chunks']):
   assert c['path'] not in chunkmap and members[c['path']]=={k:c[k] for k in ['bytes','sha256']}
   chunkmap[c['path']]=(p,index)
def second(name,b):
 if name in chunkmap:
  p,index=chunkmap[name];state=states[p]
  if not state['seen'] or state['seen'][-1]!=index:
   assert index==len(state['seen']);state['seen'].append(index)
  state['h'].update(b);state['bytes']+=len(b)
assert stream(second)==(rawbytes,total)
for p,state in states.items():
 assert state['bytes']==orig[p]['bytes'] and state['h'].hexdigest()==orig[p]['sha256'] and len(state['seen'])==len(omap[p]['chunks'])
 chunkreports.append({'origin':p,'bytes':state['bytes'],'sha256':state['h'].hexdigest(),'chunks':omap[p]['chunks']})
pr=json.loads(data['package/preregistration.json'])
assert g['preregistrationSHA256']==H(data['package/preregistration.json'])
cp=pr['canonicalCPackage']
canonical=0
for n,r in members.items():
 if n.startswith('package/c-inputs/'):
  origin=cp+'/'+n.removeprefix('package/c-inputs/');assert orig[origin]==r;canonical+=1
assert canonical==sum(p.startswith(cp+'/') for p in orig)
assert members['package/sources/timing-host-telemetry.c']=={k:pr['consumerSource'][k] for k in ['bytes','sha256']}
terminal=json.loads((S/'assembly-outputs/terminal.json').read_text());assert terminal=={'children':0,'allClosed':True,'failure':False}
assert filehash(A)==AH and H((S/'source-pins.json').read_bytes())==SH
report={'status':'PASS_ACTUAL_ASSEMBLY_V2_INDEPENDENT_READONLY_AUDIT','archiveSHA256':AH,'archiveBytes':A.stat().st_size,'manifestSHA256':MH,'manifestBytes':len(data['package/manifest.json']),'sourcePinsSHA256':SH,'preregistrationSHA256':H(data['package/preregistration.json']),'rootFunctional285AcceptanceSHA256':RH,'regularMembers':len(members),'expandedBytes':total,'USTARFramedBytes':rawbytes,'logicalOriginsVerified':len(orig),'logicalOriginBytesVerified':sum(r['bytes'] for r in orig.values()),'canonicalSourceGraphMembersVerified':canonical,'losslessChunkReconstruction':chunkreports,'checks':{'strictRegularUSTAROnly':True,'allPathsUniqueSafe':True,'allArchiveCapsPass':True,'wholeMemberHashesPass':True,'actualArchivedManifestBytesPass':True,'completeMemberSetPass':True,'all3493OriginBytesPass':True,'sourceRegistryFrozenBytesPass':True,'exactRoot285AcceptancePass':True,'twoDistinctSourcePASSReviewsAndAssemblyGOValidated':True,'zeroChildAssemblyClosedTerminalObserved':True,'archiveStableBeforeAfter':True},'independence':'Reviewer authored only audit.py, report.json, member-hashes.json, review-freeze.json and README.md in this fresh review namespace. No assembly, extraction, transfer, compiler, native, guest or timing entrypoint executed; no project module imported. Audit is independent streaming byte parsing and hashing.','remainingGates':['Root actual assembly acceptance and separate exact transfer GO','Independent actual transfer acceptance','Independent actual build52 acceptance','New consumer functional285 and separately reviewed quiet/timing source'],'execution':{'assembly':0,'extractor':0,'SSH':0,'compiler':0,'native':0,'guest':0,'timing':0}}
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(O/'member-hashes.json').write_text(json.dumps(members,indent=2)+'\n')
(O/'README.md').write_text(report['status']+'\n\nIndependent read-only streaming audit of exact archive '+AH+'. See report.json and member-hashes.json. Transfer remains separately gated.\n')
freeze={p.name:{'bytes':p.stat().st_size,'sha256':filehash(p)} for p in O.iterdir() if p.is_file()}
(O/'review-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps({'status':report['status'],'report':freeze['report.json'],'reviewFreezeSHA256':filehash(O/'review-freeze.json'),'regularMembers':len(members),'expandedBytes':total,'USTARFramedBytes':rawbytes,'origins':len(orig),'canonicalGraphMembers':canonical},indent=2))
