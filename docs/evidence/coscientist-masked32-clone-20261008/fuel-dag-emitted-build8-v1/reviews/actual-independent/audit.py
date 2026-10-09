from pathlib import Path
import json,hashlib,sys,stat,re
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-fuel-scalar-dag-emitted18-source-v1-width';R=D/'build-outputs';O=Path(__file__).resolve().parent;ip={}
def j(p):return json.loads(Path(p).read_text())
def pin(p,v=None):
 p=Path(p);st=p.lstat();assert stat.S_ISREG(st.st_mode)and not p.is_symlink();h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 assert st==p.lstat();z={'bytes':st.st_size,'sha256':h.hexdigest()}
 if v is not None:assert z=={k:v[k]for k in ['bytes','sha256']},str(p)
 ip[str(p)]=z;return z
def save(n,z):(O/n).write_text(json.dumps(z,indent=2)+'\n')
assert len(sys.argv)==2 and sys.argv[1]=='ROOT_CONFIRMED_CLOSED_BUILD8'
gpath=W/'vector-fuel-scalar-dag-emitted-build8-go-v1-root/root-go.json';g=j(gpath);gh=pin(gpath);assert gh['sha256']=='3c400eae7cb741f125e5ba033692af38c2e077a5f4dbfd9681015ac5e892c455'
pr=j(D/'build-preregistration.json');sp=j(D/'source-pins.json');assert pin(D/'source-pins.json')['sha256']==g['driverSourcePinsSHA256']=='4b289f6f678dbef35112a8a9d9ed98ef975a10c4e7150fccdc6deb9c8ada66b9'
for n,v in sp.items():pin(D/n,v)
for p,v in j(D/'input-pins.json').items():pin(p,v)
assert g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==8 and g['workloadGuestAuthorized']is False and g['timingAuthorized']is False and g['outputRoot']==str(R)
assert g['driverSHA256']==pin(D/'build8.py')['sha256']and g['preregistrationSHA256']==pin(D/'build-preregistration.json')['sha256']
for z in g['sourceReviews']+g['driverReviews']:
 pin(z['path'],z);rv=j(z['path']);assert rv['status']=='PASS_SOURCE_ONLY_FUEL_DAG_EMITTED18_PARTITION'and rv['driverSourcePinsSHA256']==g['driverSourcePinsSHA256']
ns={'__file__':str(D/'build8.py'),'__name__':'pinned_offline_only'};src=(D/'build8.py').read_bytes();assert hashlib.sha256(src).hexdigest()==sp['build8.py']['sha256'];exec(compile(src,str(D/'build8.py'),'exec'),ns)
rows=j(R/'attempts.json');pin(R/'attempts.json');assert len(rows)==8 and j(R/'terminal.json')=={'loaderCalls':8,'allChildrenClosed':True,'failure':False};pin(R/'terminal.json');assert not(R/'failure.json').exists()
env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(R),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(R),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1'}
images=j(R/'images.json');pin(R/'images.json');assert len(images)==4;blobs={}
for idx,image in enumerate(images):
 fixture,arm=image['fixture'],image['arm'];label=fixture+'-'+arm;assert (fixture,arm)==[('positive','OFF'),('positive','ON'),('negative','OFF'),('negative','ON')][idx]
 pin(image['source']['path'],image['source']);assert Path(image['source']['path']).read_bytes()==(D/(fixture+'.kotoba')).read_bytes()
 for role in ['container','native']:pin(image[role]['path'],image[role])
 body,exports=ns['kseed'](Path(image['container']['path']).read_bytes());assert body==Path(image['native']['path']).read_bytes()and [list(x)for x in exports]==image['exports']and image['arity']==1 and ('bench',image['offset'],1)in exports;blobs[(fixture,arm)]=body
 for stage in ['compile','extract']:
  i=idx*2+(0 if stage=='compile'else 1);row=rows[i];lab=label+'-'+stage;producer=pr[arm+'Producer'];args=['compile',str(R/(fixture+'.kotoba')),'--target','aarch64-macos','--output',str(R/(label+'.kseed'))]if stage=='compile'else['extract-native',str(R/(label+'.kseed')),'--symbol','bench','--output',str(R/(label+'.bin'))]
  assert row['index']==i+1 and row['label']==lab and row['argv']==[pr['loader'],producer,'0','0','aarch64','35,37,38,39','--',*args]and row['effectiveEnvironment']==env
  assert row['state']=='terminal'and row['spawned']is True and row['reaped']is True and row['returncode']==0 and not row['error']and not row['terminationReason']and not row['cleanupExceptions'];op=R/(lab+'.stdout');ep=R/(lab+'.stderr');pin(op,row['stdout']);pin(ep,row['stderr']);assert op.stat().st_size<=1048576 and ep.stat().st_size<=1048576
  assert ns['counters'](ep.read_bytes())==row['counterObservation']and row['counterObservation']['status']=='valid';raw=op.read_bytes();assert b':ok true'in raw and b':ok false'not in raw
  if stage=='extract':assert re.findall(rb':offset ([0-9]+)\b',raw)==[str(image['offset']).encode()]
