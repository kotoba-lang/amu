#!/usr/bin/env python3
"""primrw.py <file> [ops...]: rewrite grammar primitives the seed's source route lacks into seed-admissible equivalents
(same value in the language: both sides refuse an empty needle / separator).
  (vector-new)            -> (vector-alloc 0)
  (vector-new a b ..)     -> (vector-conj (vector-conj (vector-alloc 0) a) b) ..
  (string-contains? h n)  -> (>= (string-index-of h n) 0)
  (unwrap-form x) etc    -> x   [only when asked: the ADR 0363 import is the plain value]
  (unwrap! x p)           -> (try x (catch e (reject-form! p)))   [only when asked: an ADR 0363 import aborts itself]
Text outside the rewritten forms is untouched (comments, strings, layout)."""
import sys,re
p=sys.argv[1]; ops=set(sys.argv[2:]) or {'vector-new','string-contains?'}
s=open(p,encoding='utf-8').read()
DELIM=set('()[]{}"; \t\n\r,')
def skip_ws(i):
    while i<len(s):
        c=s[i]
        if c in ' \t\n\r,': i+=1
        elif c==';':
            j=s.find('\n',i); i=len(s) if j<0 else j
        else: break
    return i
def sexpr_end(i):
    """i at start of a form; return index after it"""
    c=s[i]
    if c=='"':
        j=i+1
        while s[j]!='"': j+=2 if s[j]=='\\' else 1
        return j+1
    if c=='\\': 
        j=i+2
        while j<len(s) and s[j] not in DELIM: j+=1
        return j
    if c in "'`@~^": return sexpr_end(skip_ws(i+1))
    if c=='#':
        if s[i+1] in '({': return sexpr_end(i+1)
        if s[i+1]=='?':
            j=i+2
            if s[j]=='@': j+=1
            return sexpr_end(j)
        if s[i+1]=='"': return sexpr_end(i+1)
        if s[i+1]=='_': return sexpr_end(skip_ws(i+2))
    if c in '([{':
        close={'(':')','[':']','{':'}'}[c]; j=skip_ws(i+1)
        while s[j]!=close:
            j=skip_ws(sexpr_end(j))
        return j+1
    j=i
    while j<len(s) and s[j] not in DELIM: j+=1
    return j
def args_of(i):
    """i at '(' ; return (head, [arg texts], end)"""
    j=skip_ws(i+1); he=sexpr_end(j); head=s[j:he]; out=[]; k=skip_ws(he)
    while s[k]!=')':
        e=sexpr_end(k); out.append((k,e)); k=skip_ws(e)
    return head,out,k+1
def rw(i,e):
    """rewrite text s[i:e] (a form) recursively"""
    res=[];k=i
    while k<e:
        c=s[k]
        if c=='"' or c=='\\' :
            n=sexpr_end(k); res.append(s[k:n]); k=n; continue
        if c==';':
            n=s.find('\n',k); n=e if n<0 or n>e else n; res.append(s[k:n]); k=n; continue
        if c=='(':
            j=skip_ws(k+1); he=sexpr_end(j) if s[j] not in ')' else j; head=s[j:he]
            if head in ops:
                _,args,end=args_of(k)
                a=[rw(x,y) for x,y in args]
                if head=='vector-new':
                    t='(vector-alloc 0)'
                    for x in a: t='(vector-conj %s %s)'%(t,x)
                elif head=='string-contains?':
                    assert len(a)==2,(s[k:end])
                    t='(>= (string-index-of %s %s) 0)'%(a[0],a[1])
                elif head in ('unwrap-form','unwrap-string','unwrap-i64'):
                    assert len(a)==1,(s[k:end])
                    t=a[0]
                elif head=='unwrap!':
                    assert len(a)==2,(s[k:end])
                    t='(try %s (catch e (reject-form! %s)))'%(a[0],a[1])
                res.append(t); k=end; counts[head]=counts.get(head,0)+1; continue
        res.append(c); k+=1
    return ''.join(res)
counts={}
out=rw(0,len(s))
open(p,'w',encoding='utf-8').write(out)
print(counts,file=sys.stderr)
