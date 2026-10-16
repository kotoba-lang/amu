from pathlib import Path
import json,tarfile,hashlib,importlib.util,sys,copy,argparse
sys.dont_write_bytecode=True
E=Path(__file__).resolve().parent;R=E.parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();D=args.output.resolve();D.mkdir(exist_ok=False)
def extract(a,d):
 with tarfile.open(a)as t:
  members=t.getmembers();assert all(x.isfile()and not x.issym()and not x.islnk()and not Path(x.name).is_absolute()and '..'not in Path(x.name).parts for x in members)
  d.mkdir();t.extractall(d,filter='data')
base=D/'baseline';current=D/'current';extract(R/'docs/evidence/color-neon-20261014/qualification-results.tgz',base);extract(E/'qualification-results.tgz',current)
custody=json.loads((E/'raw-custody.json').read_text());assert hashlib.sha256((E/'qualification-results.tgz').read_bytes()).hexdigest()==custody['archiveSHA256']
for x in custody['files']:
 p=current/x['path'];b=p.read_bytes();assert len(b)==x['bytes']and hashlib.sha256(b).hexdigest()==x['sha256']
sys.path.insert(0,str(E));spec=importlib.util.spec_from_file_location('portable_cw_forward',E/'native-gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
G=json.loads((current/'all39-g1-screen-v1/generated-artifacts.json').read_text());rows=[]
for e in G['images']:
 baseline=copy.deepcopy(e['baseline']);arm=copy.deepcopy(e['arm'])
 for r,d in [(baseline,base),(arm,current)]:
  for k in ['native','container','source']:
   folder='all39-g1-screen-v1/sources'if k=='source'else'all39-g1-screen-v1';p=d/folder/Path(r[k]['path']).name;r[k]['path']=str(p)
   b=p.read_bytes();assert len(b)==r[k]['bytes']and hashlib.sha256(b).hexdigest()==r[k]['sha256']
 proof=m.audit(baseline,arm);rows.append(dict(tag=e['tag'],changed=proof['changed'],loads=proof.get('forwardedLoads',0),narrows=proof.get('omittedNarrow',0)))
assert len(rows)==39 and sum(x['changed']for x in rows)==2
r=dict(status='PASS_REPOSITORY_ONLY_PORTABLE_PARENT_AND_CURRENT_ARCHIVES_ALL39_NATIVE_PROOFS',programImages=39,sourceOnlyPythonProof=True,compilerOrGuestOrNetworkCalls=0,sourceSnapshotsFromRepositoryArchivesOnly=True,rows=rows)
(D/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
