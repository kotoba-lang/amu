"""Pure source-byte, parser and signed scalar oracle controls. Native0."""
from pathlib import Path
import ast,json,hashlib
D=Path(__file__).resolve().parent
ns={'__file__':str(D/'guest-check.py'),'__name__':'pure_guest_parser'};exec(compile((D/'guest-check.py').read_bytes(),str(D/'guest-check.py'),'exec'),ns)
zero=('KEXE_ARENA_USE {'+' '.join(':'+k+' 0'for k in ns['FIELDS'])+'}\n').encode()
def raw(f,b):
 trap=f=='positive'and b==1;head='{:status :trap :exit 120'if trap else'{:status :ok :result '+str(16 if f=='positive'else 4294967289)
 return (head+' :fuel {:initial '+str(b)+' :remaining '+str(0 if trap else b-2)+'} :heap {:capacity 4096 :used 0} :string-pool {:capacity 1048576 :used 0} :vectors {:capacity 65536 :used 0} :vector-items {:capacity 65536 :used 0}}\n').encode(),(ns['SIGNAL']if trap else b'')+zero
accepted=0
for f,bs in [('positive',[1,2,3]),('negative',[2,3])]:
 for b in bs:
  a,e=raw(f,b);ns['verify'](a,e,f,b);accepted+=1
mutants=[]
a,e=raw('positive',2)
mutants.extend([(a.replace(b':result 16',b':result 17'),e,2),(a.replace(b':remaining 0',b':remaining 1'),e,2),(a.replace(b':used 0',b':used 1',1),e,2),(a+b'0\n',e,2),(a,e+b'bad\n',2),(a.replace(b':initial 2',b':initial 0'),e,2)])
a,e=raw('positive',1);mutants +=[(a,e.replace(b'SIGTRAP',b'SIGILL'),1),(a,e.replace(b':budget/fuel',b':budget/vectors'),1)]
for a,e,b in mutants:
 try:ns['verify'](a,e,'positive',b)
 except AssertionError:pass
 else:raise AssertionError('accepted mutant')
for n in ['build8.py','guest10.py','guest-check.py','source-controls.py']:ast.parse((D/n).read_text())
bs={'__file__':str(D/'build8.py'),'__name__':'pure_build_parser'};exec(compile((D/'build8.py').read_bytes(),str(D/'build8.py'),'exec'),bs)
payload=b'abcde';blob=b'KSEED1 5 1\nbench 0 1\n\n'+payload;assert bs['kseed'](blob)==(payload,[('bench',0,1)])
for bad in [blob[:-1],blob+b'x',blob.replace(b'bench 0 1',b'bench 4 2')]:
 try:bs['kseed'](bad)
 except AssertionError:pass
 else:raise AssertionError('accepted malformed export payload')
for p in [D/'positive.kotoba',D/'negative.kotoba']:
 # Minimal SOURCE delimiter check, no Kotoba execution.
 assert p.read_text().count('(')==p.read_text().count(')')
assert (((7<<1)^7)&0xffffffff)+7==16
assert (((-1<<1)^7)&0xffffffff)==4294967289
s=(D/'guest10.py').read_text();assert 'import validate'not in s and 'exec(compile(parser_bytes'in s and "'aarch64','-'"in s
(D/'pure-controls.json').write_text(json.dumps({'status':'PASS_PURE_SOURCE_ORACLE_AND_STRICT_PARSER_CONTROLS_ONLY','acceptedSyntheticReceipts':accepted,'rejectedReceiptMutants':len(mutants),'oddLiteralTailContainerAccepted':True,'rejectedContainerMutants':3,'sourceSyntaxFiles':4,'nativeCalls':0,'actualCompiledFuelOrderingQualified':False},indent=2)+'\n')
