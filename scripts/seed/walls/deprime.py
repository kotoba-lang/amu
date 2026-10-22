#!/usr/bin/env python3
"""deprime.py <file>: rename symbols ending in ' (t', last'') to t-p, last-pp outside strings/comments/char literals.
The seed's lexer reads ' only as quote (E1005); Clojure reads it as a symbol constituent."""
import re,sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()
out=[];i=0;n=len(s);names={}
SYM=re.compile(r"[A-Za-z0-9*+!\-_?<>=/.$&%]+('+)")
existing=set(re.findall(r"[A-Za-z0-9*+!\-_?<>=/.$&%]+",s))
while i<n:
    c=s[i]
    if c=='"':
        j=i+1
        while s[j]!='"':
            j+=2 if s[j]=='\\' else 1
        out.append(s[i:j+1]); i=j+1; continue
    if c==';':
        j=s.find('\n',i); j=n if j<0 else j
        out.append(s[i:j]); i=j; continue
    if c=='\\' :
        out.append(s[i:i+2]); i+=2; continue
    m=SYM.match(s,i)
    if m and (i==0 or not re.match(r"[A-Za-z0-9*+!\-_?<>=/.$&%']",s[i-1])) and m.group(0)[0] not in "0123456789":
        tok=m.group(0); base=tok.rstrip("'"); k=len(tok)-len(base)
        new=base+'-'+'p'*k
        if new in existing and tok not in names: sys.exit('collision '+new)
        names[tok]=new; out.append(new); i=m.end(); continue
    out.append(c); i+=1
open(p,'w',encoding='utf-8').write(''.join(out))
print(len(names),'renamed:',' '.join(sorted(names)),file=sys.stderr)
