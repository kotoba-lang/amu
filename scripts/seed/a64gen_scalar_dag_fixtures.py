#!/usr/bin/env python3
"""BOOTSTRAP-TOOL: native scalar DAG regression suite, independent source math and physical call checks."""
"""Independent small source interpreter; no SIR/native compiler implementation."""
from pathlib import Path
import re,json,hashlib
MASK=(1<<64)-1;MIN=-(1<<63)
def signed(x):return ((int(x)&MASK)^(1<<63))-(1<<63)
class Trap(Exception):pass
class Again(Exception):
 def __init__(self,values):self.values=values
def parse(s):
 s=re.sub(r';[^\n]*','',s);tokens=re.findall(r'"(?:\\.|[^"\\])*"|[()\[\]]|[^\s()\[\]]+',s);at=0
 def read():
  nonlocal at
  t=tokens[at];at+=1
  if t in ['(','[']:
   close=')' if t=='(' else ']';a=[]
   while tokens[at]!=close:a.append(read())
   at+=1;return a
  return int(t) if re.fullmatch(r'-?\d+',t) else t
 result=[]
 while at<len(tokens):result.append(read())
 return result
class Program:
 def __init__(self,path):
  self.functions={};self.trace=[]
  for a in parse(path.read_text()):
   if a[0] in ['defn','defn-']:self.functions[a[1]]=([a[2][i] for i in range(0,len(a[2]),2)],a[4])
 def call(self,name,args):
  formals,body=self.functions[name];return self.eval(body,dict(zip(formals,args)))
 def eval(self,e,env):
  if isinstance(e,int):return signed(e)
  if isinstance(e,str):
   if e in env:return env[e]
   if e in self.functions:return ('function',e)
   if e=='true':return 1
   if e=='false':return 0
   if e.startswith('"'):return json.loads(e)
   raise ValueError(e)
  op=e[0]
  if op=='fn':return ('closure',e[1],e[2],dict(env))
  if op=='let':
   local=dict(env)
   for k in range(0,len(e[1]),2):local[e[1][k]]=self.eval(e[1][k+1],local)
   return self.eval(e[2],local)
  if op=='loop':
   local=dict(env);names=e[1][::2]
   for k,name in enumerate(names):local[name]=self.eval(e[1][2*k+1],local)
   for _ in range(16):
    try:return self.eval(e[2],local)
    except Again as a:local.update(dict(zip(names,a.values)))
   raise ValueError('source loop finite bound')
  if op=='recur':raise Again([self.eval(v,env) for v in e[1:]])
  if op=='if':return self.eval(e[2] if self.eval(e[1],env) else e[3],env)
  if op=='do':
   value=0
   for v in e[1:]:value=self.eval(v,env)
   return value
  if op=='typed-cap-call':
   assert e[1:4]==[':io/write',':string',':string'];s=self.eval(e[4],env);self.trace.append(s);return s
  args=[self.eval(v,env) for v in e[1:]]
  if op in self.functions:return self.call(op,args)
  if op in env and isinstance(env[op],tuple):
   value=env[op]
   if value[0]=='function':return self.call(value[1],args)
   captured=dict(value[3]);captured.update(dict(zip(value[1],args)));return self.eval(value[2],captured)
  if op=='+':return signed(sum(args))
  if op=='-':return signed(-args[0] if len(args)==1 else args[0]-sum(args[1:]))
  if op=='*':
   value=1
   for a in args:value=signed(value*a)
   return value
  if op=='quot':
   a,b=args
   if b==0 or (a==MIN and b==-1):raise Trap()
   return signed((abs(a)//abs(b))*(-1 if (a<0)!=(b<0) else 1))
  if op=='bit-xor':return signed(args[0]^args[1])
  if op=='bit-and':return signed(args[0]&args[1])
  if op=='bit-or':return signed(args[0]|args[1])
  if op=='bit-not':return signed(~args[0])
  if op=='not':return int(not args[0])
  if op=='=':return int(args[0]==args[1])
  if op=='<':return int(args[0]<args[1])
  if op=='>=':return int(args[0]>=args[1])
  if op=='i64-shift-left':return signed(args[0]<<(args[1]&63))
  if op=='u64-shift-right':return signed((args[0]&MASK)>>(args[1]&63))
  raise ValueError(op)
# BOOTSTRAP-TOOL: standalone native scalar DAG regressions. No observer/baseline required.
import argparse,os,subprocess,tempfile,struct

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--seed',required=True,type=Path);ap.add_argument('--loader',required=True,type=Path);ap.add_argument('--seed-offset',type=int,default=0);ap.add_argument('--fixtures',type=Path,default=Path(__file__).resolve().parents[2]/'seed/tests/scalar-dag');ap.add_argument('--output',type=Path);a=ap.parse_args()
 seed=a.seed.resolve();loader=a.loader.resolve();F=a.fixtures.resolve();D=(a.output or Path(tempfile.mkdtemp(prefix='amu-scalar-dag-regressions-'))).resolve();D.mkdir(parents=True,exist_ok=True)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();env=dict(os.environ,KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(F)+':'+str(D),KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',KEXE_STRING_POOL='268435456',KEXE_VECTORS='4194304',KEXE_PAIRS='16777216',KEXE_VECTOR_ITEMS='134217728');rows=[];machine=[];compiled=set()
 def build(p,d,symbol):
  k=d/'target.kseed';out=d/(symbol+'.bin');steps=[]
  if p not in compiled:steps.append(('compile',['compile',str(p),'--target','aarch64-macos','--output',str(k)]))
  steps.append((symbol+'-extract',['extract-native',str(k),'--symbol',symbol,'--output',str(out)]))
  for name,args in steps:
   q=subprocess.run([str(loader),str(seed),str(a.seed_offset),'0','aarch64','35,37,38,39','--',*args],env=env,capture_output=True,text=True);(d/(name+'.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,(p.name,name,q.stdout,q.stderr)
   if name=='compile':compiled.add(p)
  offset=int(re.search(r':offset (\d+)',q.stdout)[1]);return out,offset
 def body(out,offset):
  raw=out.read_bytes();end=offset
  while end+4<=len(raw):
   end+=4
   if struct.unpack_from('<I',raw,end-4)[0]==0xd65f03c0:return raw[offset:end]
  raise AssertionError('native function lacks RET')
 def bltargets(code,offset):
  values=[]
  for i,(word,) in enumerate(struct.iter_unpack('<I',code)):
   if word&0xfc000000==0x94000000:
    delta=word&0x3ffffff;delta=delta-(1<<26) if delta&(1<<25) else delta;values.append(offset+4*i+4*delta)
  return values
 def execute(name,out,off,args,fuel,want,trace,consumed):
  e=dict(os.environ,KEXE_FUEL=str(fuel),KEXE_STRUCTURED_REPORT='1');e.pop('KEXE_COMMAND',None)
  q=subprocess.run([str(loader),str(out),str(off),str(len(args)),'aarch64','37',*map(str,args)],env=e,capture_output=True,text=True)
  if want is None:assert q.returncode!=0 and 'KEXE_TRAP' in q.stderr,(name,args,q.stdout,q.stderr)
  else:assert q.returncode==0 and int(re.search(r':result (-?\d+)',q.stdout)[1])==want,(name,args,want,q.stdout,q.stderr)
  assert q.stdout.startswith(trace),(name,trace,q.stdout)
  if consumed is not None:
   m=re.search(r':initial (\d+) :remaining (\d+)',q.stdout);assert int(m[1])-int(m[2])==consumed,(name,args,consumed,q.stdout)
  rows.append({'case':name,'args':args,'fuel':fuel,'expected':want,'expectedEffectTrace':trace,'expectedConsumed':consumed,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr})
 anchors={'repeated-swap':9,'shared-dag':23,'bool':0,'shifts':5,'literal-dag':2,'argument-effects':7}
 for name,want in anchors.items():assert Program(F/(name+'.kotoba')).call('run',[1,2])==want,(name,'independent hand-computed arithmetic anchor')
 inputs=[[0,0],[1,2],[-1,3],[7,-9],[(1<<63)-1,1],[-(1<<63),-1],[-(1<<63),63],[17,64],[17,65],[17,-1]]
 refusal={'branch-refuse','div-refuse','fuel-refuse','effect-refuse'}
 required={'repeated-swap','shared-dag','live-caller','shifts','bool','generic-export','indirect','branch-refuse','div-refuse','fuel-refuse','effect-refuse','argument-effects','argument-trap','literal-dag','site-budget','five-args'}
 assert {p.stem for p in F.glob('*.kotoba')}==required,('fixture inventory',str(F))
 for p in sorted(F.glob('*.kotoba')):
  name=p.stem;d=D/name;d.mkdir(exist_ok=True);out,off=build(p,d,'run');callee='mix' if name=='five-args' else 'scalar';helper,hoff=build(p,d,callee);assert helper.read_bytes()==out.read_bytes();hbody=body(helper,hoff)
  if name=='site-budget':
   for symbol,shouldInline in [('f000',True),('f255',True),('f256',False),('f299',False)]:
    caller,at=build(p,d,symbol);cbody=body(caller,at);hasBL=hoff in bltargets(cbody,at);assert hasBL!=shouldInline,(symbol,shouldInline,hasBL)
    if shouldInline:assert hbody[:-4] in cbody
    machine.append({'case':name,'caller':symbol,'helperOffset':hoff,'callerOffset':at,'genericBL':hasBL,'inlineExpected':shouldInline})
  else:
   caller,at=build(p,d,'walk') if name=='five-args' else (out,off);cbody=body(caller,at);hasBL=hoff in bltargets(cbody,at);expected=name not in refusal;assert hasBL!=expected,(name,hoff,hasBL)
   if expected:assert hbody[:-4] in cbody,(name,'original generic helper body absent from caller')
   machine.append({'case':name,'caller':'walk' if name=='five-args' else 'run','helperOffset':hoff,'callerOffset':at,'genericBL':hasBL,'inlineExpected':expected})
  for values in ( [[n] for n in [0,1,2,4,-1,-9,(1<<63)-1,-(1<<63)]] if name=='five-args' else inputs):
   prog=Program(p)
   try:want=prog.call('run',values)
   except Trap:want=None
   trace=''.join(prog.trace);fuel=1048576;consumed=3 if name=='site-budget' else 2 if name in ['effect-refuse','indirect','five-args'] else 1+(values[0]&3) if name=='fuel-refuse' else 1
   execute(name,out,off,values,fuel,want,trace,consumed)
   execute(name,out,off,values,1,None if consumed>1 else want,'' if consumed>1 else trace,1)
  # Public generic entry remains executable, with independent original source meaning.
  if name in ['generic-export','five-args']:
   args=[2,3] if name=='generic-export' else [1,2,3,4,5];prog=Program(p);execute(name+'-generic-entry',helper,hoff,args,1048576,prog.call(callee,args),'',0)
  print('PASS scalar DAG',name,flush=True)
 report={'status':'PASS standalone genuine typed scalar DAG native math/fuel/trap/effect/physical regressions','seedSha256':sha(seed),'programs':len(list(F.glob('*.kotoba'))),'observations':rows,'nativeExecutions':len(rows),'physicalChecks':machine,'sources':{p.name:sha(p) for p in F.glob('*.kotoba')},'limits':['Finite typed controls, not arbitrary IR proof.','Physical checks decode actual BL targets and require exact original generic body in admitted caller; generic export independently executes.','Typed300caller boundary tests256site cap; exact64/65/module4096 raw generator controls remain separate evidence.','No observer, baseline binary, temporary audit path or generated golden dependency.']};(D/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(rows),'native observations',len(machine),'physical checks',D/'report.json')
if __name__=='__main__':main()
