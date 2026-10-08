from pathlib import Path
import json,hashlib,ast,importlib.util,sys
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-fuel-scalar-dag-compiler-build4-plan-v2-width';O=Path(__file__).resolve().parent;inputs={}
def pin(p):
 assert p.is_file()and not p.is_symlink();h=hashlib.sha256();n=0
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
 return {'bytes':n,'sha256':h.hexdigest()}
def verify(p,v=None):
 z=pin(p)
 if v is not None:assert z==v,str(p)
 inputs[str(p)]=z;return z
def load(p):return json.loads(p.read_text())
assert verify(D/'source-pins.json')['sha256']=='cc57c708de8f8d4618f1f769102837a43f6c5d905a50b6fb260444f86b8c7db0'
assert verify(D/'source-report.json')['sha256']=='39afd2137825a089953edc86fa72494f9214a090e8c0b7c0c45956f99396532f'
for n,v in load(D/'source-pins.json').items():verify(D/n,v)
pr=load(D/'preregistration.json');ip=load(D/'input-pins.json')
assert len(ip)==pr['exactInputFiles']==1700 and sum(v['bytes']for v in ip.values())==pr['exactInputLogicalBytes']==362671770
assert len(ip)<=pr['maximumInputFiles']==2048 and sum(v['bytes']for v in ip.values())<=pr['maximumInputLogicalBytes']==402653184
for p,v in ip.items():verify(Path(p),v)
assert pin(D/'input-pins.json')['sha256']==pr['inputPinsSHA256']
source=Path(pr['sourceDirectory']);assert verify(source/'source-pins.json')['sha256']==pr['sourcePinsSHA256']=='fbdd649d3964b76d3d91b915065c6133f137954557d60b54df4e47b85ce6a7ba'
for n,v in load(source/'source-pins.json').items():verify(source/n,v)
assert verify(Path(pr['producer']))['sha256']=='5404f22ac455d66c1295a4ad0d90987722262b86b1aacd9bc9d69c8ad5cafd69'
assert verify(Path(pr['loader']))['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f'
assert load(Path(pr['actualProducerProof']))['status']==pr['actualProducerProofStatus']and load(Path(pr['actualProducerProof']))['G2G3G4WholeContainerAndNativeByteFixedpoint']
assert load(Path(pr['actualLoaderProof']))['status']==pr['actualLoaderProofStatus']
v=pr['emitterIndependentReview'];verify(Path(v['path']),{k:v[k]for k in ('bytes','sha256')});assert load(Path(v['path']))['status']==pr['sourceReviewStatus']=='PASS_SOURCE_ONLY_EXPERIMENTAL_FUEL_PRESERVING_DAG'
assert pr['resourceAccountingAddendum']=={'weightedBodyMaximum':96,'callerOverheadIncludingVclearMaximum':40,'totalMaximum':136,'reserve':192,'sourceHelperOrAdmissionChanges':False}
old=W/'vector-fuel-scalar-dag-compiler-build4-plan-v1-width';assert (old/'run.py').read_bytes()==(D/'run.py').read_bytes()
assert not(old/'run-outputs').exists()and not(D/'run-outputs').exists()
spec=importlib.util.spec_from_file_location('inert_build4',D/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
payload=b'\x01\x02\x03\x04\x05';assert m.kseed(b'KSEED1 5 1\nmain 0 0\n\n'+payload)==payload
for bad in [b'KSEED1 4 1\nmain 0 0\n\n'+payload,b'KSEED1 5 1\nmain 4 0\n\n'+payload,b'KSEED1 5 2\nmain 0 0\n\n'+payload]:
 try:m.kseed(bad)
 except AssertionError:pass
 else:raise AssertionError('bad header accepted')
zero=('KEXE_ARENA_USE {'+' '.join(':'+f+' 0'for f in m.FIELDS)+'}\n').encode();assert len(m.FIELDS)==17 and m.counters(zero)['status']=='valid'
assert m.counters(zero+zero)['status']=='unavailable-or-invalid'and m.counters(zero+b'error\n')['status']=='unavailable-or-invalid'
assert m.kseed(Path(pr['OFFBaselineContainer']).read_bytes())==Path(pr['OFFBaselineNative']).read_bytes()
src=(D/'run.py').read_text();ast.parse(src)
assert src.index('OFF_WHOLE_BASELINE_CONTAINER_BEFORE_EXTRACT')<src.index("raw=call(arm+'-extract'")
assert "for arm,src in [('OFF',pr['parentSource']),('ON',pr['ONSource'])]"in src
assert "argv=[pr['loader'],pr['producer']"in src and "subprocess.Popen(argv,cwd=O,env=env"in src
assert src.index("save(O/'attempts.json',rows)",src.index("r.update(state="))<src.index("counterObservation",src.index("r.update(state="))
(O/'input-pins.json').write_text(json.dumps(inputs,indent=2)+'\n');(O/'pure-controls.json').write_text(json.dumps({'status':'PASS_INDEPENDENT_PURE_BUILD4_V2_INPUT_HEADER_COUNTER_CONTROLS_ONLY','closureFiles':1700,'closureBytes':362671770,'positiveHeader':1,'rejectedHeaders':3,'counterPositive':1,'counterNegative':2,'OFFWholePayloadIdentity':True,'runImportedInertOnly':True,'runMainExecuted':False,'nativeCalls':0,'SSHCalls':0,'subprocessCalls':0},indent=2)+'\n');print('PASS SOURCE controls, native/SSH0')
