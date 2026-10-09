"""Pure models/parser checks only; imports run.py without entering main."""
from pathlib import Path
import copy,json,struct,hashlib
from run import scope,argv,dependencies,diagnostic,macho,GO_KEYS,HOST_KEYS,environment_admission
D=Path(__file__).resolve().parent;pr=json.loads((D/'preregistration.json').read_text());ip=json.loads((D/'input-pins.json').read_text());rs=json.loads((D/'recipes.json').read_text())['commands'];assert scope(pr,ip,rs)
neg=0
for key,bad in [('exactInputFiles',54),('exactInputFiles',True),('exactInputLogicalBytes',0),('maximumInputFiles',512),('maximumInputBytes',4194304),('maximumChildCalls',38.0),('guestCalls',1),('C2',True),('maximumRawBytesPerStream',2097152),('maximumCampaignSeconds',7201),('maximumDynamicHeaders',4097),('cleanupSeconds',31)]:
 q=copy.deepcopy(pr);q[key]=bad
 try:scope(q,ip,rs)
 except AssertionError:neg+=1
 else:raise AssertionError(key)
h={'compiler':{'path':'/Library/Developer/CommandLineTools/usr/bin/clang'},'sdk':'/Library/Developer/CommandLineTools/SDKs/MacOSX26.2.sdk','resourceDirectory':'/Library/Developer/CommandLineTools/usr/lib/clang/17'};out=D/'C-build-outputs'
for r in rs:
 a=argv(r,D,out,h);b=argv(r,D,out,h,True);assert a[:4]==[h['compiler']['path'],'-O2','-std=gnu11','-dynamiclib']and '-M'not in a and b[4]=='-M'and '-o'not in b
 assert a[-1]==str(out/r['workload']/'c.dylib') and all('$'not in x for x in a+b)
# Multiple -M targets are required by qrduino/sglib original recipes.
names=['inputs/qrduino/c-bridge.c','inputs/upstream/src/qrduino/qrframe.c','inputs/upstream/support/beebsc.c'];raw='\n'.join(f'x{i}.o: {D/n}'for i,n in enumerate(names))+'\n';deps=dependencies(raw.encode(),D,h,ip);assert len(deps)==3
for bad in [b'',b'x.o: /tmp/unknown.h\n',b'x.o: inputs/no-such.h\n',b'a: b: c\n',raw.encode()+b'\0']:
 try:dependencies(bad,D,h,ip)
 except (AssertionError,FileNotFoundError):neg+=1
 else:raise AssertionError('deps')
for bad in [b'error: bad\n',b'warning:\0',b'\xff']:
 try:diagnostic(bad)
 except (AssertionError,UnicodeDecodeError):neg+=1
 else:raise AssertionError('diagnostic')
assert diagnostic(b'warning: unused command argument\n')is True
name=b'/usr/lib/libSystem.B.dylib\0';cmd=struct.pack('<IIIIII',12,56,24,0,0,0)+name;cmd=cmd+bytes(56-len(cmd));raw=struct.pack('<IIIIIIII',0xfeedfacf,0x100000c,0,6,1,56,0,0)+cmd;assert macho(raw)==['/usr/lib/libSystem.B.dylib']
for offset,value in [(4,7),(12,2),(16,0),(36,7)]:
 q=bytearray(raw);struct.pack_into('<I',q,offset,value)
 try:macho(bytes(q))
 except AssertionError:neg+=1
 else:raise AssertionError('MachO')
# Frozen owned source receipts and original recipe provenance, no external tool/API calls.
for n,r in ip.items():b=(D/n).read_bytes();assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256']
env=pr['environment']|{'TMPDIR':str(out/'tmp')}
assert environment_admission(env,env)['runtimeExtraKeyNames']==[]
assert environment_admission(env,dict(env,__CF_USER_TEXT_ENCODING='0x1F5:0x0:0x0'))['runtimeExtraKeyNames']==['__CF_USER_TEXT_ENCODING']
for name,observed in [('unknown',dict(env,UNKNOWN='x')),('changed',dict(env,LANG='other')),('missing',{k:v for k,v in env.items()if k!='TZ'})]:
 try:environment_admission(env,observed)
 except AssertionError:neg+=1
 else:raise AssertionError('environment '+name)
assert 'os.execve(a[0],a,env)'in(D/'limit-exec.py').read_text()
print(json.dumps({'status':'PASS_PURE_C19_BUILD38_SOURCE_CONTROLS_ONLY','ownedInputs':len(ip),'inputBytes':sum(x['bytes']for x in ip.values()),'exactBuildArgvPositives':19,'exactDependenciesArgvPositives':19,'multiTranslationUnitDependencyPositive':1,'MachOPositive':1,'boundedWarningPositive':1,'refusals':neg,'namedMetadataPositives':2,'namedMetadataRefusals':3,'Python39SourceCompatible':True,'compilerCalls':0,'nativeGuestCalls':0,'networkCalls':0},indent=2))
