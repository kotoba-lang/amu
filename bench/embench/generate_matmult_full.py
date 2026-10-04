#!/usr/bin/env python3
# BOOTSTRAP-TOOL: complete RNG initialization, copies and 20x20 multiplication.
import argparse,pathlib,hashlib,json,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args();pin='a52a60dfc82e5d919f5c4507543e48232d6621a16e95e7c04f642a5f909b28ae';s=a.upstream.read_text()
if hashlib.sha256(a.upstream.read_bytes()).hexdigest()!=pin:raise SystemExit('unreviewed matmult profile')
block=re.search(r'matrix exp = \{(.*?)\n  \};',s,re.S)
if block is None:raise SystemExit('unreviewed matrix verifier')
expected=[int(x) for x in re.findall(r'\d+',block.group(1))]
if len(expected)!=400:raise SystemExit('unreviewed matrix dimensions')
def table(xs,start=0):
 if len(xs)==1:return str(xs[0])
 n=len(xs)//2;return '(if (< i '+str(start+n)+') '+table(xs[:n],start)+' '+table(xs[n:],start+n)+')'
source='''(ns embench.matmult-full (:export [bench observe bounds-probe]))
;; Complete original RNG/init/copy/20x20x20 multiplication and final verifier.
;; Copyright 2013-2019 Embecosm/Bristol; SPDX-License-Identifier: GPL-3.0-or-later.
(defn- expected [i :i64] :i64 '''+table(expected)+''')
(defn- put [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))
(defn- init-refs [v :vector-i64 i :i64 seed :i64] :vector-i64
 (if (= i 800) (put v 2000 seed)
  (let [next (rem (+ (* seed 133) 81) 8095)] (init-refs (put v i next) (+ i 1) next))))
(defn- copy-inputs [v :vector-i64 i :i64] :vector-i64
 (if (= i 800) v (copy-inputs (put v (+ 800 i) (vector-at v i)) (+ i 1))))
(defn- dot [v :vector-i64 row :i64 col :i64 k :i64 sum :i64] :i64
 (if (= k 20) sum
  (dot v row col (+ k 1) (+ sum (* (vector-at v (+ 800 (+ (* row 20) k))) (vector-at v (+ 1200 (+ (* k 20) col))))))))
(defn- multiply [v :vector-i64 i :i64] :vector-i64
 (if (= i 400) v
  (let [value (dot v (quot i 20) (rem i 20) 0 0)] (multiply (put v (+ 1600 i) value) (+ i 1)))))
(defn- bodies [v :vector-i64 n :i64 i :i64] :vector-i64
 (if (= i n) v (bodies (multiply (copy-inputs v 0) 0) n (+ i 1))))
(defn- state [n :i64] :vector-i64 (bodies (init-refs (vector-alloc 2001) 0 0) n 0))
(defn- verify [v :vector-i64 i :i64] :bool
 (if (= i 400) true (and (= (vector-at v (+ 1600 i)) (expected i)) (verify v (+ i 1)))))
(defn bench [n :i64] :i64 (if (= n 0) 0 (if (verify (state n) 0) 1 0)))
(defn observe [encoded :i64] :i64 (vector-at (state (quot encoded 2048)) (rem encoded 2048)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 2001) i))
'''
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'matmult-full.kotoba').write_text(source)
c='''/* BOOTSTRAP-TOOL: original initialization, body, verifier and actual globals. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/src/matmult-int/matmult-int.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t bench(int64_t n,EXTRA){if(n==0)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t observe(int64_t encoded,EXTRA){int n=encoded/2048,i=encoded%2048;memset(ArrayA,0,sizeof(ArrayA));memset(ArrayB,0,sizeof(ArrayB));memset(ResultArray,0,sizeof(ResultArray));initialise_benchmark();if(n)benchmark_body(1,n);
 if(i<400)return ArrayA_ref[i/20][i%20];if(i<800){i-=400;return ArrayB_ref[i/20][i%20];}if(i<1200){i-=800;return ArrayA[i/20][i%20];}if(i<1600){i-=1200;return ArrayB[i/20][i%20];}if(i<2000){i-=1600;return ResultArray[i/20][i%20];}if(i==2000)return Seed;return INT64_MIN;}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'sourcePins':{'matmult-int.c':pin},'dimension':20,'rngStepsPerInitialization':800,'inputCellsCopiedPerBody':800,'multiplyAddsPerBody':8000,'workspaceCells':2001,'iterations':[0,1,2,17,32],'verification':'400 original cells once after batch'},indent=2)+'\n')
