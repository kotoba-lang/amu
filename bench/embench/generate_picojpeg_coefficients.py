#!/usr/bin/env python3
# BOOTSTRAP-TOOL: AST-compose checked headers with original DC/AC coefficient path.
import argparse,pathlib,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('headers',type=pathlib.Path);p.add_argument('headers_bridge',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'libpicojpeg.c':'ed1fb932e9c2c15796bbe6caea8e2e53e61d1349fae4afc1d71847eeebb9185d','picojpeg.h':'50dbd519c3e7b5732cc2e58d9e47195a3e5652f5d14f9d997f102b844e64db36','picojpeg_test.c':'fab1ba5e93f854512ff10910e2b304b20f42a6d579db1793c7aa87e398188f8a'}
for f,d in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed picojpeg coefficients profile: '+f)
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
forms=[f for f in read(a.headers.read_text()) if f[0]=='defn-']
s=(a.upstream/'libpicojpeg.c').read_text();zag=[int(x) for x in re.findall(r'\d+',re.search(r'ZAG\[\] = \{(.*?)\};',s,re.S).group(1))]
def tree(xs,start=0):
 if len(xs)==1:return str(xs[0])
 n=len(xs)//2;return '(if (< i '+str(start+n)+') '+tree(xs[:n],start)+' '+tree(xs[n:],start+n)+')'
