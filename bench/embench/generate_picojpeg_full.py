#!/usr/bin/env python3
# BOOTSTRAP-TOOL: AST-compose checked transforms with complete repeated original fixture.
import argparse,pathlib,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('transform',type=pathlib.Path);p.add_argument('headers_bridge',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'libpicojpeg.c':'ed1fb932e9c2c15796bbe6caea8e2e53e61d1349fae4afc1d71847eeebb9185d','picojpeg.h':'50dbd519c3e7b5732cc2e58d9e47195a3e5652f5d14f9d997f102b844e64db36','picojpeg_test.c':'fab1ba5e93f854512ff10910e2b304b20f42a6d579db1793c7aa87e398188f8a'}
for f,d in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed picojpeg full profile: '+f)
class Vec(list):pass
def read(s):
 ts=[t for t in re.findall(r';[^\n]*|"(?:\\.|[^"\\])*"|[()\[\]]|[^\s()\[\];]+',s) if not t.startswith(';')];pos=0
 def form():
  nonlocal pos
  t=ts[pos];pos+=1
  if t in ('(','['):
   end=')' if t=='(' else ']';xs=[]
   while ts[pos]!=end:xs.append(form())
   pos+=1;return xs if t=='(' else Vec(xs)
  if t in (')',']'):raise ValueError('unbalanced forms')
  return t
 out=[]
 while pos<len(ts):out.append(form())
 return out
def emit(x):
 if isinstance(x,list):return ('[' if isinstance(x,Vec) else '(')+' '.join(map(emit,x))+(']' if isinstance(x,Vec) else ')')
 return x
forms=[f for f in read(a.transform.read_text()) if f[0]=='defn-']
s=(a.upstream/'picojpeg_test.c').read_text()
def tree(xs,start=0):
 if len(xs)==1:return str(xs[0])
 n=len(xs)//2;return '(if (< i '+str(start+n)+') '+tree(xs[:n],start)+' '+tree(xs[n:],start+n)+')'
for color in ('r','g','b'):
 values=[int(x) for x in re.findall(r'\d+',re.search(color+r'_ref\[64\] = \{(.*?)\};',s,re.S).group(1))]
 if len(values)!=64:raise SystemExit('unreviewed verifier shape')
 forms+=read('(defn- verify-'+color+' [i :i64] :i64 '+tree(values)+')')
new=r"""
(defn- reset-reader [v :vector-i64 i :i64] :vector-i64
 (if (= i 263) v (reset-reader (put v i 0) (+ i 1))))
(defn- reset-init [v :vector-i64 i :i64] :vector-i64
 (if (= i 1407) (put8 (reset-reader v 256) 1520 0) (reset-init (put v i 0) (+ i 1))))
(defn- complete-body [v :vector-i64] :vector-i64 (transform-state (reset-init v 1400) 169 3))
(defn- repeated-bodies [v :vector-i64 n :i64 i :i64] :vector-i64
 (if (= i n) v (repeated-bodies (complete-body v) n (+ i 1))))
(defn- verify-pixels [v :vector-i64 i :i64] :bool
 (if (= i 64) true
  (and (= (vector-at v (+ 2048 i)) (verify-r i))
       (= (vector-at v (+ 2304 i)) (verify-g i))
       (= (vector-at v (+ 2560 i)) (verify-b i))
       (verify-pixels v (+ i 1)))))
(defn bench [n :i64] :i64
 (if (or (< n 1) (> n 32)) 0
  (let [v (repeated-bodies (vector-alloc 4096) n 0)]
   (if (and (= (vector-at v 1413) 0) (= (vector-at v 1520) 1) (verify-pixels v 0)) 1 0))))
(defn repeated-state [encoded :i64] :i64
 (let [n (quot encoded 4096) cell (rem encoded 4096)]
  (vector-at (repeated-bodies (vector-alloc 4096) n 0) cell)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 4096) i))
"""
forms+=read(new)
if len({f[1] for f in forms})!=len(forms):raise SystemExit('duplicate definitions')
a.directory.mkdir(parents=True,exist_ok=True)
(a.directory/'picojpeg-full.kotoba').write_text('(ns embench.picojpeg-full (:export [bench repeated-state bounds-probe]))\n;; Original 570-byte 51x64 YH1V1 fixture, all 56 MCUs, reused owned workspace.\n;; Copyright 2014-2019 Embecosm/Bristol; picojpeg Rich Geldreich, public domain.\n'+'\n'.join(map(emit,forms))+'\n')
shutil.copy2(a.headers_bridge,a.directory/'headers-bridge.c')
fields=list(range(263))+list(range(1510,1513))+[1413,1520]+list(range(1536,1600))+list(range(2048,2816))
c=r"""/* BOOTSTRAP-TOOL: unchanged original full body and verifier. */
#define observe observe_headers
#include "headers-bridge.c"
#undef observe
static int64_t full_value(int cell){if(cell>=1536&&cell<1600)return gCoeffBuf[cell-1536];if(cell>=2048&&cell<2304)return gMCUBufR[cell-2048];if(cell>=2304&&cell<2560)return gMCUBufG[cell-2304];if(cell>=2560&&cell<2816)return gMCUBufB[cell-2560];return cellvalue(cell);}
int64_t bench(int64_t n,EXTRA){if(n<1||n>32)return 0;benchmark_body(1,n);return verify_benchmark(0);}
int64_t repeated_state(int64_t encoded,EXTRA){int n=encoded/4096,cell=encoded%4096;if(encoded<0||n<1||n>32)return INT64_MIN;
 reset();memset(gCoeffBuf,0,sizeof(gCoeffBuf));memset(gMCUBufR,0,sizeof(gMCUBufR));memset(gMCUBufG,0,sizeof(gMCUBufG));memset(gMCUBufB,0,sizeof(gMCUBufB));benchmark_body(1,n);lastStatus=pjpeg_decode_mcu();if(!verify_benchmark(0)||lastStatus!=PJPG_NO_MORE_BLOCKS)return INT64_MIN;return full_value(cell);}
"""
(a.directory/'c-bridge.c').write_text(c)
(a.directory/'profile.json').write_text(json.dumps({'status':'complete-original-active-profile','sourcePins':pins,'transformSha256':hashlib.sha256(a.transform.read_bytes()).hexdigest(),'headersBridgeSha256':hashlib.sha256(a.headers_bridge.read_bytes()).hexdigest(),'mcus':56,'blocks':168,'repeatedFields':fields,'iterations':[1,2,17,32],'workspaceCells':4096,'nativeAllocsPerCall':1,'inputBytes':570},indent=2)+'\n')