for p,v in j(R/'generated-pins.json').items():pin(p,v)
assert blobs[('negative','OFF')]==blobs[('negative','ON')]and(R/'negative-OFF.kseed').read_bytes()==(R/'negative-ON.kseed').read_bytes()
# Narrow exact-word disassembler/reencoder for all actual words; refuses unknown instructions.
def sx(x,b):return x-(1<<b)if x&(1<<(b-1))else x
def decode(word,pc):
 if word&0xfc000000 in(0x14000000,0x94000000):
  target=pc+4*sx(word&0x3ffffff,26);assert 0<=target;return {'op':'BL'if word&0x80000000 else'B','target':target,'word':word}
 if word&0xff000010==0x54000000:
  assert word&15==2;return {'op':'B.HS','target':pc+4*sx((word>>5)&0x7ffff,19),'word':word}
 if word&0xffe0001f==0xd4200000:return {'op':'BRK','imm':(word>>5)&0xffff,'word':word}
 table={0x92407c09:'AND x9,x0,#0xffffffff',0xaa0903e0:'MOV x0,x9',0xd65f03c0:'RET x30',0xa9bf7bfd:'STP x29,x30,[sp,#-16]!',0x910003fd:'MOV x29,sp',0xd10103ff:'SUB sp,sp,#64',0xa90053f3:'STP x19,x20,[sp]',0xf9001fe7:'STR x7,[sp,#56]',0xaa0003f3:'MOV x19,x0',0xaa0103f4:'MOV x20,x1',0xf94004f0:'LDR x16,[x7,#8]',0xf1000610:'SUBS x16,x16,#1',0xf90004f0:'STR x16,[x7,#8]',0xd37ffa69:'LSL x9,x19,#1',0xca140129:'EOR x9,x9,x20',0xf9401fe7:'LDR x7,[sp,#56]',0xd3407c00:'AND x0,x0,#0xffffffff',0xaa0003e9:'MOV x9,x0',0xa94053f3:'LDP x19,x20,[sp]',0x910003bf:'MOV sp,x29',0xa8c17bfd:'LDP x29,x30,[sp],#16',0xf90003f3:'STR x19,[sp]',0xaa1303e0:'MOV x0,x19',0xd28000e1:'MOVZ x1,#7',0x8b130129:'ADD x9,x9,x19',0xf94003f3:'LDR x19,[sp]',0xd37ff809:'LSL x9,x0,#1',0xca010129:'EOR x9,x9,x1'}
 assert word in table,hex(word);return {'op':table[word],'word':word}
listing={}
for key,body in blobs.items():
 assert len(body)%4==0;lst=[dict(pc=pc,**decode(int.from_bytes(body[pc:pc+4],'little'),pc))for pc in range(0,len(body),4)]
 assert b''.join(z['word'].to_bytes(4,'little')for z in lst)==body;assert all('target'not in z or z['target']<len(body)and z['target']%4==0 for z in lst);listing['/'.join(key)]=lst
FUEL=[0xf94004f0,0xf1000610,0x54000042,0xd4200000,0xf90004f0]
def words(body):return[int.from_bytes(body[i:i+4],'little')for i in range(0,len(body),4)]
a=blobs[('positive','OFF')];b=blobs[('positive','ON')];assert len(a)==232 and len(b)==272 and a[:196]==b[:196]and a[200:]==b[240:]
assert words(a)[49]==0x97ffffd3 and words(b[196:216])==FUEL
assert words(b[216:240])==[0xd37ff809,0xca010129,0xaa0903e0,0xd3407c00,0xaa0003e9,0xaa0903e0]
for arm in ['OFF','ON']:
 body=blobs[('positive',arm)];assert words(body[164:184])==FUEL;assert words(body[44:64])==FUEL
 entries={0,16,112,140};regions=[164,44]if arm=='OFF'else[164,196]
 for start in regions:
  for ins in listing['positive/'+arm]:
   if 'target'in ins and start<ins['target']<start+20:assert ins['pc']==start+8 and ins['target']==start+16 and ins['op']=='B.HS'
 assert not any(start<x<start+20 for start in regions for x in entries)
