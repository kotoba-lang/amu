"""select.py SRC [MAXTOK] -- private scalar leaf helpers eligible for inlining (names)."""
import sys,re
sys.argv=[sys.argv[0]]+sys.argv[1:]
src=sys.argv[1]; maxtok=int(sys.argv[2]) if len(sys.argv)>2 else 40
exec(open(__file__.replace('select.py','srcinline.py')).read().split('def main():')[0])
forms=parse(open(src).read()); out=[]
def toks(x): return sum(toks(i) for i in x[1]) if isinstance(x,tuple) else 1
def syms(x): return set().union(*[syms(i) for i in x[1]]) if isinstance(x,tuple) and x[1] else ({x} if not isinstance(x,tuple) else set())
for f in forms:
    if not (isinstance(f,tuple) and f[0]=='(' and f[1] and f[1][0]=='defn-'): continue
    name=f[1][1]; params=f[1][2][1]; rt=f[1][3] if len(f[1])>4 else None; body=f[1][-1]
    types=[p for p in params if p.startswith(':')]
    if not all(t in (':i64',':bool') for t in types) or rt not in (':i64',':bool'): continue
    s=syms(body)
    if name in s or 'loop' in s or 'recur' in s or any(x.startswith('vector') or x.startswith('string') or x.startswith('typed') for x in s): continue
    if toks(body)>maxtok: continue
    out.append(name)
print(' '.join(out))
