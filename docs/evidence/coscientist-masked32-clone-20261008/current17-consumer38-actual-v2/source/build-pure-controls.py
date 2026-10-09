"""Pure models only. Never invokes main, compiler, FD, thread, or guest."""
import copy,json,ast
from pathlib import Path
import build
D=Path(__file__).resolve().parent
pr=build.load(D/'build-preregistration.json');ip=build.load(D/'input-pins.json');rs=build.load(D/'recipes.json')['commands']
assert build.scope(pr,ip,rs)
n=0
def refuses(f):
 global n
 try:f()
 except (AssertionError,ValueError,KeyError,TypeError):n+=1;return
 raise AssertionError('mutant accepted')
for k in ['exactInputFiles','exactInputLogicalBytes','maximumChildCalls','dependencyCalls','buildCalls','guestCalls','consumerCalls','timingCalls','maximumCampaignSeconds','dependencyTimeoutSeconds','buildTimeoutSeconds','cleanupSeconds']:
 q=copy.deepcopy(pr);q[k]+=1;refuses(lambda:build.scope(q,ip,rs))
for k in ['maximumInputFiles','maximumInputBytes','maximumDynamicHeaders','maximumDynamicHeaderBytes','maximumSingleHeaderBytes','maximumRawBytesPerStream','maximumArtifactBytes','controlledOutputReservationBytes']:
 q=copy.deepcopy(pr);q[k]+=1;refuses(lambda:build.scope(q,ip,rs))
q=copy.deepcopy(pr);q['guestCalls']=False;refuses(lambda:build.scope(q,ip,rs))
for k in ['C2','noRetry']:
 q=copy.deepcopy(pr);q[k]=not q[k];refuses(lambda:build.scope(q,ip,rs))
q=copy.deepcopy(rs);q[0]['argvTemplate'][2]='-O3';refuses(lambda:build.scope(pr,ip,q))
q=copy.deepcopy(rs);q[1]['workload']=q[0]['workload'];refuses(lambda:build.scope(pr,ip,q))
root=Path('/fixed');out=root/'consumer-build-outputs';h={'compiler':{'path':'/fixed/clang'}}
for r in rs:
 a=build.argv(r,root,out,h);m=build.argv(r,root,out,h,True)
 assert len(a)==10 and a[-3:]==['-o',str(out/r['workload']/'consumer'),'-lproc']
 assert m==a[:4]+['-M']+a[4:-3] and '-lproc' not in m and '-o'not in m
expected={str(i):str(i)for i in range(7)}
assert build.environment_admission(expected,expected)['execEnvironmentExact']
assert build.environment_admission(expected,expected|{'__CF_USER_TEXT_ENCODING':'x'})['runtimeExtraKeyNames']==['__CF_USER_TEXT_ENCODING']
refuses(lambda:build.environment_admission(expected,expected|{'UNKNOWN':'x'}))
for observed in [{k:v for k,v in expected.items()if k!='0'},expected|{'0':'changed'}]:refuses(lambda:build.environment_admission(expected,observed))
refuses(lambda:json.loads('{"a":1,"a":2}',object_pairs_hook=build.unique_object))
refuses(lambda:build.diagnostic(b'error: bad'))
refuses(lambda:build.diagnostic(b'bad\x00'))
assert build.diagnostic(b'warning: source diagnostic\n') and not build.diagnostic(b'')
# Model exact merged-library selection; no remote filesystem query.
sdk='/Library/Developer/CommandLineTools/SDKs/MacOSX26.2.sdk';tp=Path(sdk)/'usr/lib/libSystem.B.tbd';r={'path':str(tp),'bytes':337542,'sha256':'607d9993892c95703a0909ff06f5843058ff1ec30b08337f42ab056d9bf325ea'}
h={'sdk':sdk,'libraryPins':[r]};g={'procLibraryAlias':{'alias':sdk+'/usr/lib/libproc.tbd','canonicalTargetPin':r},'expectedDynamicLoadNames':['/usr/lib/libSystem.B.dylib']}
assert build.proc_library_selection(g,h,lambda _:tp,lambda p,q:None)
for key,value in [('alias',sdk+'/usr/lib/unknown.tbd'),('canonicalTargetPin',dict(r,sha256='0'*64))]:
 q=copy.deepcopy(g);q['procLibraryAlias'][key]=value;refuses(lambda:build.proc_library_selection(q,h,lambda _:tp,lambda p,r:None))
q=copy.deepcopy(g);q['expectedDynamicLoadNames'].append('/usr/lib/libproc.dylib');refuses(lambda:build.proc_library_selection(q,h,lambda _:tp,lambda p,r:None))
refuses(lambda:build.proc_library_selection(g,h,lambda _:tp.parent/'unknown.tbd',lambda p,r:None))
refuses(lambda:build.proc_library_selection(g,dict(h,libraryPins=[]),lambda _:tp,lambda p,r:None))
# Finite actual-word MachO command shape model; no binary execution.
import struct
name=b'/usr/lib/libSystem.B.dylib\0';z=(24+len(name)+7)//8*8;cmd=struct.pack('<6I',12,z,24,0,0,0)+name+b'\0'*(z-24-len(name));raw=struct.pack('<8I',0xfeedfacf,0x100000c,0,2,1,z,0,0)+cmd
assert build.macho(raw,g['expectedDynamicLoadNames'])==g['expectedDynamicLoadNames']
refuses(lambda:build.macho(raw,['/usr/lib/libSystem.B.dylib','/usr/lib/libproc.dylib']))
refuses(lambda:build.macho(raw.replace(b'libSystem.B',b'libUnknownX'),g['expectedDynamicLoadNames']))
for p in ['build.py','build-limit-exec.py','prepare.py','header.py','qualification.py']:
 ast.parse((D/p).read_text(),feature_version=(3,9))
print(json.dumps({'scopePositive':1,'consumerArgvPositives':19,'dependencyArgvPositives':19,'environmentPositives':2,'refusals':n,'Python39AST':5,'mergedLibraryModelPositive':1,'MachOModelPositive':1,'actualCalls':0},sort_keys=True))
