from pathlib import Path
import json,stat,hashlib,struct,sys,ast
D=Path('/Users/junkawasaki/github/workspaces/codex/tc-homogeneous-tail-frame-native4-source-v2-20261009');O=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(D))
def rec(p):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode)and not p.is_symlink();b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());pr=json.loads((D/'preregistration.json').read_bytes())
for n,r in sp.items():assert rec(D/n)=={k:r[k]for k in ['bytes','sha256']}
for p,r in ip.items():assert rec(p)=={k:r[k]for k in ['bytes','sha256']}
assert len(ip)==2885 and sum(x['bytes']for x in ip.values())==451777835
fr=json.loads((D/'freeze.json').read_bytes())
a=json.loads((D/'source-assembly.json').read_bytes());mods=a['modules'];pins=a['modulePins'];assert len(mods)==len(pins)==16 and mods.count('seed/41-a64gen.kotoba')==1
candidate=b''.join(Path(a['candidate41']['path']if n=='seed/41-a64gen.kotoba'else r['path']).read_bytes()+b'\n'for n,r in zip(mods,pins));ordinary=b''.join(Path(a['ordinaryCandidate41']['path']if n=='seed/41-a64gen.kotoba'else r['path']).read_bytes()+b'\n'for n,r in zip(mods,pins));assert candidate==(D/'candidate-current16.kotoba').read_bytes()and ordinary==(D/'ordinary-current16.kotoba').read_bytes();assert rec(D/'ordinary-current16.kotoba')['sha256']=='94fe39401f5f0a1120b12b2d17bf000d14a54c9c68e1f8976b8b0ced8794f199'
assert rec(Path(a['candidate41']['path']))['sha256']=='16a6e878f516cd4617de2be2c95224633ac1814be9849e226b76024d44fd811b'
assert (D/'nsichneu.kotoba').read_bytes()==Path(pr['entries'][0]['source']['path']).read_bytes()
expanded=Path(pr['expandedOriginalSource']['path']).read_bytes();orig=(D/'nsichneu.kotoba').read_bytes();assert expanded==orig+b'\n'+b'(defn- rem [a :i64 b :i64] :i64 (- a (* b (quot a b))))\n'and len(expanded)==30443 and pr['typedOriginalFNCount']==267 and pr['typedOriginalFNAccounting']==dict(null=1,diskDefns=265,implicitRem=1)
base=Path('/Users/junkawasaki/github/workspaces/codex/published-mode2-x8-vector-statemate6-source-v2-20261009');same=['capture.py','integration.py','controller.py','typed-adapter.py','artifact_admission.py','runtime.py'];assert all((D/n).read_bytes()==(base/n).read_bytes()for n in same)
b=(base/'native-call.py').read_text();expected=b.replace("need(len(rows)<36 and pr['cases'][len(rows)]==case,'fixed ordered OFF18compile36 no retry')","need(len(rows)<4 and pr['cases'][len(rows)]==case,'fixed ordered HFTnative4 no retry')");assert expected==(D/'native-call.py').read_text()
# Recompute controls without frozen result writer.
s=(D/'source-controls.py').read_text();s=s[:s.index("(D/'source-controls.json').write_text")];g={'__file__':str(D/'source-controls.py'),'__name__':'independent_pure_no_writer'};exec(compile(s,str(D/'source-controls.py'),'exec'),g);assert g['result']==json.loads((D/'source-controls.json').read_bytes())
from run import container
payload,exports=container(Path(pr['candidateContainer']).read_bytes());assert payload==Path(pr['producer']).read_bytes()and exports==[('main',0,0)]and rec(pr['producer'])['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'
ec=json.loads((D/'emission-certificate.json').read_bytes());old=Path(ec['originalOffContainer']['path']).read_bytes();oldpayload,oldexports=container(old);cut=len(old)-len(oldpayload);new=bytearray(old);changes=[]
for x in ec['changes']:
 assert x['physicalByteOffset']==4*(x['wordIndex']-1)
 p=cut+x['physicalByteOffset'];assert struct.unpack_from('<I',old,p)[0]==x['before'];struct.pack_into('<I',new,p,x['after']);changes.append((x['wordIndex'],hex(x['before']),hex(x['after'])))
np,ne=container(bytes(new));assert ne==oldexports and len(np)==ec['expectedWholeNativeBytes']and hashlib.sha256(np).hexdigest()==ec['expectedWholeNativeSHA256']and hashlib.sha256(new).hexdigest()==ec['expectedContainerSHA256'];assert len(changes)==4
# Decode branch target adjustment independently; ordinary tail bypasses target5 prefix words.
before,after=ec['changes'][-1]['before'],ec['changes'][-1]['after'];assert before>>26==after>>26==5 and (after&0x3ffffff)-(before&0x3ffffff)==5;assert ec['changes'][0]['after']==0xf94007be and [x['after']for x in ec['changes'][1:3]]==[0xd503201f]*2
assert not Path(pr['freshOutputRoot']).exists()
summary={'sourceFiles':len(sp),'sourceLogicalBytes':sum(x['bytes']for x in sp.values()),'inputFiles':len(ip),'inputLogicalBytes':sum(x['bytes']for x in ip.values()),'sourcePins':rec(D/'source-pins.json'),'inputPins':rec(D/'input-pins.json'),'driver':rec(D/'run.py'),'preregistration':rec(D/'preregistration.json'),'freeze':rec(D/'freeze.json'),'pureControls':g['result'],'certificate':ec,'independentDecodedChanges':changes,'sameComponentHashes':{n:rec(D/n)['sha256']for n in same},'fixedCases':pr['cases'],'freshOutputAbsent':True};(O/'checks.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k in ['sourceFiles','sourceLogicalBytes','inputFiles','inputLogicalBytes','sourcePins','inputPins','driver','preregistration','freeze']}))
