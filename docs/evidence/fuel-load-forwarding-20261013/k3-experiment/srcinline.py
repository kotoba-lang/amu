"""srcinline.py SRC OUT NAME... -- upper-bound experiment: source-level inlining of the named defn-.
Calls (f a1..an) become (let [p1' a1 ..] body') with fresh parameter names; integer-literal and
plain-symbol arguments are substituted directly when the parameter is not shadowed in the body.
It drops the callee's entry fuel charge, so it only estimates the ceiling of SIR inlining."""
import sys,re,itertools
TOK=re.compile(r'\s+|;[^\n]*|"(?:\\.|[^"\\])*"|[()\[\]{}]|[^\s()\[\]{}]+')
def parse(s):
    toks=[t for t in TOK.findall(s) if t.strip() and not t.startswith(';')]
    pos=0
    def rd():
        nonlocal pos
        t=toks[pos]; pos+=1
        if t in '([{':
            close={'(':')','[':']','{':'}'}[t]; out=[]
            while toks[pos]!=close: out.append(rd())
            pos+=1; return (t,out)
        return t
    forms=[]
    while pos<len(toks): forms.append(rd())
    return forms
def show(x):
    if isinstance(x,tuple):
        o,items=x; c={'(':')','[':']','{':'}'}[o]
        return o+' '.join(show(i) for i in items)+c
    return x
fresh=itertools.count()
def subst(x,m):
    if isinstance(x,tuple): return (x[0],[subst(i,m) for i in x[1]])
    return m.get(x,x)
def binds(x,names):
    """True when any of names is rebound inside x (let/loop/fn binding vectors)."""
    if isinstance(x,tuple):
        it=x[1]
        if x[0]=='(' and it and it[0] in ('let','loop','fn') and len(it)>1 and isinstance(it[1],tuple):
            bv=it[1][1]
            if any(b in names for b in bv[0::2] if isinstance(b,str)) or any(b in names for b in bv if isinstance(b,str)): return True
        return any(binds(i,names) for i in it)
    return False
def main():
    src,out,*names=sys.argv[1:]
    forms=parse(open(src).read()); defs={}
    for f in forms:
        if isinstance(f,tuple) and f[0]=='(' and f[1] and f[1][0]=='defn-' and f[1][1] in names:
            params=f[1][2][1]; ps=[p for p in params if not p.startswith(':')]
            defs[f[1][1]]=(ps,f[1][-1])
    def rw(x):
        if isinstance(x,tuple):
            items=[rw(i) for i in x[1]]
            if x[0]=='(' and items and items[0] in defs and len(items)-1==len(defs[items[0]][0]):
                ps,body=defs[items[0]]; args=items[1:]; m={}; bv=[]
                safe=not binds(body,set(ps))
                for p,a in zip(ps,args):
                    if safe and not isinstance(a,tuple) and (re.fullmatch(r'-?\d+',a) or (re.fullmatch(r'[a-z][\w\-?!*]*',a) and not binds(body,{a}))) and a not in ('true','false'):
                        m[p]=a
                    else:
                        q=f'{p}__i{next(fresh)}'; m[p]=q; bv+= [q,a]
                b=rw(subst(body,m))
                return ('(',['let',('[',bv),b]) if bv else b
            return (x[0],items)
        return x
    res=[]
    for f in forms:
        if isinstance(f,tuple) and f[0]=='(' and f[1] and f[1][0]=='defn-' and f[1][1] in defs:
            res.append(f)  # keep the callee definition itself
        else: res.append(rw(f))
    open(out,'w').write('\n'.join(show(f) for f in res)+'\n')
main()
