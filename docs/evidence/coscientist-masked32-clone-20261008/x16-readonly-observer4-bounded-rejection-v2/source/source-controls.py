"""Pure synthetic parser/receipt controls, never a guest semantic oracle."""
from pathlib import Path
import json,struct,ast,copy
from validate_observer import validate,split,PATTERN
D=Path(__file__).resolve().parent
def row(t,x):return(t+' '+' '.join(map(str,x))+'\n').encode()
q=[1,6,0,1,0,0,1]+[0]*15
sir=[[1,1,0,0],[18,0,0,0],[3,0,7,0],[18,0,0,0],[19,0,0,0],[2,1,0,0]]
words=PATTERN*2+[0xd65f03c0,0xd4200020]
lines=[row('RH',[0,0,2,7,1]),row('RQ',q),row('RF',[0,0,0,0,0,0]),row('RF',[0,1,1,0,0,2])]+[row('RS',[0,1,i+1,*s])for i,s in enumerate(sir)]+[row('RE',[0])]
for i,b,e in [(1,1,1),(2,1,6),(3,6,6),(4,6,11),(5,11,12),(6,12,13)]:lines.append(row('RI',[i,b,e,0,0,0,1,0]))
lines +=[row('RH',[1,0,2,7,13]),row('RQ',q),row('RF',[1,0,0,0,0,0]),row('RF',[1,1,1,1,0,2])]+[row('RS',[1,1,i+1,*s])for i,s in enumerate(sir)]+[row('RC',[1,1,13,*words]),row('RE',[1])]
payload=struct.pack('<12I',*words);positive=validate(lines,payload);assert positive['eligiblePairs']==1
zero=[row('RH',[0,0,1,1,1]),row('RQ',[0]*22),row('RF',[0,0,0,0,0,0]),row('RE',[0]),row('RH',[1,0,1,1,1]),row('RQ',[0]*22),row('RF',[1,0,0,0,0,0]),row('RE',[1])];assert validate(zero,b'xxxx')['status']=='REJECTED_INITIAL_BOUNDED_X16_RELOAD_RULE_NO_PAIR'
neg=[]
def reject(label,l,p=payload):
 try:validate(l,p)
 except (AssertionError,IndexError,KeyError):neg.append(label)
 else:raise AssertionError(label)
reject('partial-footer',lines[:-1]);reject('missing-gnins', [x for x in lines if not x.startswith(b'RI 3 ')])
reject('extra-row',lines+[row('RE',[1])]);reject('trap-row',[b'KEXE_TRAP {:kind :signal}\n']+lines)
reject('code-payload-mismatch',lines,b'\0'*len(payload));reject('codeword-mismatch',[x.replace(b'4181722352',b'0')if x.startswith(b'RC ')else x for x in lines])
reject('interval-short',[row('RC',[1,1,12,*words])if x.startswith(b'RC ')else x for x in lines])
reject('fuel-mode-zero-context-fault',[row('RI',[4,6,11,0,0,0,1,120])if x.startswith(b'RI 4 ')else x for x in lines])
reject('post-SIR-mismatch',[row('RS',[1,1,3,3,0,8,0])if x.startswith(b'RS 1 1 3 ')else x for x in lines])
reject('bad-selected-owner',[row('RQ',[1,6,0,1,0,0,2]+[0]*15)if x.startswith(b'RQ ')else x for x in lines])
reject('duplicate-FN-summary',[x.replace(b'RF 0 1 ',b'RF 0 0 ')for x in lines]);reject('RREFUSE',[b'RREFUSE 1 2\n'])
for malformed in [b'',b'{:status :trap :exit 120}\n',b'RH 0\n',b'{:ok true, x}\nEXTRA\n']:
 try:split(malformed)
 except AssertionError:neg.append('split-raw-negative')
 else:raise AssertionError('split mutant')
for p in D.glob('*.py'):ast.parse(p.read_text())
print(json.dumps({'status':'PASS_PURE_SOURCE_PARSER_CONTROLS_ONLY','syntheticEligibilityPositive':1,'zeroRejectPositive':1,'negativeControls':neg,'nativeGuestOracle':False,'actualOperationalCalls':0},indent=2))
