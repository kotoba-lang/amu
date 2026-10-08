"""Finite, source/data-only structural census. Never executes compiler/artifacts."""
import collections, hashlib, json, pathlib, re, struct
W = pathlib.Path('/Users/junkawasaki/github/workspaces/codex')
R = pathlib.Path('/Users/junkawasaki/github/wt/amu-seed17')
OUT = pathlib.Path(__file__).parent
pins = {}
def pin(p):
    b = p.read_bytes(); pins[str(p)] = {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}; return b
def parse(s):
    toks = re.findall(r';[^\n]*|"(?:\\.|[^"\\])*"|[()\[\]{}]|[^\s()\[\]{}]+',s)
    toks = [x for x in toks if not x.startswith(';')]
    i = 0
    def one():
        nonlocal i
        t=toks[i]; i+=1
        if t in ('(','[','{'):
            end={'(':')','[':']','{':'}'}[t]; v=[]
            while toks[i]!=end:v.append(one())
            i+=1; return v
        return t
    forms=[]
    while i<len(toks): forms.append(one())
    return forms
def walk(x):
    if isinstance(x,list):
        yield x
        for a in x: yield from walk(a)
def integer(x): return isinstance(x,str) and bool(re.fullmatch(r'-?\d+',x))
def call(x):return isinstance(x,list) and len(x)>0 and isinstance(x[0],str)
def selector_reader(x):
    return call(x) and len(x)==3 and x[0]=='vector-at' and x[1]=='s' and integer(x[2])
def simple_dispatch(body):
    # Deliberately narrow: no state write/call before selector test; two unchanged-s calls.
    env={}
    if call(body) and body[0]=='let' and len(body)==3 and len(body[1])==2:
        key,val=body[1];env[key]=val;body=body[2]
    if not(call(body) and body[0]=='if' and len(body)==4):return None
    c,y,n=body[1:]
    if not(call(c) and c[0]=='=' and len(c)==3):return None
    sel=env.get(c[1],c[1]) if isinstance(c[1],str) else c[1]
    if not selector_reader(sel) or not integer(c[2]):return None
    if not all(call(a) and len(a)==2 and a[1]=='s' for a in [y,n]):return None
    return {'slot':int(sel[2]),'constant':int(c[2]),'yes':y[0],'no':n[0]}
def source_census(p):
    forms=parse(pin(p).decode());defs={x[1]:x[-1] for x in forms if call(x) and x[0] in ['defn','defn-']}
    nodes=[x for b in defs.values() for x in walk(b) if call(x)]
    heads=collections.Counter(x[0] for x in nodes)
    ds={n:d for n,b in defs.items() if (d:=simple_dispatch(b))}
    chains=[]
    for n,d in ds.items():
        seen=[]; cur=n
        while cur in ds and cur not in seen and ds[cur]['slot']==d['slot']:
            seen.append(cur);cur=ds[cur]['no']
        if len(seen)>=2:
            chains.append({'root':n,'slot':d['slot'],'functions':seen,'constants':[ds[v]['constant'] for v in seen],'fallback':cur})
    return {'definitions':len(defs),'caseForms':heads['case'],'ifForms':heads['if'],
            'vectorReads':heads['vector-at'],'vectorWrites':heads['vector-assoc!'],
            'userCallForms':sum(heads[n] for n in defs),'simpleReadOnlyDispatchFunctions':ds,
            'sameSlotFalseChainsAtLeast2':chains,'maximumRecognizedChain':max([len(x['functions']) for x in chains]+[0])}
bank=W/'vector-leaf-straight-read-cache-current19-build52-go-v2-root/collected/build52'
origins=json.loads(pin(W/'vector-leaf-straight-read-cache-current19-build52-source-v2-lc-remote/input-origins.json'))
report={'schema':'DENSE_DISPATCH_STATIC_FRONTIER/v1','scope':'Original full19 SOURCE and saved artifacts only',
        'execution':{'compiler':0,'native':0,'ssh':0,'solver':0},'currentSources':{},'savedTypedHistorical':{},'savedCurrentBytes':{},'CSource':{}}
names=sorted(p.name for p in bank.iterdir() if p.is_dir() and (p/'header.h').is_file())
assert len(names)==19
for name in names:
    p=W/'vector-leaf-straight-read-cache-g3-original19-compile38-plan-v1-native-controls/run-outputs'/f'{name}.kotoba'
    report['currentSources'][name]=source_census(p)
    assert pins[str(p)]==origins[str(p)],(name,'Current source diverged from build52')
    rp=R/'bench/embench/batch-ports'/f'{name}.kotoba'
    if rp.is_file():
        pin(rp);assert pins[str(rp)]==pins[str(p)],(name,'Repository body differs')
