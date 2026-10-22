#!/usr/bin/env python3
"""Generate the tm-diff guest module from kotoba-sema's frontend.cljk.

usage: tm-gen.py FRONTEND.cljk OUT.cljk

Expands the reader conditionals with the :kotoba feature (falling back to :default), picks the definitions named in
tm-names.txt (in that order) and appends tm-tail.cljk (the case dispatcher `tm-run`). The output is a stand-alone
Kotoba module that `amu check` and the KIR interpreter can run; it is the Kotoba route's reading of the same
functions the host runs, which is what tm-diff.cljs compares."""
import os, re, sys

def form_end(s,i):
    """index just past the balanced form starting at s[i]=='(' """
    depth=0;n=len(s);j=i
    while j<n:
        c=s[j]
        if c==';':
            while j<n and s[j]!='\n': j+=1
            continue
        if c=='"':
            j+=1
            while s[j]!='"':
                if s[j]=='\\': j+=1
                j+=1
            j+=1;continue
        if c=='\\':
            j+=2
            while j<n and s[j].isalnum(): j+=1
            continue
        if c in '([{': depth+=1
        elif c in ')]}':
            depth-=1
            if depth==0: return j+1
        j+=1
    raise Exception('unbalanced')

def skip_ws(s,i):
    while i<len(s):
        if s[i] in ' \t\r\n,': i+=1
        elif s[i]==';':
            while i<len(s) and s[i]!='\n': i+=1
        else: break
    return i
def elem_end(s,i):
    c=s[i]
    if c in '([{': return form_end(s,i)
    if c=='"':
        j=i+1
        while s[j]!='"':
            if s[j]=='\\': j+=1
            j+=1
        return j+1
    if c=='#':
        if s[i+1] in '({[': return form_end(s,i+1)
        if s[i+1]=='?':
            k=i+2
            if s[k]=='@': k+=1
            return form_end(s,k)
        if s[i+1]=='"': return elem_end(s,i+1)
        if s[i+1]=="'": return elem_end(s,i+2)
        return elem_end(s,i+1)
    if c in "'`~^@":
        return elem_end(s,i+1 if not s[i+1]=='@' else i+2)
    if c=='\\':
        j=i+2
        while j<len(s) and s[j].isalnum(): j+=1
        return j
    j=i
    while j<len(s) and s[j] not in ' \t\r\n,()[]{}";': j+=1
    return max(j,i+1)
def expand(s):
    out=[];i=0
    while True:
        m=s.find('#?(',i)
        if m<0: out.append(s[i:]);break
        out.append(s[i:m])
        end=form_end(s,m+2)
        j=m+3;pairs=[]
        while True:
            j=skip_ws(s,j)
            if s[j]==')': break
            fe=elem_end(s,j);feat=s[j:fe]
            j=skip_ws(s,fe);ve=elem_end(s,j);val=s[j:ve];j=ve
            pairs.append((feat,val))
        pick=None
        for f,v in pairs:
            if f==':kotoba': pick=v;break
        if pick is None:
            for f,v in pairs:
                if f==':default': pick=v;break
        # keep line count: pad newlines of dropped content
        chosen=pick if pick else ''
        orig=s[m:end]
        pad='\n'*(orig.count('\n')-chosen.count('\n')) if orig.count('\n')>chosen.count('\n') else ''
        out.append(chosen+pad)
        i=end
    return ''.join(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    # argv[1] may be a ':'-separated list of files (the facade first, then the split modules): later definitions win
    s = '\n'.join(expand(open(f).read()) for f in sys.argv[1].split(':') if f)
    i = 0; forms = {}; n = len(s)
    while True:
        i = skip_ws(s, i)
        if i >= n: break
        if s[i] == '(':
            e = form_end(s, i); f = s[i:e]; i = e
            m = re.match(r'\((defn-?|def)\s+(\^:[a-z-]+\s+)*([^\s\)]+)', f)
            if m: forms[m.group(3)] = f
        else:
            j = i
            while j < n and s[j] not in ' \t\r\n(': j += 1
            i = max(j, i + 1)
    names = open(os.environ.get('TM_NAMES') or os.path.join(here, 'tm-names.txt')).read().split()
    miss = [x for x in names if x not in forms]
    if miss:
        sys.exit('tm-gen: definitions not found in the :kotoba view: %s' % miss)
    hdr = """(ns kotoba.compiler.typemodel-probe
  {:kotoba/export [tm-run]}
  (:require [kotoba.form :as form] [kotoba.compiler.value-type :as vt])
  (:schemas {:form/r [:record :form/r [[:tag :i64] [:s :string] [:n :i64] [:k :keyword]
                                       [:kids [:list [:ref :form/r]]] [:span :i64] [:data :bytes]]]
             :form/rd [:record :form/rd [[:form [:ref :form/r]] [:pos :i64]]]
             :fe/err [:record :fe/err [[:msg :string] [:code :string] [:form [:ref :form/r]] [:phase :string] [:data [:ref :form/r]]]]}))

"""
    if os.environ.get('TM_HEADER'):
        hdr = open(os.environ['TM_HEADER']).read()
    tail = os.environ.get('TM_TAIL') or os.path.join(here, 'tm-tail.cljk')
    open(sys.argv[2], 'w').write(hdr + '\n\n'.join(forms[x] for x in names) + '\n' + open(tail).read())

main()
