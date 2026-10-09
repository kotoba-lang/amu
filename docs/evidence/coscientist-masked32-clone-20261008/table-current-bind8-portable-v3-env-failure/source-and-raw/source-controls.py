"""Finite SOURCE-only controls. Synthetic packet is not current native raw."""
from pathlib import Path
import ast,json,struct,hashlib,importlib.util,re
D=Path(__file__).resolve().parent
W=D.parent;O=W/'vector-typed-observer-native-v8/ports/crc32'
for name in ['run.py','validate.py','source-controls.py']:ast.parse((D/name).read_text())
ns={'__file__':str(D/'validate.py'),'__name__':'source_control_validator'}
exec(compile((D/'validate.py').read_bytes(),str(D/'validate.py'),'exec'),ns)
records=json.loads((O/'observer-records.json').read_text());payload=(O/'native.bin').read_bytes()
sir=[r['fields'] for r in records if r['tag']=='SIR'];fr=[r['fields'] for r in records if r['tag']=='FREC']
lt=[r['fields'] for r in records if r['tag']=='LIT'];emit={r['fields'][0]:r['fields'][-2:] for r in records if r['tag']=='EMIT'}
cn=398;pool=1592;lines=[]
source=(D/'original-input.kotoba').read_bytes()
decl=list(re.finditer(rb'\(defn-?\s+([^\s\[]+)',source));assert len(decl)==8
def row(tag,*xs):lines.append(tag+' '+' '.join(map(str,xs)))
for phase in [0,1]:
 row('FH',phase,0,332,9,1000,1000,1000)
 for r in sir:row('FSIR',phase,*r)
 for r in fr:
  for k,v in enumerate(r[1:]):row('FF',phase,r[0],k,v)
  f=r[0];ff=r[1:];match=decl[f-1]
  node=[1,900,0,f,0,0,0,0];sym=[match.start(1),match.end(1),0,0,f,0,0,0]
  for k in range(8):row('FNODE',phase,f,ff[1],k,node[k]);row('FSYM',phase,f,ff[0],k,sym[k])
  tok=[1,match.start(),match.start()+1,0]
  for k in range(4):row('FTOK',phase,f,f,k,tok[k])
owner=0
for j,op,a,b,c in sir:
 if op==1:owner=a
 if op==13:
  for phase in [0,1]:
   for k in range(38):row('TCG',j,phase,k,0)
  start,end=emit[j];row('TCCALL',j,owner,a,b,c,1 if j==220 else 0,start,end,0,96,b+1,1,1,0)
 if op==2:owner=0
labels=sorted((a,emit[j][1]) for j,op,a,b,c in sir if op==9)
row('FOUT',cn,len(payload),max(a for a,_ in labels)+1,65,17,2049,5)
row('FCODE',0,0)
for k in range(1,cn):row('FCODE',k,struct.unpack_from('<I',payload,(k-1)*4)[0])
for lab,position in sorted((a,emit[j][1]) for j,op,a,b,c in sir if op==9):row('FLABEL',lab,position)
for r in records:
 if r['tag']=='FIX':row('FFIX',*r['fields'])
for lit,b,length,unused,tok in lt:row('FLIT',lit,b,length,pool+(lit-1)*128,tok)
for j,v in enumerate(payload[pool:pool+2048],1):row('FLITB',j,v)
ex=[];k=0
for r in fr:
 f=r[0];ff=r[1:]
 if ff[11]==1:
  k+=1;off=4*(ff[13]-1);row('FEXP',k,f,off,ff[3],0);ex.append((decl[f-1][1].decode(),off,ff[3]))
row('FEND',1,0)
raw=('\n'.join(lines)+'\n').encode()
result=ns['verify'](raw,payload,ex,source);assert result['finitePaths']==256
assert result['readerFN']==result['eligibleSite'][2]==1
assert result['readerSIR']==[1,174]
receipt_controls=[]
for field,value in [('readerFN',3),('readerSIR',[2,174]),('eligibleSite',result['eligibleSite'][:2]+[3]+result['eligibleSite'][3:])]:
 bad=dict(result);bad[field]=value
 try:ns['check_receipt'](bad)
 except AssertionError:receipt_controls.append({'field':field,'mutationRejected':True})
 else:raise AssertionError('receipt owner mutation not rejected')
