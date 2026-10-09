"""Saved SOURCE/pure mocked controls only. Never calls native/main/FD/thread APIs."""
from pathlib import Path
import json,hashlib,stat,ast,runpy,sys,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-homogeneous-tail-frame-compose511-bound-hoist-native4-source-v1-20261009';Q=Path(__file__).parent

def receipt(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=33554432
 b=p.read_bytes();z=p.lstat();assert(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def check():
 sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes())
 assert len(sp)==25 and len(ip)==121 and sum(v['bytes']for v in ip.values())==9999704
 for n,v in sp.items():assert receipt(D/n)==v,n
 for n,v in ip.items():assert receipt(n)==v,n
 assert receipt(D/'source-pins.json')['sha256']=='c37e16144b1d7753ee8213f36c04d5586650e77e71cc577f7c3f08563bb2aab1'
 assert receipt(D/'input-pins.json')['sha256']=='ca16b4149b1cd43ad777cca8e3ec8900fcfb3621c151731e7d39dc707a66e716'
 return sp,ip
sp,ip=check();pr=json.loads((D/'preregistration.json').read_bytes());freeze=json.loads((D/'freeze.json').read_bytes())
assert receipt(D/'run.py')['sha256']=='62c674116c558b6fef7942b640ddc814feaec7d4e905888a7fa2c7a728d31ee5'
assert receipt(D/'preregistration.json')['sha256']=='148bf159ed21b072b84a53cd1012deca85b07ae9854f34e20a015960b2721f8a'
assert pr['maximumLoaderCalls']==4 and pr['maximumGuestWorkloadExecutions']==0 and len(pr['cases'])==4
assert [c['label']for c in pr['cases']]==['G1-compile','G1-extract','nsichneu-compile','nsichneu-extract']
assert len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='off'and pr['environment']['KEXE_COMMAND']=='1'
assert pr['maximumInputFiles']==256 and pr['maximumInputLogicalBytes']==33554432 and pr['maximumCampaignSeconds']==7500 and pr['requiredRemainingBeforeChildSeconds']==1840
components=json.loads((D/'component-binding.json').read_bytes())['components'];assert len(components)==8
for n,v in components.items():assert receipt(v['path'])=={k:v[k]for k in ['bytes','sha256']}==receipt(D/n)
for n in sp:
 if n.endswith('.py'):ast.parse((D/n).read_bytes())
# Registered SOURCE scripts have no operational __main__ call; only mocked/read
# controls execute. Intercept their exact two output writes, compare frozen JSON.
writes={};old=Path.write_text
def writer(p,text,*a,**kw):
 assert p in [D/'source-controls.json',D/'producer-controls-result.json'];assert text.encode()==p.read_bytes();writes[str(p)]=len(text);return len(text)
sys.path.insert(0,str(D))
try:
 Path.write_text=writer
 for name in ['source-controls.py','producer-controls.py']:runpy.run_path(str(D/name),run_name='review_pure_controls')
finally:Path.write_text=old
assert len(writes)==2
# Independent full-byte derivation from saved ordinary container, not candidate
# host-produced checksum. Header/exports and every unlisted byte are unchanged.
ec=json.loads((D/'emission-certificate.json').read_bytes());original=Path(ec['originalOffContainer']['path']).read_bytes();cut=original.index(b'\n\n')+2;new=bytearray(original);seen=set()
assert len(ec['changes'])==492
for c in ec['changes']:
 assert c['physicalByteOffset']%4==0 and c['physicalByteOffset']not in seen;seen.add(c['physicalByteOffset']);off=cut+c['physicalByteOffset'];assert struct.unpack_from('<I',original,off)[0]==c['before'];struct.pack_into('<I',new,off,c['after'])
assert hashlib.sha256(new).hexdigest()==ec['expectedContainerSHA256']=='16a4eba2186ff4a02f97134488e9950a9803a1f27ed077346bcc7b63d7c06eae'
assert hashlib.sha256(new[cut:]).hexdigest()==ec['expectedWholeNativeSHA256']=='f00efff199abd9795620e0a13be6695fb05de6d181fe080343b89ceae3703578'
assert new[:cut]==original[:cut] and len(new)==len(original)==37591
# Exact GO declared key set agrees with driver literal, duplicate-free.
gs=json.loads((D/'go-schema.json').read_bytes());tree=ast.parse((D/'run.py').read_bytes());sets=[ast.literal_eval(n)for n in ast.walk(tree)if isinstance(n,ast.Set)and all(isinstance(e,ast.Constant)for e in n.elts)];assert set(gs['exactKeys'])in sets and len(gs['exactKeys'])==len(set(gs['exactKeys']))
check()
report={'status':pr['sourceReviewStatus'],'scope':'Independent SOURCE review of Dense-authored native4 harness only. Reviewer authored bound-hoist algorithm; its conditional architecture admission is supplied by separate root/Dense reviews, not independently certified here.','subject':str(D),'sourcePinsSHA256':receipt(D/'source-pins.json')['sha256'],'inputPinsSHA256':receipt(D/'input-pins.json')['sha256'],'driverSHA256':receipt(D/'run.py')['sha256'],'preregistrationSHA256':receipt(D/'preregistration.json')['sha256'],'sourceFilesVerified':25,'inputFilesVerified':121,'inputLogicalBytes':9999704,'allPinsRereadAfterControls':True,'qualifiedComponentsByteIdentical':list(components),'pureControls':{'source':json.loads((D/'source-controls.json').read_bytes()),'producer':json.loads((D/'producer-controls-result.json').read_bytes()),'frozenWritesInterceptedAndByteCompared':2},'manualFindings':[],'reviewedContracts':['Exact four ordered compiler commands; primary loader arity0 -- command grammar; guest workload calls zero.','Current7618 whole main0 native/container/source lineage; canonical current16 only41 replacement and two independent conditional SOURCE architecture bindings.','Fresh G1 two-closed/admitted-call currentGO receipt before G1 NS compilation; full payload/own symbol export ABI; no arbitrary producer, input or output paths.','Prospective 123edges/492word whole original NS certificate, all header/export/other bytes identical. This is not actual new emission.','Exact17 supplied/native environment; named finite CPU1800/1801 FILE64MiB and sampled physicalFootprint4GiB policy; original eight qualified controller/capture/typed/resource components byteexact.','Fresh noRetry namespace, finite campaign7500s, required1840s before each call, strict artifact admission/unknownPID refusal, immutable seals before callbacks, all four closure then terminal valid-last report.'],'limitations':['SOURCE/pure controls only; no GO/native/build/guest or kernel operations.','New compiler syntax/type/selfhost and actual 492word emission pending; no compiler fuel/arena parity claim.','Existing sequential sampled memory/race refusals and uncertain cleanup limits are preserved; no universal OS hardpeak/process or ABI proof.','No functional runtime/full19/C timing/fixedpoint/adoption qualification.'],'operations':{'native':0,'compiler':0,'FD':0,'threadStart':0,'kernelProcess':0,'network':0,'productEdits':0,'frozenWrites':0},'audit':dict(path=str(Q/'audit.py'),**receipt(Q/'audit.py'))}
(Q/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(path=str(Q/'report.json'),**receipt(Q/'report.json'))))