for name in ['statemate','nsichneu']:
    p=W/'vector-leaf-straight-read-cache-g3-original19-compile38-plan-v1-native-controls/run-outputs'/f'{name}.bin'
    data=pin(p);assert pins[str(p)]==origins[str(p)]
    hr=json.loads(pin(bank/name/'header-receipt.json'))
    assert hr['OFF']['sha256']==pins[str(p)]['sha256'] and hr['LC']['sha256']==pins[str(p)]['sha256']
    pin(bank/name/'header.h'); pin(bank/name/'c.dylib')
    report['savedCurrentBytes'][name]={'nativeBytes':pins[str(p)],'OFFequalsLC':True,
        'headerReceipt':str(bank/name/'header-receipt.json'),'CImage':pins[str(bank/name/'c.dylib')],
        'machineDispatchCounts':None,'reason':'No instruction/data boundary map from current producer; do not scan literal pools as instructions.'}
    op=W/'vector-typed-observer-native-v8/ports'/name/'observer-records.json'
    records=json.loads(pin(op));sir=[r['fields'] for r in records if r['tag']=='SIR'];counter=collections.Counter(r[1] for r in sir)
    fs={};fid=None
    for r in sir:
        if r[1]==1:fid=r[2];fs[fid]=[]
        if fid is not None:fs[fid].append(r)
    tails=[{'sir':r[0],'callee':r[2],'temp':r[3],'argc':r[4]} for rows in fs.values() for r,s in zip(rows,rows[1:])
           if r[1]==13 and s[1]==19 and s[2]==r[3] and r[4]<=7]
    protected=['compile.status.json','extract.status.json','compile.stdout','native.bin','native.offset']
    for x in protected: pin(op.parent/x)
    report['savedTypedHistorical'][name]={'lineage':'Historical observer v8; no current producer equivalence claim',
        'opcodeCounts':dict(sorted(counter.items())),'functionCount':len(fs),'directTailCallSites':tails,
        'fuelSIR':counter[18],'runtimeCallSIR':counter[14],'typedRecords':pins[str(op)]}
    frec={r['fields'][0]:r['fields'][1:] for r in records if r['tag']=='FREC'}
    blockers=[]
    for f,rows in fs.items():
        ff=frec[f]; n=ff[3]; params=ff[5:5+n]; ops=collections.Counter(r[1] for r in rows)
        blockers.append({'function':f,'params':params,'resultType':ff[4],
            'scalarSignature':ff[4] in [1,2] and all(t in [1,2] for t in params),
            'vectorParameter':4 in params,'boolResult':ff[4]==2,
            'outsideScalarDAGOpcodeClasses':sorted(set(ops)-{1,2,3,4,5,6,7,8,9,19}),
            'callSites':ops[13],'runtimeSites':ops[14],'branchSites':ops[10]+ops[11]+ops[12],
            'fuelSites':ops[18],'sirInstructions':len(rows)})
    report['savedTypedHistorical'][name]['currentScalarDAGNecessaryGuardDiagnostic']={
        'notActualAdmission':True,'boolAlreadyAllowedByCurrentDiType':True,
        'functions':blockers,'scalarSignatureFunctions':sum(x['scalarSignature'] for x in blockers),
        'vectorParameterFunctions':sum(x['vectorParameter'] for x in blockers),
        'boolResultFunctions':sum(x['boolResult'] for x in blockers),
        'scalarSignatureWithControlOrFuelOrRT':sum(x['scalarSignature'] and bool(x['outsideScalarDAGOpcodeClasses']) for x in blockers)}
    cp=W/'vector-param-C-remote-rebuild-plan-v1-controls/package/inputs/upstream/src'/name/f'lib{name}.c'
    text=pin(cp).decode(); clean=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
    report['CSource'][name]={'switchTokens':len(re.findall(r'\bswitch\s*\(',clean)),
        'caseTokens':len(re.findall(r'\bcase\s+[^:]+:',clean)),
        'whileTokens':len(re.findall(r'\bwhile\s*\(',clean)),
        'qualification':'Lexical source census, no emitted machine dispatch or cost attribution'}
for p in [R/'seed/00-ns.kotoba',R/'seed/30-lower.kotoba',R/'seed/41-a64gen.kotoba',R/'seed/42-layout.kotoba',
    W/'vector-typed-observer-native-v8/unity-observer.kotoba',
    W/'vector-leaf-straight-read-cache-full19-selfbuild40-plan-v1-native-controls/run-outputs/G3.bin',
    W/'vector-leaf-straight-read-cache-current19-build52-go-v2-root/build52-acceptance.json'] :pin(p)
(OUT/'census.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({n:{k:v for k,v in report['currentSources'][n].items() if k not in ['simpleReadOnlyDispatchFunctions','sameSlotFalseChainsAtLeast2']} for n in ['statemate','nsichneu']},indent=2))