mutants=[
 ('wrong typed caller owner',raw.replace(b'TCCALL 220 3 1',b'TCCALL 220 2 1',1)),
 ('missing current eligible witness',raw.replace(b'TCCALL 220 3 1 0 1 1',b'TCCALL 220 3 1 0 1 0',1)),
 ('path fuel inserted',raw.replace(b'FSIR 0 25 9 8 0 0',b'FSIR 0 25 18 0 0 0',1)),
 ('wrong table slice',raw.replace(b'FSIR 0 29 21 0 2 16',b'FSIR 0 29 21 0 3 16',1)),
 ('wrong current mask',raw.replace(b'FSIR 0 216 3 1 255 0',b'FSIR 0 216 3 1 254 0',1)),
 ('wrong physical pool position',raw.replace(b'FLIT 2 129 128 1720',b'FLIT 2 129 128 1728',1)),
 ('missing prefix context field',raw.replace(b'TCG 220 0 37 0\n',b'',1)),
 ('wrong normal footer',raw.replace(b'FEND 1 0',b'FEND 1 1',1)),
 ('missing typed owner node',raw.replace(next(x for x in raw.splitlines(keepends=True) if x.startswith(b'FNODE 0 1 ')),b'',1)),
 ('missing typed token',raw.replace(next(x for x in raw.splitlines(keepends=True) if x.startswith(b'FTOK 0 1 ')),b'',1)),
 ('missing symbol record',raw.replace(next(x for x in raw.splitlines(keepends=True) if x.startswith(b'FSYM 0 1 ')),b'',1)),
 ('missing fixed physical branch',raw.replace(next(x for x in raw.splitlines(keepends=True) if x.startswith(b'FFIX ')),b'',1)),
 ('missing physical label',raw.replace(next(x for x in raw.splitlines(keepends=True) if x.startswith(b'FLABEL ')),b'',1)),
 ('missing physical export',raw.replace(next(x for x in raw.splitlines(keepends=True) if x.startswith(b'FEXP ')),b'',1)),
 ('missing unadmitted ordinary call',raw.replace(next(x for x in raw.splitlines(keepends=True) if x.startswith(b'TCCALL ') and not x.startswith(b'TCCALL 220 ')),b'',1)),
 ('unexpected extra G context site',raw+b'TCG 1000 0 0 0\n'),
]
controls=[]
for name,b in mutants:
 assert b!=raw
 try:ns['verify'](b,payload,ex,source)
 except (AssertionError,KeyError):controls.append({'fault':name,'syntheticRawRejected':True,'actualNativeFaultDetected':False})
 else:raise AssertionError('undetected source packet mutation '+name)
helper=(D/'observer-helpers.kotoba').read_text();admit=(D/'readonly-admission.kotoba').read_text()
assert 'tc-call'not in admit and 'gn-put'not in helper and 'gn-gs'not in helper and 'vector-assoc'not in helper
assert helper.count('(fo-original-call M i f t n)')==2 # one selected branch only
assert '(df-admit'not in helper and '(tc-admit M i f t n)'in helper
driver=(D/'run.py').read_text();assert "len(rows)<8"in driver and "RLIMIT_AS"not in driver and "RLIMIT_FSIZE"in driver
assert "ROOT_GO_READONLY_TC_CURRENT_BIND8_PORTABLE_MEMORY_ONLY"in driver and "TCEmitterExecutionAuthorized']is False"in driver
assert driver.index("save(O/'terminal.json'")<driver.index("save(O/'completion.json'")
assembly=json.loads((D/'source-assembly.json').read_text());assert assembly['exactReverseBaseline'] and assembly['tcCandidateSourceUnchanged']=='3d7c169818cdf0fabc151da98017d3b28bbe38fc3407d9b42921b646520c2aba'
out={'status':'SOURCE_DATA_CHECKS_ONLY_NO_EXECUTION_GO','syntheticPacketBasedOnHistoricalSourceData':True,
     'currentProducerBindingEstablished':False,'syntheticFinitePaths':256,'syntheticMutants':controls,'readerReceiptControls':receipt_controls,'readerReceiptConsistent':True,
     'PythonSyntaxOnly':True,'observerReadonlyCallGraphSourceCheck':True,'validLastSourceOrderCheck':True,
     'execution':{'compiler':0,'native':0,'ssh':0,'solver':0,'CPUProbe':0},
     'historicalInputs':{str(p):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [O/'observer-records.json',O/'native.bin']}}
(D/'source-controls.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'])
