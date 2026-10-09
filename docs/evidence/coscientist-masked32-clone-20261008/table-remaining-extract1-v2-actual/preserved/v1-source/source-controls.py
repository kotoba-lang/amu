"""Finite SOURCE checks only. Never calls driver main/loader/setter/libproc."""
from pathlib import Path
import ast,json,hashlib,importlib.util
D=Path(__file__).resolve().parent;W=D.parent;B=W/'crc-table-decision-collapse-tc-emitted-build8-source-v1-20261008'
for p in D.glob('*.py'):ast.parse(p.read_text())
pr=json.loads((D/'preregistration.json').read_bytes());assert pr['maximumLoaderCalls']==1 and pr['maximumDistinctProcessStarts']==2 and len(pr['orderedChildren'])==1
assert len(pr['environment'])==17 and pr['environment']['KEXE_CAP_RESOURCES_35']==str(D/'run-outputs')
assert pr['actualEmissionProof']['sha256']=='98416905a0b6afad3a7cd04e1e73d50c04e10b9f667aac70a710f3271801c693'
ns={'__file__':str(D/'launch-wrapper.py'),'__name__':'offline_wrapper_controls'};exec(compile((D/'launch-wrapper.py').read_bytes(),str(D/'launch-wrapper.py'),'exec'),ns)
argv=pr['orderedChildren'][0]['nativeArgv'];assert ns['allowed'](argv,pr)
controls=[]
for name,index,value in [('different saved producer',1,pr['producer']['path']),('different symbol',10,'prefix-crc'),('old input path',8,pr['savedContainer']['path']),('old output namespace',12,str(B/'run-outputs/observed-on-input.bin')),('extra native arg',None,'check')]:
 a=argv.copy()
 if index is None:a.append(value)
 else:a[index]=value
 assert not ns['allowed'](a,pr);controls.append({'name':name,'rejected':True})
assert ns['environment_admission'](pr['environment'],dict(pr['environment']))['runtimeExtraKeyNames']==[]
e=dict(pr['environment']);e['__CF_USER_TEXT_ENCODING']='opaque-metadata';assert ns['environment_admission'](pr['environment'],e)['runtimeExtraKeyNames']==['__CF_USER_TEXT_ENCODING']
for name,mut in [('unknown runtime key',lambda e:e.__setitem__('UNREGISTERED','1')),('missing required key',lambda e:e.pop('KEXE_FUEL')),('changed required value',lambda e:e.__setitem__('KEXE_FUEL','1'))]:
 e=dict(pr['environment']);mut(e)
 try:ns['environment_admission'](pr['environment'],e)
 except AssertionError:controls.append({'name':name,'rejected':True})
 else:raise AssertionError(name)
assert (D/'adapter.py').read_bytes()==(B/'adapter.py').read_bytes()
assert not(D/'run-outputs').exists()and not(B/'run-outputs/observed-on-input.bin').exists()and not(B/'run-outputs/completion.json').exists()
raw=(B/'run-outputs/observed-on-input.kseed').read_bytes();end=raw.index(b'\n\n');rows=raw[:end].splitlines();assert rows[0]==b'KSEED1 3680 4'
exports=[(z[0].decode(),int(z[1]),int(z[2]))for row in rows[1:]for z in [row.split()]];assert exports==[tuple(r)for r in pr['expectedExports']]
assert raw[end+2:]==(B/'run-outputs/on-input.bin').read_bytes()
q={'status':'PASS_FINITE_SOURCE_CONTROLS_ONLY','knownNativeArgvAccepted':True,'negativeControls':controls,'exact17EnvironmentControls':True,'savedContainerAndCandidateNativeIdentity':True,'old7FailedNamespaceAbsencePreserved':True,'expectedFreshObservedArtifactNotProduced':True,'nativeCompilerGuestSetterProcessAPICalls':0}
(D/'source-controls.json').write_text(json.dumps(q,indent=2)+'\n')
