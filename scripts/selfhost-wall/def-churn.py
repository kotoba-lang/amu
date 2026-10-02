#!/usr/bin/env python3
# def-churn.py <repo> <path,path,...> <n-commits>: the fraction of top-level definitions (by name) whose read form is
# unchanged between consecutive commits touching PATHS. BOOTSTRAP-TOOL; docs/selfhost-memory-plan-20261002.md item 4.
import subprocess, sys, hashlib, os
sys.setrecursionlimit(100000)
import importlib.util
_spec = importlib.util.spec_from_file_location('form_census', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'form-census.py'))
_fc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_fc); read_all = _fc.read_all
repo, paths, n = sys.argv[1], sys.argv[2].split(','), int(sys.argv[3])
commits = subprocess.run(['git','-C',repo,'log','--format=%h','-n',str(n),'--']+paths,capture_output=True,text=True).stdout.split()
commits.reverse()
def h(f): return hashlib.sha1(repr(f).encode()).hexdigest()
def defs(c):
    out={}
    for p in paths:
        t=subprocess.run(['git','-C',repo,'show',f'{c}:{p}'],capture_output=True,text=True).stdout
        try: forms=read_all(t)
        except Exception: continue
        for f in forms:
            if f[0]=='seq' and f[1] and f[1][0][0]=='symbol' and f[1][0][1] in ('defn','defn-','def','def-','defmacro') and len(f[1])>1:
                out[repr(f[1][1])]=h(f)
    return out
prev=None; rows=[]
for c in commits:
    d=defs(c)
    if prev is not None and d:
        same=sum(1 for k,v in d.items() if prev.get(k)==v)
        rows.append((c,len(d),same))
    prev=d
fr=sorted(s/t for _,t,s in rows)
print('commits',len(rows),'defs(last)',rows[-1][1] if rows else 0)
print('unchanged fraction: median %.4f  p10 %.4f  min %.4f  mean %.4f'%(fr[len(fr)//2],fr[len(fr)//10],fr[0],sum(fr)/len(fr)))
first=defs(commits[0]); last=prev
print('first->last (%d commits): %.3f unchanged'%(len(commits)-1, sum(1 for k,v in last.items() if first.get(k)==v)/len(last)))
for c,t,s in rows:
    if s/t<0.9: print('low',c,t,s)
