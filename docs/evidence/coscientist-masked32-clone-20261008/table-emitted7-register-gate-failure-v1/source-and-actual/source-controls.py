"""Offline SOURCE controls only; never invoke main, producer, loader, setters or libproc."""
from pathlib import Path
import ast,json,copy,hashlib
D=Path(__file__).resolve().parent;OLD=D.parent/'crc-table-decision-collapse-native-component-v4-portable-env-20261008'
for n in ['run.py','launch-wrapper.py','validate.py','author-source.py','author-plan.py','source-controls.py']:ast.parse((D/n).read_text())
ns={'__file__':str(D/'validate.py'),'__name__':'offline_tc_emission_controls'}
exec(compile((D/'validate.py').read_bytes(),str(D/'validate.py'),'exec'),ns)
base=json.loads((OLD/'run-outputs/typed-binding.json').read_bytes())
# Existing current actual raw is a positive control for the preserved verifier;
# it is never relabeled as actual TC emission.
raw=(OLD/'run-outputs/observed-input-compile.stdout').read_bytes()
payload=(OLD/'run-outputs/ordinary-input.bin').read_bytes()
exports=json.loads((OLD/'run-outputs/completion.json').read_bytes())['products'][0]['exports']
actual=ns['verify_binding'](raw,payload,[tuple(x)for x in exports],(D/'original-input.kotoba').read_bytes())
assert actual==base and actual['TCEmitterExecuted']is False
# Isolated synthetic physical-span model exercises the new certificate only.
# It is not passed to the full raw validator or accepted as an emitted artifact.
b=copy.deepcopy(base);site=b['eligibleSite'];site[6:8]=[244,257]
for row in b['allRawRecords']['TCCALL']:
 if row[0]==220:row[6:8]=[244,257]
rows=copy.deepcopy(b['allRawRecords']);pool=next(r[3]for r in rows['FLIT']if r[0]==1)
words=[0xaa1903e0,0xf94004e8,0xf1000508,0x54000062,0xf90004ff,0xd4200000,0xf940c0f1,0x8b000e31,0xd2800010|((pool&65535)<<5),0xf2a00010|(((pool>>16)&65535)<<5),0xf8706a20,0xf90004e8,0xaa0003e9]
for row in rows['FCODE']:
 if 244<=row[0]<257:row[1]=words[row[0]-244]
rows['FFIX']=[r for r in rows['FFIX']if not 244<=r[1]<257]+[[200,252,5,1,0]]
rows['TCEMIT']=[[220,1,0,1,256,244,257,200,201,0,13,0,1,0]]
model=ns['emission_certificate'](rows,b,base);assert model['spanWords']==13
controls=[]
def reject(name,mut):
 rr=copy.deepcopy(rows);bb=copy.deepcopy(b);mut(rr,bb)
 try:ns['emission_certificate'](rr,bb,base)
 except (AssertionError,KeyError,ValueError):controls.append({'name':name,'rejected':True})
 else:raise AssertionError('accepted '+name)
reject('missing selected-emitter record',lambda r,b:r['TCEMIT'].clear())
reject('duplicate selected-emitter record',lambda r,b:r['TCEMIT'].append(r['TCEMIT'][0].copy()))
reject('wrong selected site',lambda r,b:r['TCEMIT'][0].__setitem__(0,221))
reject('wrong reader owner',lambda r,b:b.__setitem__('readerFN',3))
reject('site capacity exhausted',lambda r,b:r['TCEMIT'][0].__setitem__(12,257))
reject('used-word budget mismatch',lambda r,b:r['TCEMIT'][0].__setitem__(10,4097))
reject('caller prefix descriptor changed',lambda r,b:next(x for x in b['allRawRecords']['TCG']if x[:3]==[220,0,24]).__setitem__(3,1))
for name,at,value in [('no logical charge',246,0xd503201f),('wrong exhaustion publication',248,0xf90004e8),('missing exhaustion trap',249,0xd503201f),('wrong index stride',251,0x8b000a31),('narrow32 table load',254,0xb8706a20),('missing success fuel publication',255,0xd503201f),('wrong input local',244,0xaa1803e0),('wrong result register',256,0xaa0003e8)]:
 reject(name,lambda r,b,at=at,value=value:next(x for x in r['FCODE']if x[0]==at).__setitem__(1,value))
reject('wrong relocation target',lambda r,b:r['FFIX'][-1].__setitem__(3,2))
# GO argv/prereg/source-only syntax. No subprocess method is invoked.
pr=json.loads((D/'preregistration.json').read_bytes());assert len(pr['orderedChildren'])==8 and all(x['nativeArgv'][0]==pr['loader']['path']for x in pr['orderedChildren'])
assert pr['producer']['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'
assert (D/'adapter.py').read_bytes()==(OLD/'adapter.py').read_bytes() and (D/'launch-wrapper.py').read_bytes()==(OLD/'launch-wrapper.py').read_bytes()
assert pr['environment']['TMPDIR']==str(D/'run-outputs') and len(pr['environment'])==17
assert not (D/'run-outputs').exists()
q={'status':'PASS_FINITE_OFFLINE_SOURCE_CONTROLS_ONLY','preservedCurrentActualReadonlyVerifier':True,
 'syntheticTCSpanModelOnly':True,'syntheticModel':model,'mutations':controls,
 'operationalCalls':{'compiler':0,'loader':0,'guest':0,'setter':0,'processAPI':0},
 'doesNotEstablishCurrentCandidateCompilationOrGuestBehavior':True}
(D/'source-controls.json').write_text(json.dumps(q,indent=2)+'\n')
