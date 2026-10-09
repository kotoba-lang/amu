"""Inert source helpers and saved bytes only; zero operational APIs."""
from pathlib import Path
import ast,json,importlib.util,copy
from source_capacity import source_capacity_contract,mem_fits,END,WORDS,BASE
D=Path(__file__).parent;pr=json.loads((D/'preregistration.json').read_bytes());assert source_capacity_contract(D,pr)
def module(n):
 sp=importlib.util.spec_from_file_location(n,D/(n+'.py'));m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
parser=module('compiler_output');w=module('launch-wrapper')
def refuses(f):
 try:f()
 except (AssertionError,ValueError,UnicodeError,KeyError):return
 raise AssertionError('refusal model admitted')
for c in pr['cases']:
 assert w.allowed(c['nativeArgv'],pr)
 if c['kind']=='compile':raw=('{:ok true, :target :aarch64-macos, :output '+json.dumps(c['outputPath'])+', :bytes 64}\n').encode();assert parser.parse_output(raw,c)=={'kind':'compile','containerBytes':64}
 else:raw=('{:ok true, :output '+json.dumps(c['outputPath'])+', :offset 0, :length 64, :arity 0}\n').encode();assert parser.parse_output(raw,c)=={'kind':'extract','offset':0,'nativeBytes':64,'arity':0}
 for b in [b'',raw+b'extra',b'QINIT 1\n'+raw,raw.replace(b'64',b'0')]:refuses(lambda b=b,c=c:parser.parse_output(b,c))
 a=copy.deepcopy(c['nativeArgv']);a[-1]+='-different';assert not w.allowed(a,pr)
e=pr['environment'];assert w.environment_admission(e,e)['nativeExecEnvironmentExact']
assert w.environment_admission(e,dict(e,__CF_USER_TEXT_ENCODING='uninspected'))['runtimeExtraKeyNames']==['__CF_USER_TEXT_ENCODING']
refuses(lambda:w.environment_admission(e,dict(e,UNKNOWN='x')));refuses(lambda:w.environment_admission(e,dict(e,KEXE_FUEL='1')))
for p in D.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
s=(D/'run.py').read_text();assert "pr['compileFuel']=='off'and pr['environment']['KEXE_FUEL']=='off'"in s
assert s.index("save(O/'terminal.json'")<s.index('guard();terminal=load')<s.index("save(O/'report.json'")
assert "out.read_bytes()==ordinary"in s and "validate_producer"in s
assert 'validate_producer'in (D/'launch-wrapper.py').read_text()
assert not mem_fits(END-WORDS+1,WORDS) # deterministic capacity refusal; no synthetic success
q={'status':'PASS_PURE_CURRENT_G4_POSITIVE_MEMO4_SOURCE_CONTROLS_ONLY','exactCaseParserPositives':4,'malformedUnexpectedOutputRefusals':16,'exactArgvRefusals':4,'namedEnvironmentPositives':2,'namedEnvironmentRefusals':2,'capacityBoundaryPositives':2,'capacityBoundaryRefusals':3,'nativeCapacityIsBuiltinMemFitsNotInventedTop':True,'sourceAllocationSpan':1765120,'requestedBlockWords':WORDS,'absoluteTopAcceptanceMaximum':END-WORDS,'validLastOrdering':True,'operations':0};(D/'source-controls.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q))
