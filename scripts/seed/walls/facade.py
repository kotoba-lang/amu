#!/usr/bin/env python3
"""facade.py <frontend.cljk> [keep,names]: make the Kotoba reading of the kotoba.compiler.frontend facade admissible.
Every alias def whose target is not in its module's Kotoba export becomes host-only (#?(:kotoba nil :default ..));
a Kotoba-only private alias (#?(:kotoba (def ^:private ..))) is dropped from the Kotoba reading the same way (nothing in
this file reads it: the facade has no function of its own). The Kotoba export list keeps the names still defined."""
import re,sys
p=sys.argv[1]; extra=set(sys.argv[2].split(',')) if len(sys.argv)>2 else set()
base=p.rsplit('/',1)[0]+'/'
s=open(p).read()
nsr=dict(re.findall(r'\[kotoba\.compiler\.frontend\.([a-z\-]+) :as ([a-z\-]+)\]',s))
exps={}
for mod,a in nsr.items():
    t=open(base+'frontend/'+mod.replace('-','_')+'.cljk').read()
    m=re.search(r':kotoba/export \[([^\]]*)\]',t)
    exps[a]=set(m.group(1).split()) if m else set()
L=s.split('\n'); dropped=[]; kept=[]
for i,l in enumerate(L):
    m=re.match(r'^(#\?\(:kotoba )?\(def ((?:\^:\S+ )*)(\S+) ([a-z\-]+)/(\S+?)\)(\))?$',l)
    if not m: continue
    kot,meta,name,a,tgt=m.group(1),m.group(2),m.group(3),m.group(4),m.group(5)
    ok = (tgt in exps.get(a,())) or name in extra
    private = bool(meta) and 'private' in meta
    if ok and not private: kept.append(name); continue
    if kot: L[i]=';; (Kotoba reading: no private alias; the facade has no function that reads one) '+l[len('#?(:kotoba '):-1]
    else: L[i]='#?(:kotoba nil :default '+l+')'
    dropped.append(name)
s='\n'.join(L)
m=re.search(r':kotoba/export \[([^\]]*)\]',s)
names=m.group(1).split()
gone=[n for n in names if n in dropped and n not in kept]
newexp=[n for n in names if n not in gone]
s=s[:m.start(1)]+' '.join(newexp)+s[m.end(1):]
open(p,'w').write(s)
print('kept',len(kept),'dropped',len(dropped),'export',len(names),'->',len(newexp),file=sys.stderr)
print('dropped from export:',' '.join(gone),file=sys.stderr)

# ---- pass 2: a kept alias whose target is a FUNCTION in its module's Kotoba reading becomes a forwarding defn there
# (stage-0: "constant alias must name a declared constant" -- a def may alias a constant, not a function)
def sexpr_end(t,i):
    c=t[i]
    if c=='"':
        j=i+1
        while t[j]!='"': j+=2 if t[j]=='\\' else 1
        return j+1
    if c in '([{':
        close={'(':')','[':']','{':'}'}[c]; j=i+1
        while True:
            while t[j] in ' \t\n,': j+=1
            if t[j]==close: return j+1
            j=sexpr_end(t,j)
    j=i
    while j<len(t) and t[j] not in ' \t\n,()[]{}"': j+=1
    return j
def kotoba_sig(t,name):
    for m in re.finditer(r'\(defn '+re.escape(name)+r' \[',t):
        i=m.end()-1; e=sexpr_end(t,i); params=t[i:e]
        k=e
        while t[k] in ' \t\n': k+=1
        if t[k]=='"' : continue
        re_=sexpr_end(t,k); ret=t[k:re_]
        if ret.startswith('(') : continue
        return params,ret
    return None
s=open(p).read(); L=s.split('\n'); fw=[]
for i,l in enumerate(L):
    m=re.match(r'^\(def (\S+) ([a-z\-]+)/(\S+?)\)$',l)
    if not m: continue
    name,a,tgt=m.groups()
    mod=[k for k,v in nsr.items() if v==a][0]
    t=open(base+'frontend/'+mod.replace('-','_')+'.cljk').read()
    sig=kotoba_sig(t,tgt)
    if not sig: continue
    params,ret=sig
    inner=params[1:-1]; toks=[]; j=0
    while j<len(inner):
        while j<len(inner) and inner[j] in ' \t\n,': j+=1
        if j>=len(inner): break
        e=sexpr_end(inner,j); toks.append(inner[j:e]); j=e
    args=toks[0::2]
    call='(%s/%s%s)'%(a,tgt,''.join(' '+x for x in args))
    L[i]='#?(:kotoba (defn %s %s %s %s)\n   :default %s)'%(name,params,ret,call,l)
    fw.append(name)
open(p,'w').write('\n'.join(L))
print('forwarding defns',len(fw),' '.join(fw),file=sys.stderr)