# Call closure explicitly: entry140, OFF call196→16 and RET104→200; ON has no call.
assert next(z for z in listing['positive/OFF']if z['pc']==196)['target']==16
assert [z['pc']for z in listing['positive/OFF']if z['op']=='BL']==[196]and not[z for z in listing['positive/ON']if z['op']=='BL']
assert words(a[140:164])==[0xa9bf7bfd,0x910003fd,0xd10103ff,0xf90003f3,0xf9001fe7,0xaa0003f3]
assert words(a[184:196])==[0xaa1303e0,0xd28000e1,0xf9401fe7]
assert words(a[212:228])==[0xf94003f3,0x910003bf,0xa8c17bfd,0xd65f03c0]and words(b[252:268])==words(a[212:228])
assert words(a[16:44])==[0xa9bf7bfd,0x910003fd,0xd10103ff,0xa90053f3,0xf9001fe7,0xaa0003f3,0xaa0103f4]
assert words(a[72:108])==[0xaa0903e0,0xf9401fe7,0xd3407c00,0xaa0003e9,0xaa0903e0,0xa94053f3,0x910003bf,0xa8c17bfd,0xd65f03c0]
# Every reachable instruction is arithmetic or registered stack/context access; extra112 charge uncalled.
reachableOFF=list(range(140,228,4))+list(range(16,108,4));reachableON=list(range(140,268,4));assert 112 not in reachableOFF and 112 not in reachableON
proof={'schema':'FUEL_DAG_EMITTED_MACHINE8_STATIC/v1','status':'PASS_STATIC_ACTUAL_MACHINE_FUEL_ORDER_FIXED_FIXTURE_ONLY','actualBuildCalls':8,'positiveQualifiedSiteCount':1,'negativeWholeIdentity':True,'images':images,'fuelTransactionProof':{'benchEntryUnits':1,'outerUnits':1,'additionalDynamicCharges':0,'privateContextX7Preserved':True,'fuelInteriorIngress':False,'directBenchABI':True},'benchEntryByteOffset':140,'benchFuelByteOffset':164,'OFFOuterCallByteOffset':196,'OFFOuterEntryByteOffset':16,'OFFOuterFuelByteOffset':44,'ONInlineOuterFuelByteOffset':196,'unchangedPrefixBytes':196,'suffixRelocationDeltaBytes':40,'inlineSubstitutionSpan':[196,240],'extraUnreachableFuelByteOffset':112,'wordDecodeReencodeCounts':{k:len(v)for k,v in listing.items()},'sourceABIContextAssumption':'Accepted e14 loader supplies private synchronous context at x7 and valid stack; original stack frames preserve x7 before each fuel use. No callback/heap/indirect memory access on the fixed entry closure.','typedSIROwnerMetadataCaptured':False,'typedSIRCorrespondenceQualified':False,'machineOwnerEvidence':'One actual direct private entry16 from BL196; full body independently decoded, no FNID/SIR receipt invented.','CPUExecutionQualified':False,'actualNonresumingTrapQualified':False,'performanceQualified':False,'nativeCompilerSSHCallsByReviewer':0}
save('machine-proof.json',proof);save('word-listing.json',listing)
actual=j(R/'report.json');pin(R/'report.json');assert actual['status']=='COMPLETE_FUEL_DAG_EMITTED_BUILD8_ARTIFACT_IDENTITY_ONLY'and actual['images']==images
report={'status':'PASS_INDEPENDENT_SAVED_RAW_FUEL_DAG_EMITTED_BUILD8_IDENTITY_STATIC_MACHINE_ONLY','driverSourcePinsSHA256':g['driverSourcePinsSHA256'],'rootGOSHA256':gh['sha256'],'actualBuildCalls':8,'closedLoaderCalls':8,'negativeWholeIdentity':True,'positiveQualifiedSiteCount':1,'fuelTransactionProof':proof['fuelTransactionProof'],'images':images,'machineAcceptanceEligibility':'STATIC_MACHINE_PATH_PROVED_TYPED_SIR_OWNER_CORRESPONDENCE_UNCAPTURED_ROOT_MUST_RESOLVE_PREREG_SCOPE','typedSIRCorrespondenceQualified':False,'guestCallsByReviewer':0,'actualCPUTrapQualified':False,'performanceQualified':False,'full19Qualified':False,'participation':'Reviewer independently SOURCE reviewed emitted18 and component18 earlier. This independently hashes saved raw and decodes exact actual words; no native rerun or independent OS trace.','limits':['Static machine path/fuel/context proof under accepted private loader ABI is not CPU trap execution.','Original prereg mentions typed SIR ownership; build8 stdout has no SIR/FREC observer metadata. No typed FNIDs or SIR correspondence inferred.','Guest admission requires separate root actual machine acceptance scope and accepted complete component18 receipt.']}
save('report.json',report);save('input-pins.json',ip);save('completion-pins.json',{p.name:pin(p)for p in sorted(O.iterdir())if p.is_file()and p.name!='completion-pins.json'});print(json.dumps({'report':pin(O/'report.json'),'machine':pin(O/'machine-proof.json'),'inputPins':pin(O/'input-pins.json')}))
