"""Independent saved-byte audit; no project imports or operational execution."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,re,struct,copy,base64,shlex,ast
W=Path('/Users/junkawasaki/github/workspaces/codex')
S=W/'vector-leaf-straight-read-cache-current19-build52-source-v2-lc-remote'
G=W/'vector-leaf-straight-read-cache-current19-build52-go-v2-root'
C=G/'collected';B=C/'build52';O=Path(__file__).resolve().parent
ROOT='/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-v2-root'
SH='b12caa329a1532399cab8b2ee94b5096bb1811d952aa76c3287b672b05917b4b'
AH='3b099c22196af6ba53fae99c3696284e405714abacefef6015d39edcc210077a'
MH='67f00b5dae259c4a077ad104534a7a075f438127ab845513eaeb7ec7e865455b'
RH='2a4379322134f28ff101f20e829058495f3246366565b815dd86252ff77e49eb'
CH='fc4976c2c38edf426275df82a200b5ab99128c7dcb4c79a120d95e12ca62abb0'
H=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_text())
inputs={}
def pin(p,r=None):
 p=Path(p);assert p.is_file() and not p.is_symlink();b=p.read_bytes();q={'bytes':len(b),'sha256':H(b)}
 if r:assert q=={k:r[k] for k in ['bytes','sha256']}
 inputs[str(p)]={'path':str(p),**q};return b
def remote(r):
 assert r['path'].startswith(ROOT+'/');return pin(C/r['path'].removeprefix(ROOT+'/'),r)
archive=pin(G/'collected-build52.tgz');assert len(archive)==1378053 and H(archive)==CH
members={}
with tarfile.open(G/'collected-build52.tgz','r:gz') as t:
 for m in t:
  q=PurePosixPath(m.name);assert m.isfile() and not m.pax_headers and not m.sparse and not m.issym() and not m.islnk() and not q.is_absolute() and '..' not in q.parts and str(q)==m.name and m.name not in members
  b=t.extractfile(m).read();assert len(b)==m.size and b==pin(C/m.name)
  members[m.name]={'bytes':len(b),'sha256':H(b)}
assert len(members)==195 and sum(r['bytes'] for r in members.values())==9189014
assert set(members)=={str(p.relative_to(C)) for p in C.rglob('*') if p.is_file()}
cr=load(C/'collection-receipt.json');assert cr['status']=='READONLY_BUILD52_RECEIPT_COLLECTION_ONLY' and cr['sourcePinsSHA256']==SH and cr['root']==ROOT and cr['compilerCalls']==cr['nativeCalls']==0
assert {r['path']:{k:r[k] for k in ['bytes','sha256']} for r in cr['members']}=={n:r for n,r in members.items() if n!='collection-receipt.json'}
assert len(cr['members'])==194
assert H(pin(S/'source-pins.json'))==SH and pin(C/'package/source-pins.json')==(S/'source-pins.json').read_bytes()
bank=load(S/'source-pins.json')
for n,r in bank.items():pin(S/n,r)
pr=load(S/'preregistration.json');assert len(pr['entries'])==19 and pr['totalChildren']==52
assert H(pin(C/'package/manifest.json'))==MH
man=load(C/'package/manifest.json');assert man['sourcePinsSHA256']==SH and man['remoteRoot']==ROOT
manifest={r['path']:r for r in man['members']}
for n,r in bank.items():assert {k:manifest['package/'+n][k] for k in ['bytes','sha256']}==r
assert {k:manifest['package/sources/timing-host-telemetry.c'][k] for k in ['bytes','sha256']}=={k:pr['consumerSource'][k] for k in ['bytes','sha256']}
assert pr['consumerSource']['sha256']=='cb3fb83d563c47e9d823d7d375ff183c363e1c2c03efb14430e3e6c81300294e'
g=json.loads(pin(G/'build-go.json'));rg=json.loads(pin(C/'control/build-go.json'))
assert g['phase']=='build' and g['authorized'] is True and g['sourcePinsSHA256']==SH and g['archiveSHA256']==AH and g['manifestSHA256']==MH and g['rootFunctional285AcceptanceSHA256']==RH
assert g['preregistrationSHA256']==H((S/'preregistration.json').read_bytes())
assert g['functionalAuthorized'] is False and g['timingAuthorized'] is False and g['destination']=='zebulun@100.66.28.79' and g['remoteRoot']==ROOT
assert [g[k] for k in ['maximumChildren','CBuilds','consumerBuilds','identityQueries','maximumLaunchTransportChildren']]==[52,19,19,14,1]
derived=copy.deepcopy(g)
for i,r in enumerate(g['sourceReviews']):
 b=pin(r['path'],r);assert b==pin(C/'control'/('review'+str(i)+'.json'))
 v=json.loads(b);assert v['status'].startswith('PASS') and v['sourcePinsSHA256']==SH
 derived['sourceReviews'][i]=dict(r,path=ROOT+'/control/review'+str(i)+'.json')
assert len(g['sourceReviews'])==2 and g['sourceReviews'][0]['sha256']!=g['sourceReviews'][1]['sha256']
b=pin(g['transferAcceptance']['path'],g['transferAcceptance']);assert b==pin(C/'control/transfer-acceptance.json')
ta=json.loads(b);assert ta['status'].startswith('PASS') and ta['archiveSHA256']==AH
pin(ta['independentReview']['path'],ta['independentReview'])
derived['transferAcceptance']=dict(g['transferAcceptance'],path=ROOT+'/control/transfer-acceptance.json')
derived['originalLocalGOSHA256']=H((G/'build-go.json').read_bytes())
rb=json.dumps(derived,indent=2).encode()+b'\n';assert rg==derived and rb==(C/'control/build-go.json').read_bytes()
L=S/'build-launch-outputs';assert pin(L/'derived-remote-go.json')==rb
lr=json.loads(pin(L/'report.json'));assert lr['remoteGOSHA256']==H(rb) and lr['archiveSHA256']==AH and lr['sourcePinsSHA256']==SH and lr['actualBuildAcceptance'] is False
assert json.loads(pin(L/'terminal.json'))=={'children':1,'allClosed':True,'failure':False}
la=json.loads(pin(L/'children/attempts.json'));assert len(la)==1
launch=la[0];assert launch['state']=='terminal' and launch['returncode']==0 and launch['exception'] is None and launch['cleanupException'] is None and launch['timeoutSeconds']==7980
assert pin(launch['stdout']['path'],launch['stdout'])==b'LC_BUILD52_REMOTE_TERMINAL\n' and pin(launch['stderr']['path'],launch['stderr'])==b''
files={n:base64.b64encode((C/'control'/n).read_bytes()).decode() for n in ['review0.json','review1.json','transfer-acceptance.json','build-go.json']}
req=dict(files=files,remoteGOSHA256=H(rb),sourcePinsSHA256=SH)
encoded=base64.b64encode(json.dumps(req,separators=(',',':')).encode()).decode()
tree=ast.parse((S/'launch-build.py').read_text())
template=next(n.value.left.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='wrapper' for t in n.targets))
wrapper=template%(ROOT,encoded)
assert launch['argv']==['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',g['destination'],'python3 -c '+shlex.quote(wrapper)]
assert launch['environment']==dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/junkawasaki',TMPDIR='/private/tmp')
before=load(B/'identity-before.json');after=load(B/'identity-after.json');assert before==after
e=pr['expectedHost'];assert before['version'].splitlines()[0]==e['version'] and before['target']==e['target'] and before['SDKVersion']==e['SDK'] and before['OS']==e['OS'] and before['OSBuild']==e['OSBuild']
assert before['compiler']=='/Library/Developer/CommandLineTools/usr/bin/clang' and before['SDK']=='/Library/Developer/CommandLineTools/SDKs/MacOSX26.2.sdk'
env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/zebulun',TMPDIR=ROOT+'/tmp');fullenv=dict(env,SDKROOT=before['SDK'])
ev=load(B/'effective-environment.json');assert ev['environment']==fullenv and ev['allOtherInheritedVariablesRemoved'] is True and 'CPATH' in ev['removedNames'] and 'LIBRARY_PATH' in ev['removedNames']
rows=load(B/'children/attempts.json');assert len(rows)==52
identlabels=['resolved-clang','sdk-path','sdk-version','clang-version','clang-target','OS-version','OS-build']
queries=[[s.replace('$RESOLVED_CLANG',before['compiler']) for s in a] for a in pr['identityQueryArgv']]
expectedrows=[]
for label,argv in zip(identlabels,queries):expectedrows.append(('before-'+label,argv,30,env))
for r in pr['entries']:
 argv=[s.replace('$RESOLVED_CLANG',before['compiler']).replace('$TASK_ROOT',ROOT+'/package/c-inputs').replace('$FRESH_BUILD',ROOT+'/build52') for s in r['CBuild']]
 for s in r['CBuild']:
  if s.startswith('$TASK_ROOT/') and s.endswith('.c'):assert 'package/c-inputs/'+s.removeprefix('$TASK_ROOT/') in manifest
 expectedrows.append(('C-'+r['workload'],argv,180,fullenv))
for r in pr['entries']:
 argv=[s.replace('$RESOLVED_CLANG',before['compiler']).replace('$PACKAGE',ROOT+'/package').replace('$FRESH_BUILD',ROOT+'/build52') for s in r['consumerBuild']]
 expectedrows.append(('consumer-'+r['workload'],argv,180,fullenv))
for label,argv in zip(identlabels,queries):expectedrows.append(('after-'+label,argv,30,fullenv))
raw=[]
for i,(r,x) in enumerate(zip(rows,expectedrows)):
 assert r['index']==i+1 and (r['label'],r['argv'],r['timeoutSeconds'],r['environment'])==x
 assert r['state']=='terminal' and r['returncode']==0 and r['exception'] is None and r['cleanupException'] is None
 for k in ['stdout','stderr']:
  assert r[k]['path']==r[k+'Path']==ROOT+'/build52/children/'+str(i+1)+'.'+k
  b=remote(r[k]);assert len(b)<=16777216;raw.append(r[k])
 if i<7 or i>=45:assert remote(r['stderr'])==b''
for i in range(7):assert remote(rows[i]['stdout'])==remote(rows[i+45]['stdout'])
values=[remote(rows[i]['stdout']).decode().strip() for i in range(7)]
assert values==[before['compiler'],'/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk',before['SDKVersion'],before['version'],before['target'],before['OS'],before['OSBuild']]
ci=load(B/'C-images.json');hi=load(B/'consumer-images.json');assert len(ci)==len(hi)==19
anchors=[]
for j,(r,c,h) in enumerate(zip(pr['entries'],ci,hi)):
 name=r['workload'];assert c['workload']==h['workload']==name and c['symbol']==r['CSymbol']
 assert c['argv']==rows[7+j]['argv'] and h['argv']==rows[26+j]['argv'] and h['C']==c['C'] and h['nativeCalls']==0
 for image in [c,h]:assert image['compilerIdentityBefore']==image['compilerIdentityAfter']==before
 cb=remote(c['C']);run=remote(h['runner']);hb=remote(h['header']);text=hb.decode()
 for b,kind in [(cb,6),(run,2)]:assert len(b)>=32 and b[:4]==b'\xcf\xfa\xed\xfe' and struct.unpack_from('<I',b,4)[0]==0x100000c and struct.unpack_from('<I',b,12)[0]==kind
 def array(name):
  matches=re.findall(r'static const unsigned char '+name+r'\[\] = \{([^}]*)\};',text);assert len(matches)==1;return bytes(int(x) for x in matches[0].split(','))
 off=array('known_baseline');lc=array('known_candidate');fresh=array('timing_known_c_bytes')
 assert len(off)==r['OFF']['bytes'] and H(off)==r['OFF']['sha256'] and len(lc)==r['LC']['bytes'] and H(lc)==r['LC']['sha256'] and fresh==cb
 arr=lambda n,b:'static const unsigned char '+n+'[] = {'+','.join(map(str,b))+'};\n'
 exact='#include <stddef.h>\n#include <stdint.h>\n#define KEXE_EMBEDDED 1\n#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES '+str(r['nativeFeatureRequirements']['OFF']|r['nativeFeatureRequirements']['LC'])+'ULL\n#define KEXE_EMBEDDED_ISA "aarch64"\n#define TIMING_KNOWN_IMAGES 2\n'
 exact+=arr('known_baseline',off)+arr('known_candidate',lc)+'static const unsigned char *const timing_known_images[] = {known_baseline,known_candidate};\n'
 exact+='static const size_t timing_known_sizes[] = {'+str(len(off))+','+str(len(lc))+'};\nstatic const uint64_t timing_known_offsets[] = {'+str(r['OFF']['offset'])+','+str(r['LC']['offset'])+'};\n'
 exact+='#define TIMING_KNOWN_DYLIB 1\n#define TIMING_KNOWN_C_SYMBOL '+json.dumps(r['CSymbol'])+'\n'+arr('timing_known_c_bytes',cb)
 assert exact.encode()==hb
 hr=load(B/name/'header-receipt.json');assert hr['header']==h['header'] and hr['C']==c['C'] and hr['OFF']==r['OFF'] and hr['LC']==r['LC'] and hr['CSymbol']==r['CSymbol'] and hr['featureRequirements']==r['nativeFeatureRequirements'] and hr['entryOffsets']==[r['OFF']['offset'],r['LC']['offset']] and hr['bodyUnchanged'] is True
 anchors.append({'workload':name,'C':c['C'],'header':h['header'],'runner':h['runner'],'wholeOFFLCAndFreshCBytesVerified':True,'wholeHeaderTextVerified':True,'offsets':hr['entryOffsets'],'CSymbol':r['CSymbol'],'featureRequirements':r['nativeFeatureRequirements']})
report0=load(B/'report.json');assert report0['status']=='PASS_FRESH_C19_CONSUMER19_BUILD52_IDENTITY_ONLY' and report0['images']==hi and report0['children']==52 and report0['CBuilds']==report0['consumerBuilds']==19 and report0['identityQueries']==14
for k,v in [('sourcePinsSHA256',SH),('archiveSHA256',AH),('manifestSHA256',MH),('rootFunctional285AcceptanceSHA256',RH),('preregistrationSHA256',g['preregistrationSHA256'])]:assert report0[k]==v
assert report0['nativeCalls']==report0['timingCalls']==0 and report0['functionalQualified'] is report0['quietQualified'] is report0['SDKWholeTreeHashQualified'] is False
assert load(B/'terminal.json')==dict(children=52,allClosed=True,failure=False,nativeCalls=0,timingCalls=0)
assert not (B/'failure.json').exists()
old=[]
for name in ['assembly','transfer']:
 p=G/(name+'-acceptance.json');v=json.loads(pin(p));assert v['status'].startswith('PASS') and v['archiveSHA256']==AH
 r=v['independentReview'];pin(r['path'],r);old.append(r)
report={'status':'PASS_ACTUAL_BUILD52_V2_INDEPENDENT_SAVED_RAW_IDENTITY_ONLY','sourcePinsSHA256':SH,'archiveSHA256':AH,'manifestSHA256':MH,'preregistrationSHA256':g['preregistrationSHA256'],'rootFunctional285AcceptanceSHA256':RH,'collectedArchiveSHA256':CH,'originalLocalGOSHA256':H((G/'build-go.json').read_bytes()),'remoteGOSHA256':H(rb),'children':52,'CBuilds':19,'consumerBuilds':19,'identityQueries':14,'allClosed':True,'allReturnCodesZero':True,'exceptions':0,'cleanupExceptions':0,'rawStreamsVerified':104,'collectedMembersVerified':195,'collectedExpandedBytes':9189014,'identityBeforeAfter':before,'images':anchors,'checks':{'allCollectedArchiveAndLocalBytesMatch':True,'collectionMemberRegistryComplete':True,'currentFrozenRegistryPass':True,'localToRemoteGOExactTranslationPass':True,'launchPinnedControlPayloadExactArgvAndRawSealPass':True,'exact52ArgvOrderEnvironmentTimeoutsPass':True,'fullRawBytesReturnCodesAndReapReceiptsPass':True,'beforeAfterSevenRawIdentityQueriesPass':True,'all19CanonicalCRecipesPass':True,'all19ConsumerCb3fRecipesPass':True,'all19WholeHeaderTextsPayloadOffsetsSymbolsFeaturesAndFreshCBytesPass':True,'all38ThinARM64KindsPass':True},'priorAcceptedReviews':old,'functionalQualified':False,'quietQualified':False,'timingQualified':False,'SDKWholeTreeHashQualified':False,'nativeCalls':0,'timingCalls':0,'independence':'Reviewer participated in V2 SOURCE, actual assembly and transfer reviews, but authored no operational driver and executed no remote/compiler/native/guest/timing operation. Only independent saved-byte review artifacts authored. Complete prior origin archive audit reused via accepted exact review refs; no duplicate 3493-origin reread. Compiler/SDKSettings byte identities and SDK alias canonical resolution are the guarded remote driver receipts, while all 14 query raw streams and identity stability were independently checked.','remainingGates':['Root actual build52 acceptance','Separate reviewed executable new-consumer functional285 source and rootGO','Separate quiet/timing source reviews and rootGO after accepted new-consumer285'],'reviewExecution':dict(SSH=0,compiler=0,native=0,guest=0,timing=0,driver=0)}
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(O/'input-pins.json').write_text(json.dumps(inputs,indent=2)+'\n')
(O/'full-raw-refs.json').write_text(json.dumps(raw,indent=2)+'\n')
(O/'README.md').write_text(report['status']+'\n\nSOURCE, archive and transfer review participation disclosed. Full audit inputs frozen in input-pins.json. Functional285, quiet and timing remain separately gated.\n')
for p,r in list(inputs.items()):pin(p,r)
freeze={p.name:{'bytes':p.stat().st_size,'sha256':H(p.read_bytes())} for p in O.iterdir() if p.is_file()}
(O/'review-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps({'status':report['status'],'report':freeze['report.json'],'inputPins':freeze['input-pins.json'],'reviewFreezeSHA256':H((O/'review-freeze.json').read_bytes()),'inputs':len(inputs)},indent=2))
