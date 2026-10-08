from pathlib import Path
import re,json,hashlib,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');O=Path(__file__).resolve().parent;P=Path('/Users/junkawasaki/github/wt/amu-seed17/bench/embench/batch-ports/crc32.kotoba')
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
rootPath=W/'crc-original-table-reach-source-trace-root-20261009/report.json';root=json.loads(rootPath.read_text());assert pin(P)==root['source']
tokens=re.findall(r'[()\[\]]|[^\s()\[\]]+',re.sub(r';[^\n]*','',P.read_text()));pos=0
def parse():
 global pos
 t=tokens[pos];pos+=1
 if t in ['(','[']:
  close=')'if t=='('else']';xs=[]
  while tokens[pos]!=close:xs.append(parse())
  pos+=1;return xs if t=='('else ('vector',xs)
 return int(t)if re.fullmatch(r'-?\d+',t)else t
forms=[]
while pos<len(tokens):forms.append(parse())
fns={x[1]:(x[2][1][::2],x[-1])for x in forms if isinstance(x,list)and x and x[0]in ['defn','defn-']}
class Recur(Exception):
 def __init__(self,values):self.values=values
calls=[];steps=0
def ev(x,e):
 global steps
 steps+=1;assert steps<2000000,'finite interpreter bound'
 if type(x)is int:return x
 if isinstance(x,str):return e[x]
 if isinstance(x,tuple):return [ev(v,e)for v in x[1]]
 op=x[0]
 if op=='if':return ev(x[2]if ev(x[1],e)else x[3],e)
 if op=='let':
  local=dict(e);bind=x[1][1]
  for i in range(0,len(bind),2):local[bind[i]]=ev(bind[i+1],local)
  return ev(x[-1],local)
 if op=='loop':
  bind=x[1][1];names=bind[::2];local=dict(e)
  for n,v in zip(names,bind[1::2]):local[n]=ev(v,local)
  while True:
   try:return ev(x[-1],local)
   except Recur as r:
    assert len(r.values)==len(names);local.update(zip(names,r.values))
 if op=='recur':raise Recur([ev(v,e)for v in x[1:]])
 vals=[ev(v,e)for v in x[1:]]
 if op in fns:
  names,body=fns[op];assert len(names)==len(vals)
  if op=='table-at':calls.append(vals[0])
  return ev(body,dict(zip(names,vals)))
 if op=='<':return vals[0]<vals[1]
 if op=='=':return vals[0]==vals[1]
 if op=='+':return sum(vals)
 if op=='-':return vals[0]-vals[1]
 if op=='*':return vals[0]*vals[1]
 if op=='bit-and':return vals[0]&vals[1]
 if op=='bit-xor':return vals[0]^vals[1]
 if op=='bit-not':return ~vals[0]
 if op=='u64-shift-right':return (vals[0]&((1<<64)-1))>>vals[1]
 if op=='vector-at':assert 0<=vals[1]<len(vals[0]);return vals[0][vals[1]]
 raise AssertionError(op)
# Evaluate each table leaf via actual branch structure, not concatenation assumption.
values=[]
for i in range(256):values.append(ev(['table-at',i],{}))
assert values==root['sourceTableValues']
calls=[];traces=[]
for stop in [1,2,1024,1081]:
 calls=[];ans=ev(['prefix-crc',stop],{});visited=list(calls);assert len(visited)==stop
 traces.append(dict(prefix=stop,CRC=ans,distinctIndices=len(set(visited)),missingIndices=sorted(set(range(256))-set(visited))))
 if stop==1081:fullVisits=visited
assert traces==root['traces']
first=[next(j+1 for j,v in enumerate(fullVisits)if v==i)for i in range(256)]
assert first==root['firstVisitByIndex'] and max(first)==root['all256FirstPrefix']==1081
assert len(set(fullVisits[:1080]))==255 and set(range(256))-set(fullVisits[:1024])=={154}
new=W/'crc-table-decision-collapse-tc-remaining-extract1-source-v2-20261009/run-outputs/observed-on-input.bin';b=new.read_bytes();assert len(b)==3680 and sha(b)=='5187d8338730957bf4611f294117c811099af65c9d1117492dd57430e8fa8999'
payload=struct.pack('<256Q',*values);assert b[1632:1632+2048]==payload
old=W/'crc-table-decision-collapse-native-component-v4-portable-env-20261008/run-outputs/ordinary-input.bin';oldb=old.read_bytes();assert len(oldb)==3640 and sha(oldb)=='8c5ab9f7a78b4df15a735d655bdcbee8b4b3bef6613cdcf99e639b153332b7d4';hits=[i for i in range(len(oldb))if oldb.startswith(payload,i)];assert hits==[1592]
# Concrete table mutation invisible to 1024 coverage/answer but observed at first full prefix.
fnsOriginal=fns['table-at'];mut=values.copy();mut[154]^=1
fns['table-at']=(['i'],['vector-at',('vector',mut),'i'])
calls=[];mut1024=ev(['prefix-crc',1024],{});calls=[];mut1081=ev(['prefix-crc',1081],{});fns['table-at']=fnsOriginal
assert mut1024==1703161001 and mut1081!=4018572661
rootFreeze=rootPath.parent/'freeze.json';rf=json.loads(rootFreeze.read_text())
for n,v in rf['files'].items():
 raw=(rootPath.parent/n).read_bytes();assert len(raw)==v['bytes'] and sha(raw)==v['sha256']
r={'rootFreeze':pin(rootFreeze),'rootFrozenFiles':rf['files'],'status':'PASS_INDEPENDENT_FINITE_ORIGINAL_SOURCE_TABLE_REACH_TRACE_ONLY','independent':True,'priorAuthorship':False,'source':pin(P),'rootReport':pin(rootPath),'method':'New bounded S-expression parser/interpreter executes original table branch tree, next-seed/checksum/prefix functions; records actual interpreted table-at argument on each recurrence. Root algorithm not imported or executed. Arithmetic intermediates here remain within signed i64 before masks; unsigned shifts explicitly mask u64.',
'verifiedTraces':traces,'firstVisitByIndex':first,'all256FirstPrefix':1081,'prefix1080Distinct':255,'literalIdentity':{'sourceValues':256,'nativeON':pin(new),'ONPoolOffset':1632,'nativeOFF':pin(old),'OFFUniqueContiguousPoolOffset':1592,'tableBytes':2048,'tableSHA256':sha(payload),'allValuesExactBothPayloads':True},
'mutationCounterexample':{'changedTableIndex':154,'operation':'xor1','prefix1024ResultUnchanged':mut1024,'prefix1081MutatedResult':mut1081,'prefix1081OriginalResult':4018572661,'shorter1024FullCoverageClaimRejected':True},
'limitations':['Pure original-source reach only. This does not prove compiled candidate site220 reach, 13-word hardware execution, guest fuel/trap/arena semantics, timing/full19 or performance.', 'Prefix1081 may be separately registered as additional OFF/ON coverage later; this audit neither launches it nor changes original eight cases or original1024 benchmark body/profile.', 'All256 first prefix is proved within the deterministic source trace beginning seed0 and CRC4294967295; no claim about arbitrary seeds or inputs.'],
'operationalCalls':0,'nativeCompilerNetworkProcessAPICalls':0,'subjectEdits':0,'reviewerSource':pin(Path(__file__))}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(O/'report.json')))
