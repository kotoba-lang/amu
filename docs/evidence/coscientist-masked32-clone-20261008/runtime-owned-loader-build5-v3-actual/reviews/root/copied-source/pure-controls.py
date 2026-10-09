"""Pure injection/source-read checks only; no Clang/Popen/FD/thread APIs."""
from pathlib import Path
import json, copy, ast, struct
import run
D=Path(__file__).resolve().parent
pr=json.loads((D/'preregistration.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes())
assert run.scope(pr,ip)
negative=[]
def refuse(name,fn):
    try: fn()
    except (AssertionError,ValueError,KeyError,TypeError,UnicodeDecodeError): negative.append(name)
    else: raise AssertionError('mutant admitted '+name)
for name,k,v in [('stale-count','exactInputFiles',49),('stale-bytes','exactInputLogicalBytes',0),('bool-count','exactInputFiles',True),('bool-bytes','exactInputLogicalBytes',True),('guest-authorized','guestCalls',1),('second-build','maximumClangBuildCalls',2),('C2','C2',True),('wrong-source','source',{}),('extra-command','maximumChildCalls',6)]:
    z=copy.deepcopy(pr);z[k]=v;refuse(name,lambda:run.scope(z,ip))
for name,change in [('wrong-macro',lambda z:z['cases'][3]['argv'].__setitem__(3,'-DKEXE_OWNERSHIP_DIAGNOSTIC_V4')),('environment-injection',lambda z:z['environment'].update(CPATH='/external')),('different-timeout',lambda z:z['cases'][3].update(timeoutSeconds=181))]:
    z=copy.deepcopy(pr);change(z);refuse(name,lambda:run.scope(z,ip))
dep=('kexe_loader_diagnostic.o: '+pr['source']['path']+'\n').encode()
assert run.dependencies(dep,pr)==[pr['source']['path']]
for name,b in [('dependency-duplicate',dep[:-1]+b' '+pr['source']['path'].encode()),('dependency-relative',b'x: relative.h\n'),('dependency-outside',b'x: /etc/passwd\n'),('dependency-NUL',dep+b'\x00'),('dependency-two-targets',dep+b'y: x\n'),('dependency-source-missing',('x: '+pr['sdk']+'/usr/include/stdio.h\n').encode())]:refuse(name,lambda:run.dependencies(b,pr))
cmds=[[str(Path(pr['outputRoot'])/'kexe_loader_diagnostic-fixture42.o')if t=='__OBJECT__'else t for t in c]for c in pr['previewCommandsTemplate']]
def encoded(cs):return ('\n'.join(' '.join(json.dumps(x)for x in c)for c in cs)+'\n').encode()
assert run.preview(encoded(cmds),pr,ip)==cmds
for name,change in [('foreign-linker',lambda z:z[1].__setitem__(0,'/foreign/ld')),('foreign-library',lambda z:z[1].append('-lGPU')),('framework',lambda z:z[1].extend(['-framework','Metal'])),('foreign-input',lambda z:z[0].append('/etc/passwd')),('third-command',lambda z:z.append(z[0]))]:
    z=copy.deepcopy(cmds);change(z);refuse(name,lambda:run.preview(encoded(z),pr,ip))
# Exact V5 prospective argv is a gate, not a substituted historical compile.
assert pr['cases'][3]['argv']==json.loads(Path(pr['subjectPreregistration']['path']).read_bytes())['prospectiveLoaderBuildArgv']
for name,change in [('wrong-default-sdk',lambda z:z[0].__setitem__(z[0].index('-isysroot')+1,'/foreign/sdk')),('missing-default-sdk',lambda z:z[1].__delitem__(slice(z[1].index('-syslibroot'),z[1].index('-syslibroot')+2))),('wrong-resource-dir',lambda z:z[0].__setitem__(z[0].index('-resource-dir')+1,'/foreign/clang')),('wrapper-as-frontend',lambda z:z[0].__setitem__(0,pr['compiler']['path']))]:
    z=copy.deepcopy(cmds);change(z);refuse(name,lambda:run.preview(encoded(z),pr,ip))
assert run.bounded_diagnostic(b'')['nonempty']is False
assert run.bounded_diagnostic(b'source.c:7: warning: deprecated API [-Wdeprecated-declarations]\n')['nonempty']is True
for name,b in [('diagnostic-NUL',b'warning:\x00'),('diagnostic-invalidUTF8',bytes([255])),('diagnostic-overcap',b'w'*1048577),('diagnostic-error',b'source.c:7: error: failed\n')]:
    refuse(name,lambda:run.bounded_diagnostic(b))
for name,change in [('dumpdir-other-output',lambda z:z[0].__setitem__(z[0].index('-dumpdir')+1,pr['outputRoot']+'/foreign-')),('internal-search-outside',lambda z:z[0].__setitem__(z[0].index('-internal-isystem')+1,'/external/include')),('attached-I-outside',lambda z:z[0].__setitem__(z[0].index('-I/usr/local/include'),'-I/external/include')),('attached-L-outside',lambda z:z[1].__setitem__(z[1].index('-L/usr/local/lib'),'-L/external/lib')),('debug-dir-outside',lambda z:z[0].__setitem__(next(i for i,t in enumerate(z[0])if t.startswith('-fdebug-compilation-dir=')),'-fdebug-compilation-dir=/external')),('mismatched-object',lambda z:z[1].__setitem__(z[1].index(str(Path(pr['outputRoot'])/'kexe_loader_diagnostic-fixture42.o')),str(Path(pr['outputRoot'])/'kexe_loader_diagnostic-other.o'))),('unknown-nonabsolute-option',lambda z:z[0].append('-funknown-role'))]:
    z=copy.deepcopy(cmds);change(z);refuse(name,lambda:run.preview(encoded(z),pr,ip))
def absent(_):raise FileNotFoundError()
assert run.absent_paths(pr['localLibraryShadowPaths'],absent)
refuse('local-library-shadow-present',lambda:run.absent_paths(pr['localLibraryShadowPaths'],lambda _:object()))
sh=run.local_header_shadows([pr['sdk']+'/usr/include/sys/resource.h',pr['compilerResourceDirectory']+'/include/stddef.h'],pr)
assert sh==['/usr/local/include/stddef.h','/usr/local/include/sys/resource.h']
refuse('local-selected-header-shadow-present',lambda:run.absent_paths(sh,lambda _:object()))
def command(kind,name,minimum):
    text=name.encode()+b'\x00';length=((minimum+len(text)+7)//8)*8
    return struct.pack('<III',kind,length,minimum)+bytes(minimum-12)+text+bytes(length-minimum-len(text))
def model_macho(lib='/usr/lib/libSystem.B.dylib',dyld='/usr/lib/dyld',extra=b''):
    commands=command(0xc,lib,24)+command(0xe,dyld,12)+extra
    return struct.pack('<IIIIIIII',0xfeedfacf,0x100000c,0,2,2+(1 if extra else 0),len(commands),0,0)+commands
assert run.macho_loader(model_macho(),pr)['loadDylibs']==['/usr/lib/libSystem.B.dylib']
for name,b in [('macho-foreign-library',model_macho('/external/lib.dylib')),('macho-foreign-dyld',model_macho(dyld='/external/dyld')),('macho-rpath',model_macho(extra=struct.pack('<II',0x8000001c,8))),('macho-truncated-command',model_macho()[:-1]),('macho-wrong-cpu',model_macho()[:4]+bytes(4)+model_macho()[8:])]:refuse(name,lambda:run.macho_loader(b,pr))
for p in D.glob('*.py'):ast.parse(p.read_bytes())
text=(D/'run.py').read_text()
assert 'killpg'not in text and 'start_new_session=True'not in text
assert text.index("finally:\n        save(O/'terminal.json'")<text.index("status='COMPLETE_SOURCE_BOUND_HELD_LAUNCH_V6")
assert "if not wait_entered:"in text and "wait-uncertain-signal-authority-retired"in text
print(json.dumps({'status':'PASS_PURE_SOURCE_HELD_LAUNCH_V6_BUILD5_MODELS_ONLY','refusals':negative,'exactRegistryPositive':True,'dependenciesAndLinkPreviewModelsOnly':True,'actualClangBuildCalls':0,'actualFDProcessGuestCalls':0},indent=2))
