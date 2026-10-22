from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,tempfile
E=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(E/'timing-results.tgz')==load(E/'timing-archive-manifest.json')['sha256']
with tempfile.TemporaryDirectory(prefix='amu-clone-timing-replay-') as tmp:
 W=Path(tmp);d=W/'remote-evidence';d.mkdir()
 with tarfile.open(E/'timing-results.tgz') as t:t.extractall(d,filter='data')
 src=(E/'timing-audit.py').read_text().replace("w=Path('/private/tmp/amu-private-length-clones-20261006')",'w=Path('+repr(str(W))+')')
 assert str(W) in src
 (W/'audit.py').write_text(src)
 q=subprocess.run([sys.executable,str(W/'audit.py')],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 actual=load(W/'timing-audit.json');assert actual==load(E/'timing-audit.json')
 result={'status':'PASS extracted independent native product/candidate/C timing replay','acceptedTriples':actual['acceptedTriples'],'qualifiedImprovements':actual['qualifiedImprovements'],'qualifiedRegressions':actual['qualifiedRegressions'],'performanceAllowsFurtherAdoptionGates':actual['performanceAllowsFurtherAdoptionGates'],'freshTimings':0,'officialEmbenchScore':False,'productPromoted':False,'all19GoalAchieved':False}
 (E/'timing-replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
