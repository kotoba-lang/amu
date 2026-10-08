from pathlib import Path
import ast,sys,json,types,hashlib,importlib.util
sys.dont_write_bytecode=True
D=Path(__file__).parent
s=importlib.util.spec_from_file_location('inert_build_driver',D/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert m.kseed(b'KSEED1 5 1\nmain 0 0\n\nabcde')==b'abcde'
rejected=0
for b in [b'KSEED1 4 1\nmain 0 0\n\nabcde',b'KSEED1 5 1\nmain 4 0\n\nabcde',b'KSEED1 5 1\nmain 0 1\n\nabcde']:
 try:m.kseed(b)
 except AssertionError:rejected+=1
 else:raise AssertionError('bad header accepted')
raw=Path('/Users/junkawasaki/github/workspaces/codex/vector-masked32-shift-orr-compiler-build4-plan-v2-native-controls/run-outputs/ON-compile.stderr').read_bytes();assert m.counters(raw)['status']=='valid';assert m.counters(raw+b'error\n')['status']!='valid'
# Exercise actual nested ledger code with an explicitly fake process; no subprocess/OS signal execution.
tree=ast.parse((D/'run.py').read_text());main=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='main');call=next(x for x in main.body if isinstance(x,ast.FunctionDef)and x.name=='call')
for case in ['success','interrupt','nonzero']:
 O=D/'pure-cases'/case;O.mkdir(parents=True);rows=[];events=[];pr=json.loads((D/'preregistration.json').read_bytes());env={'PATH':'fixed','KEXE_ARENA_USE':'1'}
 class Fake:
  pid=1;returncode=None
  def poll(self):
   if case=='interrupt':raise KeyboardInterrupt()
   self.returncode=7 if case=='nonzero'else 0;return self.returncode
  def wait(self,timeout):events.append('wait');self.returncode=0 if self.returncode is None else self.returncode;return self.returncode
 def spawn(argv,**kw):kw['stdout'].write(b'{:ok true}\n');kw['stdout'].flush();kw['stderr'].write(raw);kw['stderr'].flush();events.append('spawn');return Fake()
 ns={k:getattr(m,k)for k in ['need','save','receipt','counters','time','signal','resource']};ns.update(pr=pr,O=O,rows=rows,env=env,guard=lambda:events.append('guard'),subprocess=types.SimpleNamespace(Popen=spawn),os=types.SimpleNamespace(killpg=lambda *x:events.append('kill')))
 exec(compile(ast.Module(body=[call],type_ignores=[]),'<exact ledger pure control>','exec'),ns)
 try:ns['call']('case',['compile','source'])
 except AssertionError:assert case!='success'
 else:assert case=='success'
 assert rows[0]['state']=='terminal'and rows[0]['reaped']and (O/'case.stdout').exists()and (O/'case.stderr').read_bytes()==raw and 'wait'in events
 if case=='interrupt':assert 'kill'in events and rows[0]['error']=='KeyboardInterrupt'
 if case=='nonzero':assert rows[0]['returncode']==7
out={'status':'PASS_PURE_BUILD4_HEADER_COUNTER_AND_EXACT_LEDGER_CONTROLS_ONLY','unalignedDataTailAccepted':True,'badHeadersRejected':rejected,'counterPositiveAndErrorNegative':True,'fakeLedgerCases':3,'interruptKilledAndReaped':True,'nativeCalls':0,'OSSignalCalls':0,'subprocessCalls':0}
(D/'pure-controls.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
