"""Pure parser/whole-byte certificate/primary-loader argv controls; no subprocess/thread/FD APIs."""
import json,hashlib,struct,ast,importlib.util
from pathlib import Path
D=Path(__file__).parent
spec=importlib.util.spec_from_file_location('compiler_output',D/'compiler_output.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
pr=json.loads((D/'preregistration.json').read_bytes());ec=json.loads((D/'emission-certificate.json').read_bytes());controls=[]
primary=Path(pr['loaderGrammarSource']['path']).read_bytes();assert hashlib.sha256(primary).hexdigest()==pr['loaderGrammarSource']['sha256'];primary=primary.decode();main=primary[primary.index('int main(int argc, char **argv) {'):];assert main.index('argc = i;')<main.index('argc < 6 || argc > 11')<main.index('argc != (int)(6 + arity)')<main.index('FILE *file = fopen(argv[1], "rb");');assert 'kexe_guest_argv = argv + i + 1;'in main and 'kexe_guest_argc = argc - i - 1;'in main
for c in pr['cases']:
 a=c['nativeArgv'];assert len(a)==13 and a[2:7]==['0','0','aarch64','35,37,38,39','--'];assert a[7]in['compile','extract-native'];assert a[11:]==['--output',c['outputPath']]
 # Primary loader main source: first -- at6 truncates typedargc to6, equals6+arity0;
 # remaining command args are loader-provided guest command argv, not typed arguments.
 typedargc=a.index('--');assert typedargc==6+int(a[3]);controls.append(c['label']+'-primary-argc0')
 path=json.dumps(c['outputPath']).encode()
 raw=(b'{:ok true, :target :aarch64-macos, :output '+path+b', :bytes 100}\n')if c['kind']=='compile'else(b'{:ok true, :output '+path+b', :offset 0, :length 100, :arity '+str(c['arity']).encode()+b'}\n')
 assert m.parse_output(raw,c)['kind']==c['kind'];controls.append(c['label']+'-strict-positive')
 for name,bad in [('empty',b''),('partial',raw[:-1]),('trap',b'{:trap :fuel}\n'),('extra',raw+b'junk\n'),('wrongpath',raw.replace(path,b'"wrong"'))]:
  try:m.parse_output(bad,c)
  except AssertionError:controls.append(c['label']+'-'+name)
  else:raise AssertionError('mutant accepted '+name)
old=Path(ec['originalOffContainer']['path']).read_bytes();expected=bytearray(old)
cut=old.index(b'\n\n')+2
for change in ec['changes']:
 p=cut+change['physicalByteOffset'];assert struct.unpack_from('<I',old,p)[0]==change['before'];struct.pack_into('<I',expected,p,change['after'])
assert hashlib.sha256(expected).hexdigest()==ec['expectedContainerSHA256'];assert hashlib.sha256(expected[cut:]).hexdigest()==ec['expectedWholeNativeSHA256'];assert len(expected)==len(old)
for name,pos in [('header-change',0),('unlisted-word',cut),('wrong-private-target',cut+ec['changes'][-1]['physicalByteOffset'])]:
 mutant=expected.copy();mutant[pos]^=1;assert hashlib.sha256(mutant).hexdigest()!=ec['expectedContainerSHA256'];controls.append(name)
for p in D.glob('*.py'):ast.parse(p.read_bytes())
result={'status':'PASS_PURE_HFT_COMPOSE511_BOUND_HOIST_NATIVE4_SOURCE_CONTROLS_ONLY','controls':controls,'callsScheduled':4,'suppliedEnvironmentKeys':len(pr['environment']),'nativeCalls':0,'guestCalls':0,'expectedEmissionBytesDerivedFromSavedOFF':True,'actualNewCandidateSyntaxPending':True}
(D/'source-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'controls':len(controls),'calls':4,'native':0}))
