from pathlib import Path
import json,tarfile,hashlib,importlib.util,sys,copy,argparse
sys.dont_write_bytecode=True
E=Path(__file__).resolve().parent;R=E.parents[2]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();D=a.output.resolve();D.mkdir(exist_ok=False)
def extract(e,d,archiveName="qualification-results.tgz",custodyName="raw-custody.json"):
 a=e/archiveName;c=json.loads((e/custodyName).read_text());assert hashlib.sha256(a.read_bytes()).hexdigest()==c['archiveSHA256']
 with tarfile.open(a)as t:
  ms=t.getmembers();assert all(x.isfile()and not x.issym()and not x.islnk()and not Path(x.name).is_absolute()and '..'not in Path(x.name).parts for x in ms);d.mkdir();t.extractall(d,filter='data')
 for x in c['files']:
  b=(d/x['path']).read_bytes();assert len(b)==x['bytes']and hashlib.sha256(b).hexdigest()==x['sha256']
base=D/'baseline';current=D/'current';extract(R/'docs/evidence/copy-chain-forward-20261014',base);extract(E,current)
sys.path.insert(0,str(E));s=importlib.util.spec_from_file_location('portable_cw48',E/'native-gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def check(r):
 for k in ['native','container','source']:
  b=Path(r[k]['path']).read_bytes();assert len(b)==r[k]['bytes']and hashlib.sha256(b).hexdigest()==r[k]['sha256']
G=json.loads((current/'all39-g1-screen-v1/generated-artifacts.json').read_text());rows=[]
for x in G['images']:
 off=copy.deepcopy(x['baseline']);on=copy.deepcopy(x['arm'])
 for r,d in [(off,base),(on,current)]:
  for k in ['native','container','source']:
   folder='all39-g1-screen-v1/sources'if k=='source'else'all39-g1-screen-v1';r[k]['path']=str(d/folder/Path(r[k]['path']).name)
  check(r)
 proof=m.audit(off,on,current);rows.append(dict(tag=x['tag'],changed=proof['changed'],extendedBlocks=len(proof.get('proofs',[]))))
assert len(rows)==39 and sum(x['changed']for x in rows)==2
arms=json.loads((current/'generic-controls-v1/arms.json').read_text())
for tag,r in arms.items():
 for k in ['source','native','container']:r[k]['path']=str(current/'generic-controls-v1'/Path(r[k]['path']).name)
 check(r)
q=m.audit(arms['OFF'],arms['ON'],current);assert q['changed']and len(q['proofs'])==1254
revision=D/'review-revision';extract(E,revision,'review-fixes-results.tgz','review-fixes-raw-custody.json')
newG=json.loads((revision/'all39-g1-screen-v1/generated-artifacts.json').read_text());assert len(newG['images'])==39
for x in newG['images']:
 original=next(z for z in G['images']if z['tag']==x['tag'])
 for k in ['source','native','container']:
  folder='all39-g1-screen-v1/sources'if k=='source'else'all39-g1-screen-v1';newPath=revision/folder/Path(x['arm'][k]['path']).name;oldPath=current/folder/Path(original['arm'][k]['path']).name
  blob=newPath.read_bytes();assert blob==oldPath.read_bytes()and hashlib.sha256(blob).hexdigest()==x['arm'][k]['sha256']==original['arm'][k]['sha256']
for f in ['ON.bin','ON.kseed','renamed-copy-chain.kotoba']:assert(revision/'generic-identity-v1'/f).read_bytes()==(current/'generic-controls-v1'/f).read_bytes()
unit=json.loads((revision/'headroom-unit-v1/report.json').read_text());assert len(unit['rows'])==12 and all(x['actual']==x['expected']==(48 if x['remainingWords']>=512 else 16)for x in unit['rows'])
receipt=json.loads((R/'seed/adoption-20261012.json').read_text());newNative=hashlib.sha256((revision/'selfbuild-v1/artifacts/G4.bin').read_bytes()).hexdigest();assert newNative==receipt['nativeImageSHA256']==hashlib.sha256((R/'seed/bootstrap/adopted-20261012.bin').read_bytes()).hexdigest()
assert hashlib.sha256((revision/'candidate.kotoba').read_bytes()).hexdigest()==receipt['sourceUnitySHA256']
out=dict(status='PASS_CHECKOUT_RELATIVE_PARENT_CURRENT_ARCHIVE_FULL39_AND_GENERIC_BOTH_SIDES_WHOLE_CODE_PROOFS',rows=rows,genericBlocks=1254,reviewFixWhole39AndGenericIdentities=True,headroomBoundaryCases=12,currentCompilerSHA256=newNative,compilerGuestTimingNetworkCalls=0,sourceSnapshotsFromRepositoryArchivesOnly=True)
(D/'report.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
