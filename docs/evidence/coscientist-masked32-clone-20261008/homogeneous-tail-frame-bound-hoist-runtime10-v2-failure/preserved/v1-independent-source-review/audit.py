"""SOURCE/read-only inventories and injected pure controls; never native/main."""
from pathlib import Path
import json,hashlib,stat,ast,sys,runpy,io,contextlib,importlib.util,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'tc-hft-compose511-bound-hoist-original-ns-runtime10-source-v1-20261009';Q=Path(__file__).parent

def pin(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=33554432;x=p.read_bytes();z=p.lstat();assert(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return {'bytes':len(x),'sha256':hashlib.sha256(x).hexdigest()}
def check():
 sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());assert len(sp)==21 and len(ip)==256 and sum(r['bytes']for r in ip.values())==20913901
 for n,v in sp.items():assert pin(D/n)==v,n
 for n,v in ip.items():assert pin(n)==v,n
 assert pin(D/'source-pins.json')['sha256']=='f9fcd266bbd9baad4919af88dd0d2e2748ad884d640baae1556fe0354ee0d627'
 assert pin(D/'input-pins.json')['sha256']=='e480c9d0d8133e62127c753eb90185fc6c72811adcdc4126edb5a0201c65a19d'
 return sp,ip
sp,ip=check();pr=json.loads((D/'preregistration.json').read_bytes());assert pin(D/'run.py')['sha256']=='68573404130ceb322738f55c89ed80490c31faf31a604e593aa78df4ed71ee88';assert pin(D/'preregistration.json')['sha256']=='340a51a978dc48fe4f801b5c1cfe6aa6ec5b73c9f55949bf3ac8ba9e865b8093'
components=json.loads((D/'component-binding.json').read_bytes())['components'];assert len(components)==10
for n,r in components.items():assert pin(r['path'])=={k:r[k]for k in ['bytes','sha256']}==pin(D/n)
for n in sp:
 if n.endswith('.py'):ast.parse((D/n).read_bytes())
sys.path.insert(0,str(D));spec=importlib.util.spec_from_file_location('pure_test',D/'pure-controls.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);controls=mod.controls();assert controls==json.loads((D/'pure-controls.json').read_bytes())
buffer=io.StringIO()
with contextlib.redirect_stdout(buffer):runpy.run_path(str(D/'wrapper-seal-controls.py'),run_name='review_injected_wrappers')
wrappers=json.loads(buffer.getvalue());assert wrappers==json.loads((D/'wrapper-seal-controls-result.json').read_bytes())
# Primary nonembedded loader grammar independently binds ten typed cases.
src=Path(pr['loaderGrammarSource']['path']).read_text()if 'loaderGrammarSource'in pr else Path('/Users/junkawasaki/github/wt/amu-seed17/tools/kexe_loader.c').read_text();main=src[src.index('int main(int argc, char **argv) {'):];assert main.index('argc = i;')<main.index('argc != (int)(6 + arity)) return 2;')<main.index('FILE *file = fopen(argv[1], "rb");')
assert len(pr['cases'])==10 and [c['profile']for c in pr['cases']]==[n for n in [0,1,2,17,32]for _ in range(2)]
for i,c in enumerate(pr['cases']):
 assert len(c['nativeArgv'])==7 and c['nativeArgv'][2:6]==['36440','1','aarch64','-']and c['nativeArgv'][6]==str(c['profile'])and '--'not in c['nativeArgv'];assert c['arm']==['OFF','ON'][i%2]
# Recompute actual full native/certificate association without relying on report status.
off=Path(pr['images']['OFF']['native']['path']).read_bytes();on=Path(pr['images']['ON']['native']['path']).read_bytes();cert=json.loads(Path(pr['emissionCertificate']['path']).read_bytes());assert len(off)==len(on)==37520
changes=[{'wordIndex':1+i//4,'physicalByteOffset':i,'before':int.from_bytes(off[i:i+4],'little'),'after':int.from_bytes(on[i:i+4],'little')}for i in range(0,len(off),4)if off[i:i+4]!=on[i:i+4]];assert changes==cert['changes']and len(changes)==492
assert hashlib.sha256(on).hexdigest()=='f00efff199abd9795620e0a13be6695fb05de6d181fe080343b89ceae3703578'
for arm in ['OFF','ON']:
 raw=Path(pr['images'][arm]['container']['path']).read_bytes();cut=raw.index(b'\n\n')+2;assert raw[cut:]==Path(pr['images'][arm]['native']['path']).read_bytes()and b'batch 36440 1\n'in raw[:cut]
 gs=json.loads((D/'go-schema.json').read_bytes());assert len(gs['exactKeys'])==len(set(gs['exactKeys']))==19 and gs['exactKeys'].count('runtimeGuestAuthorized')==1
check()
r={'status':pr['sourceReviewStatus'],'subject':str(D),'scope':'Independent SOURCE runtime10 harness review; reviewer authored bound-hoist algorithm but not Dense runtime harness. Actual code/emission and conditional architecture proof are separately bound, not independently requalified here.','sourcePinsSHA256':pin(D/'source-pins.json')['sha256'],'inputPinsSHA256':pin(D/'input-pins.json')['sha256'],'driverSHA256':pin(D/'run.py')['sha256'],'preregistrationSHA256':pin(D/'preregistration.json')['sha256'],'sourceFilesVerified':21,'inputFilesVerified':256,'inputLogicalBytes':20913901,'allPinsRereadAfterControls':True,'byteExactPriorOperationalComponents':list(components),'pureControls':controls,'wholeWrapperControls':wrappers,'reviewed':['Current OFF7618 whole source/images and fresh actual e810 G1 full compiler/source plus NS actual492word/container/ownbatch36440arity1.','Original unchanged five NS profiles0/1/2/17/32, C95 result-only oracle, adjacent10 OFF/ON; primary loader no-- typed argc7 before fopen independently reread.','Strict result/fuel/all17arena/exit/raw parser and pair equality; original fuel16777216, zero caps and exact17 arena/env, CPU30hard31/outer30/reap30.','Exact19 unique GO keys/runtimeGuestAuthorized once; two distinct reviews, current proof matrix/fixture, immutable seals/whole artifact/source binding, fresh namespace/call11 beforeAPI refusal.','Ten qualified operational components byte-identical, strict unknown PID/race refusal retained; finite700s campaign and60s before each call, bounded metadata/raw/sample/FD ownership and valid-last terminal.'],'findings':[],'limitations':['No GO/native/guest/FD/thread/kernel/network/product/frozen-write operations.','New runtime10 is unexecuted; actual emission/source binding is not functional or general private-frame ABI proof.','Strict sequential physical memory sampler can refuse ephemeral unknown member; no relaxation or retry, no hardpeak/OS completeness claim.','No C timing/full19/fixedpoint/general composition/adoption qualification.'],'operations':{'native':0,'FD':0,'thread':0,'kernel':0,'network':0,'frozenWrites':0},'audit':dict(path=str(Q/'audit.py'),**pin(Q/'audit.py'))}
(Q/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(Q/'report.json'),**pin(Q/'report.json'))))
