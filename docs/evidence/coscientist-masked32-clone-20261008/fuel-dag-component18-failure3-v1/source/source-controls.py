"""Pure source/record controls. No subprocess or native invocation."""
from pathlib import Path
import json,importlib.util,ast
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('checker',D/'validate.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
def model(c):
 f=2;g=1;p=10;end=18;ff=[0]*16;ff[10]=2;ff[12]=p;ff[14]=1;gf=[0]*16;gf[12]=1
 r=[('PIPELINE',[0,40,4]),('ALLOC',[100,100,100,200,0,0]),('ROOT',[c,30,f,1,2,end,p,100,200,300,40,4,4,4,32,0,0])]
 outer=[[1,f,2,2],[18,0,0,0],[9,7,0,0],[4,0,1,0],[4,1,2,0],[6,3,0,0],[13,g,0,1],[19,0,0,0],[2,f,0,0]]
 r += [('SIR',[p+j,*s])for j,s in enumerate(outer)];r += [('FREC',[f,j,x])for j,x in enumerate(ff)]
 inner=[[1,g,1,1],[9,1,0,0],[4,0,1,0],[3,1,4294967295,0],[6,5,0,0],[19,0,0,0],[2,g,0,0]]
 r += [('INNER',[1+j,*s])for j,s in enumerate(inner)];r += [('IFREC',[g,j,x])for j,x in enumerate(gf)]
 if c>=6:r += [('GUARD',[c,0,901 if c==9 else 0,1])]
 else:
  r += [('STATE',[c,end,20,60,30,2,2,3,0,0,1,1,40,1])];r += [('FUELWORD',[25+j,w])for j,w in enumerate(v.FUEL)]
  if c<3:r += [('FUELMODEL',[c,1 if c==0 else 0,0 if c==0 else c-1,0])]
 r += [('END',[c,777])]
 return ('\n'.join(tag+' '+' '.join(map(str,z))for tag,z in r)+'\n').encode()
positive=[]
for c in range(16):positive.append(v.verify(model(c),c))
mutants=[model(0).replace(b'END 0 777',b'END 0 778'),model(0).replace(b'FUELMODEL 0 1 0 0',b'FUELMODEL 0 1 0 1'),model(0).replace(b'IFREC 1 14 0',b'IFREC 1 14 1'),model(0).replace(b'ROOT 0 30 2 1 2',b'ROOT 0 30 2 1 8'),model(0).replace(str(v.FUEL[0]).encode(),str(v.FUEL[0]+1).encode()),model(0).replace(b' 0 0 1 1 40 1',b' 0 0 0 1 40 1'),model(9).replace(b'GUARD 9 0 901 1',b'GUARD 9 0 901 0'),model(6).replace(b'GUARD 6 0 0 1',b'GUARD 6 1 0 1')]
for j,b in enumerate(mutants):
 try:v.verify(b,9 if j==6 else 6 if j==7 else 0)
 except (AssertionError,ValueError):pass
 else:raise AssertionError('accepted mutant'+str(j))
for n in ['run.py','assemble.py','validate.py','source-controls.py']:ast.parse((D/n).read_text())
s=(D/'run.py').read_text();assert "except BaseException as ex"in s and "os.killpg(p.pid,signal.SIGKILL)"in s and "p.wait(timeout=pr['reapSeconds'])"in s and "len(rows)<18"in s
rev=json.loads((D/'reversal.json').read_text());assert rev['exactReverseParent']and rev['sentinelNoSecondFallback']
(D/'source-controls.json').write_text(json.dumps({'status':'PASS_PURE_SOURCE_RECORD_CONTROLS_ONLY','syntheticValidCases':16,'rejectedMutants':8,'syntaxFiles':4,'parentReversal':True,'nativeCalls':0,'genuineFixtureEligibility':False,'actualTrapQualified':False},indent=2)+'\n')
