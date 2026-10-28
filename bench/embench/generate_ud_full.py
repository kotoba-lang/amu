#!/usr/bin/env python3
# BOOTSTRAP-TOOL: full original UD initialization, LU, substitutions and repeat.
import argparse,pathlib,json,hashlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args();pin='eb9cb63f7a5d081229c3de201ec83f24ed535cb95414804ef355c3b1e4626f2b'
if hashlib.sha256(a.upstream.read_bytes()).hexdigest()!=pin:raise SystemExit('unreviewed UD profile')
s=a.upstream.read_text()
source='''(ns embench.ud-full (:export [bench observe bounds-probe]))
;; Original 6 active equations, 20x20 storage, LU and both substitutions.
;; Copyright 2014-2019 Embecosm/Bristol; SPDX-License-Identifier: GPL-3.0-or-later.
(defn- put [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))
(defn- at [v :vector-i64 row :i64 col :i64] :i64 (vector-at v (+ (* row 20) col)))
(defn- init [v :vector-i64 row :i64 col :i64 sum :i64] :vector-i64
 (if (= row 6) v
  (if (= col 6) (init (put v (+ 400 row) sum) (+ row 1) 0 0)
   (let [base (+ row col 2) value (if (= row col) (* base 2) base)]
    (init (put v (+ (* row 20) col) value) row (+ col 1) (+ sum value))))))
(defn- lower-sum [v :vector-i64 row :i64 col :i64 k :i64 sum :i64] :i64
 (if (= k col) sum (lower-sum v row col (+ k 1) (- sum (* (at v row k) (at v k col))))))
(defn- lower [v :vector-i64 i :i64 j :i64] :vector-i64
 (if (= j 6) v
  (let [w (lower-sum v j i 0 (at v j i)) value (quot w (at v i i))]
   (lower (put v (+ (* j 20) i) value) i (+ j 1)))))
(defn- upper-sum [v :vector-i64 i :i64 j :i64 k :i64 sum :i64] :i64
 (if (> k i) sum (upper-sum v i j (+ k 1) (- sum (* (at v (+ i 1) k) (at v k j))))))
(defn- upper [v :vector-i64 i :i64 j :i64] :vector-i64
 (if (= j 6) v
  (let [value (upper-sum v i j 0 (at v (+ i 1) j))]
   (upper (put v (+ (* (+ i 1) 20) j) value) i (+ j 1)))))
(defn- lu [v :vector-i64 i :i64] :vector-i64
 (if (= i 5) v (lu (upper (lower v i (+ i 1)) i (+ i 1)) (+ i 1))))
(defn- forward-sum [v :vector-i64 i :i64 j :i64 w :i64] :i64
 (if (= j i) w (forward-sum v i (+ j 1) (- w (* (at v i j) (vector-at v (+ 440 j)))))))
(defn- forward [v :vector-i64 i :i64] :vector-i64
 (if (= i 6) v
  (let [w (forward-sum v i 0 (vector-at v (+ 400 i)))] (forward (put v (+ 440 i) w) (+ i 1)))))
(defn- backward-sum [v :vector-i64 i :i64 j :i64 w :i64] :i64
 (if (= j 6) w (backward-sum v i (+ j 1) (- w (* (at v i j) (vector-at v (+ 420 j)))))))
(defn- backward [v :vector-i64 i :i64] :vector-i64
 (if (< i 0) v
  (let [w (backward-sum v i (+ i 1) (vector-at v (+ 440 i))) value (quot w (at v i i))]
   (backward (put v (+ 420 i) value) (- i 1)))))
(defn- body [v :vector-i64] :vector-i64 (put (backward (forward (lu (init v 0 0 0) 0) 0) 5) 540 0))
(defn- bodies [v :vector-i64 n :i64 i :i64] :vector-i64
 (if (= i n) v (bodies (body v) n (+ i 1))))
(defn- state [n :i64] :vector-i64 (bodies (vector-alloc 541) n 0))
(defn- expected [i :i64] :i64 (if (< i 2) 0 (if (< i 5) 1 (if (= i 5) 2 0))))
(defn- verify [v :vector-i64 i :i64] :bool
 (if (= i 20) (= (vector-at v 540) 0)
  (and (= (vector-at v (+ 420 i)) (expected i)) (verify v (+ i 1)))))
(defn bench [n :i64] :i64 (if (= n 0) 0 (if (verify (state n) 0) 1 0)))
(defn observe [encoded :i64] :i64 (vector-at (state (quot encoded 1024)) (rem encoded 1024)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 541) i))
'''
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'ud-full.kotoba').write_text(source)
start=s.index('int ludcmp(int nmax, int n)\n{');body=s[start:];end=body.index('\n\n\n/*');body=body[:end].replace('int ludcmp(','static int observed_ludcmp(',1);needle='  return(0);'
if body.count(needle)!=1:raise SystemExit('unreviewed UD observation boundary')
body=body.replace(needle,'  for(int observer_i=0;observer_i<6;observer_i++)snapshot_y[observer_i]=y[observer_i];\n'+needle,1)
start=s.index('benchmark_body(unsigned int lsf, unsigned int gsf)\n{');end=s.index('\nint ludcmp(int nmax, int n)\n{',start);benchmark=s[start:end].replace('benchmark_body(','observed_body(',1).replace('chkerr = ludcmp(nmax,n);','chkerr = observed_ludcmp(nmax,n);',1)
c='''/* BOOTSTRAP-TOOL: original C body, with only initialized y captured. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/src/ud/libud.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static long snapshot_y[6];
'''+body+'\nstatic int\n'+benchmark+'''
static int64_t field(int cell){if(cell<400)return a[cell/20][cell%20];if(cell<420)return b[cell-400];if(cell<440)return x[cell-420];if(cell<446)return snapshot_y[cell-440];if(cell==540)return chkerr;return INT64_MIN;}
int64_t bench(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t observe(int64_t encoded,EXTRA){memset(a,0,sizeof(a));memset(b,0,sizeof(b));memset(x,0,sizeof(x));memset(snapshot_y,0,sizeof(snapshot_y));chkerr=0;if(encoded/1024)observed_body(1,encoded/1024);return field(encoded%1024);}
int64_t oracle_selfcheck(int64_t n,EXTRA){int r=observed_body(1,n);long saved_a[20][20],saved_b[20],saved_x[20];memcpy(saved_a,a,sizeof(a));memcpy(saved_b,b,sizeof(b));memcpy(saved_x,x,sizeof(x));int s=benchmark_body(1,n);return r==s&&verify_benchmark(r)&&verify_benchmark(s)&&memcmp(saved_a,a,sizeof(a))==0&&memcmp(saved_b,b,sizeof(b))==0&&memcmp(saved_x,x,sizeof(x))==0;}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'sourcePins':{'libud.c':pin},'activeN':5,'activeEquations':6,'matrixStorage':400,'workspaceCells':541,'fields':list(range(446))+[540],'iterations':[0,1,2,17,32],'excluded':'unused/uninitialized C local y[6..99]','verification':'once after all bodies'},indent=2)+'\n')
