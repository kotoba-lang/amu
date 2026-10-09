"""Pure finite parser/admission mutation controls; never call main or operational APIs."""
from pathlib import Path
import ast,json,copy
D=Path(__file__).resolve().parent
def load(p):return json.loads(Path(p).read_bytes())
def inert(name):
 ns={'__name__':'source_controls_only','__file__':str(D/name)}
 exec(compile((D/name).read_bytes(),str(D/name),'exec'),ns);return ns
for p in D.glob('*.py'):ast.parse(p.read_text())
pr=load(D/'preregistration.json');run=inert('run.py');wrapper=inert('launch-wrapper.py');decoder=inert('validate-runtime.py')
ep=load(pr['actualEmissionProof']['path']);xp=load(pr['actualExtractionProof']['path']);ec=load(pr['actualExtractionCompletion']['path'])
run['emission_guard'](ep,xp,ec,pr)
mutants=[('ep','status','wrong'),('ep','oldBuild8StillFailed',False),('ep','savedCalls',8),('ep','completionAbsent',False),('xp','oldCallsRepeated',1),('xp','guestRuntimeQualified',True),('xp','freshExtractionCalls',2),('ec','TCEmitterExecuted',True),('ec','generatedWorkloadExecuted',True),('ec','status','COMPLETE_CURRENT_ORIGINAL_TC_EMITTED_BUILD8_ARTIFACT_IDENTITY_ONLY'),('ec','sourcePinsSHA256','wrong')]
for target,key,value in mutants:
 e,x,c=copy.deepcopy((ep,xp,ec));{'ep':e,'xp':x,'ec':c}[target][key]=value
 try:run['emission_guard'](e,x,c,pr)
 except AssertionError:pass
 else:raise AssertionError((target,key))
tail=b' :heap {:capacity 16777216 :used 0} :string-pool {:capacity 268435456 :used 0} :vectors {:capacity 4194304 :used 0} :vector-items {:capacity 134217728 :used 0}}\n'
ok=b'{:status :ok :result 1 :fuel {:initial 1000000 :remaining 999998}'+tail
negative=[ok+b'SENTINEL\n',b'SENTINEL\n'+ok,ok[:-2],ok.replace(b':result 1',b':exit 1'),ok.replace(b':result 1',b':result 9223372036854775808'),ok.replace(b'999998',b'1000001'),ok.replace(b'16777216',b'16777215'),ok.replace(b':used 0',b':used -1',1),ok+ok]
assert decoder['parse_report'](ok)['remainingFuel']==999998
for b in negative:
 try:decoder['parse_report'](b)
 except AssertionError:pass
 else:raise AssertionError('parser mutant accepted')
assert len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='1000000'
assert 'KEXE_COMMAND'not in pr['environment'] and not any(k.startswith('KEXE_CAP_')for k in pr['environment'])
assert pr['orderedChildren']==pr['cases'] and len(pr['cases'])==8 and not(D/'run-outputs').exists()
for i,c in enumerate(pr['cases']):
 assert c['index']==i+1 and c['arm']==['OFF','ON'][i%2] and c['nativeArgv'][5]=='-' and c['arity']==1
 assert wrapper['allowed'](c['nativeArgv'],pr)
 payload,exports=run['kseed'](Path(pr[c['arm'].lower()+'Container']['path']).read_bytes())
 assert payload==Path(pr[c['arm'].lower()+'Artifact']['path']).read_bytes()
 assert (c['symbol'],c['offset'],1)in exports
 changed=c['nativeArgv'].copy();changed[2]=str(c['offset']+4);assert not wrapper['allowed'](changed,pr)
 if i%2:assert (c['symbol'],c['argument'],c['expectedResult'])==tuple(pr['cases'][i-1][k]for k in ['symbol','argument','expectedResult'])
q={'status':'PASS_SOURCE_ONLY_FINITE_CONTROLS_NO_GO','proofAdmissionNegativeControls':len(mutants),'syntheticParserNegativeControls':len(negative),'argvNegativeControls':8,'sourceContainerOwnOffsetsResolved':True,'nativeCalls':0,'networkCalls':0,'setters':0,'processAPICalls':0,'C2Enabled':False,'notNativeAdmissionTests':True}
(D/'source-controls.json').write_text(json.dumps(q,indent=2)+'\n')
