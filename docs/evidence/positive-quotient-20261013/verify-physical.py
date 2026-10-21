"""Verify preserved raw custody and replay all39 physical gates; no native execution."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,tarfile
E=Path(__file__).resolve().parent
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();D=a.output.resolve();D.mkdir(parents=True,exist_ok=False)
 custody=json.loads((E/'raw-custody.json').read_text());rows=custody['files']
 with tarfile.open(E/'qualification-results.tgz')as t:
  members=t.getmembers();assert len(members)==len(rows)
  assert {m.name for m in members}=={r['path']for r in rows}
  assert all(m.isfile()and not m.issym()and not m.islnk()and not Path(m.name).is_absolute()and '..'not in Path(m.name).parts for m in members)
  for r in rows:
   b=t.extractfile(r['path']).read();assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256']
  t.extractall(D,filter='data')
 s=importlib.util.spec_from_file_location('positive_physical',E/'native-gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 images=copy.deepcopy(json.loads((E/'portable-artifacts.json').read_text())['images']);reports=[]
 for e in images:
  for side in['baseline','arm']:
   for key in['source','native','container']:
    row=e[side][key];p=(D/row['path']).resolve();assert p.is_relative_to(D);row['path']=str(p)
  r=m.audit(e['baseline'],e['arm']);reports.append(dict(tag=e['tag'],status=r['status'],changed=r['changed']))
  (D/(e['tag']+'-replay.json')).write_text(json.dumps(r,indent=2)+'\n')
 assert len(reports)==39 and sum(x['changed']for x in reports)==2
 report=dict(status='PASS_RAW_CUSTODY_ALL39_NATIVE_PHYSICAL_REPLAY',files=len(rows),images=39,changed=2,rows=reports,nativeExecution=False,performanceMeasured=False)
 (D/'replay-report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
