"""Pure injection/source-read checks only; no Clang/Popen/FD/thread APIs."""
from pathlib import Path
import json, copy, ast
import run
D=Path(__file__).resolve().parent
pr=json.loads((D/'preregistration.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes())
assert run.scope(pr,ip)
negative=[]
def refuse(name,fn):
    try: fn()
    except (AssertionError,ValueError,KeyError,TypeError): negative.append(name)
    else: raise AssertionError('mutant admitted '+name)
for name,k,v in [('stale-count','exactInputFiles',49),('stale-bytes','exactInputLogicalBytes',0),('bool-count','exactInputFiles',True),('bool-bytes','exactInputLogicalBytes',True),('guest-authorized','guestCalls',1),('second-build','maximumClangBuildCalls',2),('C2','C2',True),('wrong-source','source',{}),('extra-command','maximumChildCalls',6)]:
    z=copy.deepcopy(pr);z[k]=v;refuse(name,lambda:run.scope(z,ip))
for name,change in [('wrong-macro',lambda z:z['cases'][3]['argv'].__setitem__(4,'-DKEXE_OWNERSHIP_DIAGNOSTIC_V4')),('environment-injection',lambda z:z['environment'].update(CPATH='/external')),('different-timeout',lambda z:z['cases'][3].update(timeoutSeconds=181))]:
    z=copy.deepcopy(pr);change(z);refuse(name,lambda:run.scope(z,ip))
dep=('kexe_loader_diagnostic.o: '+pr['source']['path']+'\n').encode()
assert run.dependencies(dep,pr)==[pr['source']['path']]
for name,b in [('dependency-duplicate',dep[:-1]+b' '+pr['source']['path'].encode()),('dependency-relative',b'x: relative.h\n'),('dependency-outside',b'x: /etc/passwd\n'),('dependency-NUL',dep+b'\x00'),('dependency-two-targets',dep+b'y: x\n')]:refuse(name,lambda:run.dependencies(b,pr))
cmds=[[pr['compiler']['path'],'-cc1','-isysroot',pr['sdk'],pr['source']['path']],[pr['linker']['path'],'-syslibroot',pr['sdk'],'-lSystem','-lproc','-o',str(Path(pr['outputRoot'])/'kexe-loader')]]
def encoded(cs):return ('\n'.join(' '.join(json.dumps(x)for x in c)for c in cs)+'\n').encode()
assert run.preview(encoded(cmds),pr,ip)==cmds
for name,change in [('foreign-linker',lambda z:z[1].__setitem__(0,'/foreign/ld')),('foreign-library',lambda z:z[1].append('-lGPU')),('framework',lambda z:z[1].extend(['-framework','Metal'])),('foreign-input',lambda z:z[0].append('/etc/passwd')),('third-command',lambda z:z.append(z[0]))]:
    z=copy.deepcopy(cmds);change(z);refuse(name,lambda:run.preview(encoded(z),pr,ip))
for p in D.glob('*.py'):ast.parse(p.read_bytes())
text=(D/'run.py').read_text()
assert 'killpg'not in text and 'start_new_session=True'not in text
assert text.index("finally:\n        save(O/'terminal.json'")<text.index("status='COMPLETE_SOURCE_BOUND_HELD_LAUNCH_V4")
assert "if not wait_entered:"in text and "wait-uncertain-signal-authority-retired"in text
print(json.dumps({'status':'PASS_PURE_SOURCE_HELD_LAUNCH_V4_BUILD5_MODELS_ONLY','refusals':negative,'exactRegistryPositive':True,'dependenciesAndLinkPreviewModelsOnly':True,'actualClangBuildCalls':0,'actualFDProcessGuestCalls':0},indent=2))