new='''
(defn- extend [x :i64 s :i64] :i64
 (if (and (> s 0) (<= s 15) (< x (pow (- s 1)))) (i16 (+ (i16 x) 1 (- 0 (pow s)))) (i16 x)))
(defn- huff-code [v :vector-i64 table :i64 i :i64 code :i64] :vector-i64
 (if (= i 16) (put8 v 263 0)
  (let [base (+ 640 (* table 48)) maximum (vector-at v (+ base 16 i))]
   (if (and (<= code maximum) (not= maximum 65535))
    (let [index (bit-and (+ (vector-at v (+ base 32 i)) (- code (vector-at v (+ base i)))) 255)]
     (put8 v 263 (vector-at v (+ (huff-value-base table) index))))
    (let [a (bit v) next (bit-or (bit-and (* code 2) 65535) (vector-at a 263))]
     (huff-code a table (+ i 1) next))))))
(defn- huff-symbol [v :vector-i64 table :i64] :vector-i64
 (let [a (bit v)] (huff-code a table 0 (vector-at a 263))))
(defn- zero-coefficients [v :vector-i64 k :i64 end :i64] :vector-i64
 (if (= k end) v (zero-coefficients (put v (+ 1536 (zag k)) 0) (+ k 1) end)))
(defn- ac-coefficients [v :vector-i64 table :i64 quant :i64 k :i64] :vector-i64
 (if (= k 64) v
  (let [a (huff-symbol v table) symbol (vector-at a 263) size (bit-and symbol 15) run (quot symbol 16)
        b (if (= size 0) a (bits a size 1)) extra (if (= size 0) 0 (vector-at b 263))]
   (if (not= size 0)
    (if (> (+ k run) 63) (fail b 28)
     (let [next (+ k run) c (zero-coefficients b k next) ac (extend extra size)
           d (put c (+ 1536 (zag next)) (i16 (* ac (vector-at c (+ quant next)))))]
      (ac-coefficients d table quant (+ next 1))))
    (if (= run 15)
     (if (> (+ k 16) 64) (fail b 28) (ac-coefficients (zero-coefficients b k (+ k 16)) table quant (+ k 16)))
     (zero-coefficients b k 64))))))
(defn- coefficient-block [v :vector-i64 block :i64] :vector-i64
 (let [component (vector-at v (+ 1490 block)) quant (+ 512 (if (= (vector-at v (+ 1450 component)) 0) 0 64))
       table (if (= (vector-at v (+ 1470 component)) 0) 0 1) a (huff-symbol (put8 v 1610 block) table)
       s (vector-at a 263) width (bit-and s 15) b (if (= width 0) a (bits a width 1))
       r (if (= width 0) 0 (vector-at b 263)) dc (bit-and (+ (extend r s) (vector-at b (+ 1510 component))) 65535)
       c (put (put b (+ 1510 component) (i16 dc)) 1536 (i16 (* dc (vector-at b quant))))
       ac-table (if (= (vector-at c (+ 1480 component)) 0) 2 3)]
  (ac-coefficients c ac-table quant 1)))
(defn- coefficient-blocks [v :vector-i64 count :i64 i :i64] :vector-i64
 (let [blocks (vector-at v 1408) block (rem i blocks) a (coefficient-block v block)]
  (if (or (= (+ i 1) count) (not= (vector-at a 1520) 0)) a
   (let [b (if (= block (- blocks 1)) (put16 a 1413 (- (vector-at a 1413) 1)) a)]
    (coefficient-blocks b count (+ i 1))))))
(defn- coefficient-state [v :vector-i64 count :i64] :vector-i64
 (let [a (stages v 3)]
  (if (or (= count 0) (not= (vector-at a 1520) 0)) a
   (if (= count 169)
    (let [b (coefficient-blocks a 168 0)] (fail (put16 b 1413 (- (vector-at b 1413) 1)) 1))
    (coefficient-blocks a count 0)))))
(defn observe [encoded :i64] :i64
 (let [count (quot encoded 2048) cell (rem encoded 2048)] (vector-at (coefficient-state (vector-alloc 2048) count) cell)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 2048) i))
'''
forms+=read('(defn- zag [i :i64] :i64 '+tree(zag)+')\n'+new)
if len({f[1] for f in forms})!=len(forms):raise SystemExit('duplicate definitions')
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'picojpeg-coefficients.kotoba').write_text('(ns embench.picojpeg-coefficients (:export [observe bounds-probe]))\n;; Original no-restart/non-reduced fixture coefficient path; IDCT/color still open.\n;; Copyright 2014-2019 Embecosm/Bristol; picojpeg Rich Geldreich, public domain.\n'+'\n'.join(map(emit,forms))+'\n')
shutil.copy2(a.headers_bridge,a.directory/'headers-bridge.c')
# Observe actual pre-transform coefficients while still executing original transforms.
begin=s.index('decodeNextMCU (void)\n{');end=s.index('\n//------------------------------------------------------------------------------',begin);body=s[begin:end];body=body[body.index('{')+1:body.rfind('}')]
needle='  transformBlock (mcuBlock);'
if body.count(needle)!=1:raise SystemExit('coefficient observation boundary changed')
body=body.replace(needle,'  capture(mcuBlock);\n'+needle,1)
fields=list(range(1536,1600))+list(range(1510,1513))+list(range(256,263))+[1413,1520,1610]
terminal=list(range(263))+list(range(1510,1513))+[1413,1520]
c='''/* BOOTSTRAP-TOOL: actual pre-transform snapshots; original transforms retained. */
#define observe observe_headers
#include "headers-bridge.c"
#undef observe
static const int coef_fields[]={'''+','.join(map(str,fields))+'''};
static int64_t saved[168][sizeof(coef_fields)/sizeof(coef_fields[0])],buffers[168][256];
static int captures,currentBlock;
static int64_t coef_value(int cell){if(cell>=1536&&cell<1600)return gCoeffBuf[cell-1536];if(cell==1610)return currentBlock;return cellvalue(cell);}
static void capture(int block){currentBlock=block;for(unsigned i=0;i<sizeof(coef_fields)/sizeof(coef_fields[0]);i++)saved[captures][i]=coef_value(coef_fields[i]);for(int i=0;i<256;i++)buffers[captures][i]=gInBuf[i];captures++;}
static uint8 observed_decode(void){
'''+body+'''\n}
static int prepare_coefficients(void){stages(3);captures=0;currentBlock=0;if(lastStatus||gReduce||gRestartInterval||gMaxBlocksPerMCU!=3||gNumMCUSRemaining!=56)return 0;
 pInfo.m_pMCUBufR=gMCUBufR;pInfo.m_pMCUBufG=gMCUBufG;pInfo.m_pMCUBufB=gMCUBufB;
 while(gNumMCUSRemaining){lastStatus=observed_decode();if(lastStatus)return 0;gNumMCUSRemaining--;}lastStatus=pjpeg_decode_mcu();return captures==168&&lastStatus==PJPG_NO_MORE_BLOCKS&&verify_benchmark(0);}
int64_t observe(int64_t encoded,EXTRA){int n=encoded/2048,cell=encoded%2048;if(encoded<0||n>169)return INT64_MIN;if(n==0){stages(3);return coef_value(cell);}if(!prepare_coefficients())return INT64_MIN;
 if(n==169)return coef_value(cell);if(cell>=0&&cell<256)return buffers[n-1][cell];for(unsigned i=0;i<sizeof(coef_fields)/sizeof(coef_fields[0]);i++)if(cell==coef_fields[i])return saved[n-1][i];return INT64_MIN;}
int64_t coefficient_oracle_selfcheck(int64_t n,EXTRA){if(n<1||n>32||!prepare_coefficients())return 0;int64_t state[268];int cells[268];int k=0;for(int i=0;i<263;i++)cells[k++]=i;for(int i=1510;i<1513;i++)cells[k++]=i;cells[k++]=1413;cells[k++]=1520;
 for(int i=0;i<k;i++)state[i]=coef_value(cells[i]);unsigned char r[256],g[256],b[256];memcpy(r,gMCUBufR,256);memcpy(g,gMCUBufG,256);memcpy(b,gMCUBufB,256);
 benchmark_body(1,n);lastStatus=pjpeg_decode_mcu();if(!verify_benchmark(0)||lastStatus!=PJPG_NO_MORE_BLOCKS)return 0;for(int i=0;i<k;i++)if(state[i]!=coef_value(cells[i]))return 0;
 return memcmp(r,gMCUBufR,256)==0&&memcmp(g,gMCUBufG,256)==0&&memcmp(b,gMCUBufB,256)==0;}
'''
(a.directory/'c-bridge.c').write_text(c)
(a.directory/'profile.json').write_text(json.dumps({'status':'coefficients-fragment-only','sourcePins':pins,'headersSha256':hashlib.sha256(a.headers.read_bytes()).hexdigest(),'headersBridgeSha256':hashlib.sha256(a.headers_bridge.read_bytes()).hexdigest(),'blocks':168,'fields':fields,'bufferPrefixes':[1,3,4,84,165,168],'terminalFields':terminal,'workspaceCells':2048},indent=2)+'\n')
