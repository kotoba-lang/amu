from pathlib import Path
import json,hashlib,copy
W=Path(__file__).parent;D=W/'all39-g1-screen-v1';D.mkdir();(D/'sources').mkdir()
old=W.parent/'seed-copy-chain-forward-20261014/all39-g1-screen-v1'
P=json.loads((old/'PLAN.json').read_text());G=json.loads((old/'generated-artifacts.json').read_text())
def pin(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
producer=W/'compiler-only-v1/artifacts/candidate.bin';container=producer.with_suffix('.kseed');assert producer.exists()
entries=[]
for e in G['images']:
 src=D/'sources'/Path(e['source']['path']).name;src.write_bytes(Path(e['source']['path']).read_bytes())
 r=copy.deepcopy(e);r.pop('arm');r['baseline']=e['arm'];r['source']=pin(src);r['reused']=False;entries.append(r)
P.update(status='FROZEN_NATIVE_G1_SCREEN_NOT_FIXEDPOINT_OR_ADOPTED',entries=entries,stableProducer=pin(producer),stableProducerContainer=pin(container),actualProducerStage='G1_CURRENT_MAIN_BASE_NATIVE_CANDIDATE',baseProduct='f7c3bd84fe2cdf868598980d781b1616f1c48109',expectedChangedImages='Certified linear copy-chain available values remove repeated item loads and idempotent sign narrows; original stores, guards, fuel and cold path retained',candidate=pin(W/'candidate.kotoba'),selfhostReportExpected='PENDING_G1_SCREEN_FIRST')
P['environment'].update(KEXE_CAP_RESOURCES_35=str(D),TMPDIR=str(D))
P['inputs']=[P['stableProducer'],P['stableProducerContainer'],P['loader'],P['candidate']]+[e['source']for e in entries]
(D/'PLAN.json').write_text(json.dumps(P,indent=2)+'\n')
s=(old/'run-generation.py').read_text();s=s.replace('print(json.dumps(R,indent=2),flush=True)','print(R["status"],flush=True)')
(D/'run-generation.py').write_text(s)
(D/'controller-pins.json').write_text(json.dumps(dict(files=[pin(D/'PLAN.json'),pin(D/'run-generation.py')]),indent=2)+'\n')
print('prepared full39 native screen')
