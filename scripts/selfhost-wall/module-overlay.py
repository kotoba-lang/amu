#!/usr/bin/env python3
"""Check ONE frontend module of kotoba-sema on the project route before its dependencies are Kotoba-clean.

usage: SEMA=<kotoba-sema> OUT=<dir> module-overlay.py MODULE:root,root,... [MODULE:...]
Writes OUT/src (a copy of kotoba-sema/src) in which each MODULE is replaced by a minimal module holding only the :kotoba definitions
(and what they call inside that module) named after the colon, with the refers to the real base / kernel-region / closure-types it
needs. Then: WALL_CP=<classpath with OUT/src in place of kotoba-sema/src> check-native.sh OUT/src/kotoba/compiler/frontend/<module under test>.cljk.
The stand-alone differential guest (ds-gen.sh) is one file; this is the same code as a linked module (ns, :refer, export surface)."""
import re,glob,os,sys
HERE=os.path.dirname(os.path.abspath(__file__))
src=open(HERE+'/tm-gen.py').read().replace('\nmain()\n','\n')
ns={};exec(src,ns)
form_end=ns['form_end'];skip_ws=ns['skip_ws'];expand=ns['expand']
SEMA=os.environ.get('SEMA','/Users/junkawasaki/github/kotoba-lang/kotoba-sema')
S=SEMA+'/src/kotoba/compiler/'
TOK=re.compile(r"[^\s()\[\]{}\"',`~@^]+")
def strip(t): return re.sub(r'"(?:[^"\\]|\\.)*"','',re.sub(r';[^\n]*','',t))
def toplevel(s):
    forms={};order=[];i=0;n=len(s)
    while True:
        i=skip_ws(s,i)
        if i>=n:break
        if s[i]=='(':
            e=form_end(s,i);t=s[i:e];i=e
            m=re.match(r'\((defn-?|def)\s+(\^:?[a-z-]+\s+)*([^\s\)\[]+)',t)
            if m: forms[m.group(3)]=t;order.append(m.group(3))
        else:
            j=i
            while j<n and s[j] not in ' \t\r\n(':j+=1
            i=max(j,i+1)
    return forms,order
mods={}
for f in glob.glob(S+'frontend/*.cljk'):
    name=os.path.basename(f)[:-5]
    raw=open(f).read()
    nsend=form_end(raw,0)
    kv=expand(raw)
    forms,order=toplevel(kv[form_end(kv,skip_ws(kv,0)):])
    mods[name]=(raw[:nsend],forms,order)
def overlay(modname,roots,outdir,requires):
    nsf,forms,order=mods[modname]
    seen=[];
    def visit(x):
        if x in seen or x not in forms:return
        seen.append(x)
        for y in TOK.findall(strip(forms[x])):
            if y in forms: visit(y)
    for r in roots: visit(r)
    body=[x for x in order if x in seen]
    nsname=re.match(r'\(ns\s+(\S+)',nsf).group(1)
    sch=re.search(r'#\?\(:kotoba \(:schemas.*?\}\)\)\)',nsf,re.S)
    # reuse the schemas block of the real ns form
    i=nsf.index('#?(:kotoba (:schemas')
    schemas=nsf[i:nsf.rindex(')')]  # up to the end of ns form (drop final paren)
    homes={}
    for mn in ['base','kernel_region','closure_types']:
        for d in mods[mn][1]: homes.setdefault(d,mn)
    used=set()
    for x in body: used|=set(TOK.findall(strip(forms[x])))
    byhome={}
    for t in sorted(used):
        if t not in forms and t in homes and homes[t]!=modname: byhome.setdefault(homes[t],[]).append(t)
    requires=requires+''.join(' [kotoba.compiler.frontend.%s :refer [%s]]'%(m.replace('_','-'),' '.join(v)) for m,v in byhome.items())
    text='(ns '+nsname+'\n  (:require [kotoba.lang.coll :as set] [kotoba.lang.text :as str] [kotoba.form :as form] [kotoba.compiler.value-type :as vt] [kotoba.compiler.frontend-tables :as tables]'+requires+')\n  '+schemas+')\n\n'
    text+='\n\n'.join(forms[x] for x in body)+'\n'
    os.makedirs(outdir+'/kotoba/compiler/frontend',exist_ok=True)
    open(outdir+'/kotoba/compiler/frontend/'+modname.replace('_','_')+'.cljk','w').write(text)
    return body
import shutil,subprocess
OUT=os.environ['OUT']
shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT)
shutil.copytree(SEMA+'/src',OUT+'/src')
tmp=OUT+'/overlay'
for spec in sys.argv[1:]:
    m,roots=spec.split(':'); overlay(m,roots.split(','),tmp,'')
    shutil.copy(tmp+'/kotoba/compiler/frontend/'+m+'.cljk',OUT+'/src/kotoba/compiler/frontend/'+m+'.cljk')
print('staged', OUT+'/src')
