#!/usr/bin/env python3
# BOOTSTRAP-TOOL: AST-compose unchanged Montgomery helpers with full repeated body.
import argparse,ast,hashlib,json,pathlib,re,copy
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('port',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'mont64.c':'52b99661f046c6b647de144e968dfd12d192d54347010edca915c085ac9565aa'}
for f,s in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=s:raise SystemExit('unreviewed mont64 profile: '+f)
if hashlib.sha256(a.port.read_bytes()).hexdigest()!='a188ca9f79433931f2afe76679096d562c0ee2d58a6c67f8488f13a09171de20':raise SystemExit('unreviewed Montgomery helper component')
# Load only the trusted AST reader/writer definitions; never execute another CLI.
module=ast.parse((pathlib.Path(__file__).with_name('generate_picojpeg_coefficients.py')).read_text());helpers=[x for x in module.body if isinstance(x,(ast.ClassDef,ast.FunctionDef)) and x.name in ('Vec','read','emit')];exec(compile(ast.Module(body=helpers,type_ignores=[]),'checked AST reader','exec'))
forms=[f for f in read(a.port.read_text()) if f[0]=='defn-']
new='''
(defn- body-state [] :vector-i64
 (let [a 380896260630216687 b 1473642379452024179 m -366962936819156833
       reference (simple-result a b m) result (montgomery-result a b m)
       actual (vector-at result 0) inverse-check (vector-at result 1)
       errors (if (and (= actual reference) (= inverse-check 1)) 0 1)]
  [reference actual inverse-check errors]))
(defn- repeated [n :i64] :vector-i64
 (loop [i 0 last [0 0 0 0]] (if (= i n) last (recur (+ i 1) (body-state)))))
(defn bench [n :i64] :i64 (if (= n 0) 0 (if (= (vector-at (repeated n) 3) 0) 1 0)))
(defn observe [encoded :i64] :i64
 (let [n (quot encoded 4) field (rem encoded 4)] (vector-at (repeated n) field)))
(defn bounds-probe [i :i64] :i64 (vector-at [0 0 0 0] i))
'''
forms+=read(new);a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'mont64-full.kotoba').write_text('(ns embench.mont64-full (:export [bench observe bounds-probe]))\n;; Original complete mont64 body; verification once after repetition.\n;; SPDX-License-Identifier: GPL-3.0-or-later; Embecosm/Bristol 2013-2019.\n'+'\n'.join(map(emit,forms))+'\n')
s=(a.upstream/'mont64.c').read_text();start=s.index('benchmark_body(unsigned int lsf, unsigned int gsf)\n{');end=s.index('\nvoid\ninitialise_benchmark',start);body=s[start:end].replace('benchmark_body(','observed_body(',1);needle='\n  return errors;';inject='\n        snapshot[0]=p1;snapshot[1]=p;snapshot[2]=(2*hr*rinv-m*mprime==1);snapshot[3]=errors;';where='\n      }\n\n  return errors;'
if body.count(where)!=1:raise SystemExit('unreviewed mont64 observation boundary')
body=body.replace(where,inject+where,1)
c='''/* BOOTSTRAP-TOOL: unchanged original body/verifier; untimed snapshots. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include "../upstream/src/aha-mont64/mont64.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static uint64 snapshot[4];
static int
'''+body+'''
int64_t bench(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t observe(int64_t encoded,EXTRA){initialise_benchmark();observed_body(1,encoded/4);return (int64_t)snapshot[encoded%4];}
int64_t oracle_selfcheck(int64_t n,EXTRA){initialise_benchmark();int a=observed_body(1,n),b=benchmark_body(1,n);return a==b&&verify_benchmark(a)&&verify_benchmark(b)&&snapshot[0]==snapshot[1]&&snapshot[2]==1&&snapshot[3]==0;}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'sourcePins':pins,'helperComponentSha256':hashlib.sha256(a.port.read_bytes()).hexdigest(),'iterations':[0,1,2,17,32],'observableFields':['simple result','Montgomery result','inverse check','errors'],'verification':'once after batch'},indent=2)+'\n')
