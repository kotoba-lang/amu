from pathlib import Path
import json,hashlib,sys,runpy,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-native4-source-v2-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent;sys.path.insert(0,str(S));m=runpy.run_path(str(S/'run.py'));pr=m['load'](S/'preregistration.json');sp=m['load'](S/'source-pins.json');ip=m['load'](S/'input-pins.json')
for n,r in sp.items():m['pin'](S/n,r)
for p,r in ip.items():m['pin'](p,r)
a=m['load'](O/'attempts.json');t=m['load'](O/'terminal.json');assert len(a)==4 and t=={'calls':4,'closed':True,'failure':False}
from artifact_admission import accept_artifact_observation
for i,r in enumerate(a):
 assert r['index']==i+1 and r['nativeArgv']==pr['cases'][i]['nativeArgv']and r['state']=='terminal'and r['returncode']==0 and r['failure']is None and not r['waitUncertain']and r['captureStopAcknowledged'];assert accept_artifact_observation(r['controllerObservation'])
 for n in ['stdout','stderr']:assert m['receipt'](O/(r['label']+'.'+n))==r[n]
artifacts=[]
for name,symbol,arity in [('G1','main',0),('nsichneu','batch',1)]:
 b=(O/(name+'.bin')).read_bytes();packed=(O/(name+'.kseed')).read_bytes();payload,exports=m['container'](packed);assert b==payload and any(e[0]==symbol and e[2]==arity for e in exports);artifacts.append(dict(name=name,native=m['receipt'](O/(name+'.bin')),container=m['receipt'](O/(name+'.kseed')),exports=exports))
ec=m['load'](S/'emission-certificate.json');old=m['pin'](ec['originalOffContainer']['path'],ec['originalOffContainer']).read_bytes();raw=(O/'nsichneu.kseed').read_bytes();cut=old.index(b'\n\n')+2;changes=[];expected=bytearray(old)
for x in ec['changes']:assert struct.unpack_from('<I',old,cut+x['physicalByteOffset'])[0]==x['before'];struct.pack_into('<I',expected,cut+x['physicalByteOffset'],x['after']);changes.append(x)
assert raw==expected and m['receipt'](O/'nsichneu.kseed')['sha256']==ec['expectedContainerSHA256']
q=dict(status='PASS_ROOT_SAVED_HFT_V3_NATIVE4_V2_WHOLE_FOUR_WORD_EMISSION_ONLY',sourcePinsSHA256=m['receipt'](S/'source-pins.json')['sha256'],closedCompilerCalls=4,finiteSamples=sum(r['memorySamples']for r in a),perCallStrictMemoryPolicy=[r['controllerObservation']['strictOldMemoryPolicyPassed']for r in a],artifacts=artifacts,wholeNSExceptFourWordsUnchanged=True,changes=changes,guestRuntimeExecuted=False,generalFrameABIQualified=False,performanceQualified=False,C2=False,notes=['First build uses existing typed termination-gap admission; three others strict sampled.','Direct waits closed0; no hard physical-memory peak claim.','Native source type/word binding only; full fuel/trap/17arena/fixedpoint/full19/C timing pending.','Old encoder-name failure preserved; no old-call retry.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
p=W/'compute-address-continuation-20261008-root/checkpoint.json';c=json.loads(p.read_bytes());c['currentHomogeneousFrameCandidate']={'source':str(W/'tc-homogeneous-tail-frame-candidate-source-v3-20261009'),'native4Source':str(S),'state':'V3_CLOSED0_ONCE4_EXACT_FOUR_WORD_EMISSION_INDEPENDENT_PENDING','native4GO':str(W/'tc-homogeneous-tail-frame-native4-go-root-v2-20261009/root-go.json'),'native4RootActualProof':str(D/'report.json'),'native4Calls':4,'nativeCompilerSHA256':artifacts[0]['native']['sha256'],'oldNative4V1FAILPreserved':True,'guestCalls':0,'performanceQualified':False};c['noLiveProcess']=True;p.write_text(json.dumps(c,indent=2)+'\n')
