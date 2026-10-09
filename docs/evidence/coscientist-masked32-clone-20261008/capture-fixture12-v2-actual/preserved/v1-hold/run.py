"""Import inert; separately reviewed GO permits real pipe/thread fixture only."""
from pathlib import Path
import hashlib,json,sys
D=Path(__file__).resolve().parent
def receipt(p):
 p=Path(p);assert p.is_file()and not p.is_symlink();b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(Path(p).read_bytes())
def main(go_path):
 g=load(go_path);sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json')
 assert set(g)=={'status','sourcePinsSHA256','inputPinsSHA256','driverSHA256','outputRoot','maximumCaptureThreads','noRetry','reviews'}
 assert g['status']=='ROOT_GO_REAL_PIPE_CAPTURE_FIXTURE8_ONLY' and g['maximumCaptureThreads']==8 and g['noRetry']is True and g['outputRoot']==str(D/'fixture-outputs')
 assert g['sourcePinsSHA256']==receipt(D/'source-pins.json')['sha256'] and g['inputPinsSHA256']==receipt(D/'input-pins.json')['sha256'] and g['driverSHA256']==receipt(D/'run.py')['sha256']
 for name,v in sp.items():assert receipt(D/name)==v
 for path,v in ip.items():assert receipt(path)==v
 assert len(g['reviews'])==2 and len({r['path']for r in g['reviews']})==2
 for r in g['reviews']:
  assert set(r)=={'path','bytes','sha256'} and receipt(r['path'])=={k:r[k]for k in ['bytes','sha256']}
  q=load(r['path']);assert q['status']=='PASS_SOURCE_ONLY_REAL_PIPE_CAPTURE_FIXTURE8' and q['sourcePinsSHA256']==g['sourcePinsSHA256'] and q['driverSHA256']==g['driverSHA256']
 assert pr['nativeCalls']==0 and pr['processStarts']==0 and pr['groupAPICalls']==0 and pr['maximumCaptureThreads']==8
 from fixture import run_fixture
 q=run_fixture(D/'fixture-outputs')
 assert len(q['cases'])==8 and all(r['capture']['stoppedWriter']for r in q['cases'])
 (D/'fixture-outputs/completion.json').write_text(json.dumps(q,indent=2)+'\n')
if __name__=='__main__':assert len(sys.argv)==2;main(sys.argv[1])
