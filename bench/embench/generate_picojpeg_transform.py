#!/usr/bin/env python3
# BOOTSTRAP-TOOL: AST-compose coefficients with original IDCT/YH1V1 transforms.
import argparse,pathlib,hashlib,json,shutil
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('coefficients',type=pathlib.Path);p.add_argument('headers_bridge',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'libpicojpeg.c':'ed1fb932e9c2c15796bbe6caea8e2e53e61d1349fae4afc1d71847eeebb9185d','picojpeg.h':'50dbd519c3e7b5732cc2e58d9e47195a3e5652f5d14f9d997f102b844e64db36','picojpeg_test.c':'fab1ba5e93f854512ff10910e2b304b20f42a6d579db1793c7aa87e398188f8a'}
for f,d in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed picojpeg transform profile: '+f)
import re
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
forms=[f for f in read(a.coefficients.read_text()) if f[0]=='defn-']
new=r"""
(defn- floor-quot [x :i64 divisor :i64] :i64
 (if (< x 0) (- 0 (quot (+ (- 0 x) (- divisor 1)) divisor)) (quot x divisor)))
(defn- multiply-idct [x :i64 factor :i64] :i64 (i16 (floor-quot (+ (* (i16 x) factor) 128) 256)))
(defn- pixel-clamp [x :i64] :i64 (let [s (i16 x)] (if (< s 0) 0 (if (> s 255) 255 s))))
(defn- descale [x :i64] :i64 (pixel-clamp (+ (floor-quot (+ x 64) 128) 128)))
(defn- set-lane [v :vector-i64 base :i64 stride :i64 k :i64 x :i64] :vector-i64
 (put v (+ base (* stride k)) (i16 x)))
(defn- fill-lane [v :vector-i64 base :i64 stride :i64 k :i64 x :i64] :vector-i64
 (if (= k 8) v (fill-lane (set-lane v base stride k x) base stride (+ k 1) x)))
(defn- lane-dc [v :vector-i64 base :i64 stride :i64 k :i64] :bool
 (if (= k 8) true (and (= (vector-at v (+ base (* stride k))) 0) (lane-dc v base stride (+ k 1)))))
(defn- idct-lane [v :vector-i64 base :i64 stride :i64 columns :bool] :vector-i64
 (if (lane-dc v base stride 1)
  (let [dc (vector-at v base)] (fill-lane v base stride 0 (if columns (descale dc) dc)))
  (let [src4 (vector-at v (+ base (* stride 5))) src7 (vector-at v (+ base (* stride 3)))
        x4 (i16 (- src4 src7)) x7 (i16 (+ src4 src7))
        src5 (vector-at v (+ base stride)) src6 (vector-at v (+ base (* stride 7)))
        x5 (i16 (+ src5 src6)) x6 (i16 (- src5 src6))
        tmp1 (multiply-idct (- x4 x6) 196) stg26 (i16 (- (multiply-idct x6 277) tmp1))
        x24 (i16 (- tmp1 (multiply-idct x4 669))) x15 (i16 (- x5 x7)) x17 (i16 (+ x5 x7))
        tmp2 (i16 (- stg26 x17)) tmp3 (i16 (- (multiply-idct x15 362) tmp2)) x44 (i16 (+ tmp3 x24))
        src0 (vector-at v base) src1 (vector-at v (+ base (* stride 4)))
        x30 (i16 (+ src0 src1)) x31 (i16 (- src0 src1))
        src2 (vector-at v (+ base (* stride 2))) src3 (vector-at v (+ base (* stride 6)))
        x12 (i16 (- src2 src3)) x13 (i16 (+ src2 src3)) x32 (i16 (- (multiply-idct x12 362) x13))
        x40 (i16 (+ x30 x13)) x43 (i16 (- x30 x13)) x41 (i16 (+ x31 x32)) x42 (i16 (- x31 x32))
        a (set-lane v base stride 0 (if columns (descale (+ x40 x17)) (+ x40 x17)))
        b (set-lane a base stride 1 (if columns (descale (+ x41 tmp2)) (+ x41 tmp2)))
        c (set-lane b base stride 2 (if columns (descale (+ x42 tmp3)) (+ x42 tmp3)))
        d (set-lane c base stride 3 (if columns (descale (- x43 x44)) (- x43 x44)))
        e (set-lane d base stride 4 (if columns (descale (+ x43 x44)) (+ x43 x44)))
        f (set-lane e base stride 5 (if columns (descale (- x42 tmp3)) (- x42 tmp3)))
        g (set-lane f base stride 6 (if columns (descale (- x41 tmp2)) (- x41 tmp2)))]
   (set-lane g base stride 7 (if columns (descale (- x40 x17)) (- x40 x17))))))
(defn- idct-pass [v :vector-i64 columns :bool i :i64] :vector-i64
 (if (= i 8) v
  (idct-pass (idct-lane v (+ 1536 (if columns i (* i 8))) (if columns 8 1) columns) columns (+ i 1))))
(defn- color [v :vector-i64 block :i64 i :i64] :vector-i64
 (if (= i 64) v
  (let [c (bit-and (vector-at v (+ 1536 i)) 255)
        a (if (= block 0)
            (put8 (put8 (put8 v (+ 2048 i) c) (+ 2304 i) c) (+ 2560 i) c)
            (if (= block 1)
             (let [cg (i16 (- (quot (* c 88) 256) 44)) cb (i16 (- (+ c (quot (* c 198) 256)) 227))]
              (put8 (put8 v (+ 2304 i) (pixel-clamp (- (vector-at v (+ 2304 i)) cg))) (+ 2560 i) (pixel-clamp (+ (vector-at v (+ 2560 i)) cb))))
             (let [cr (i16 (- (+ c (quot (* c 103) 256)) 179)) cg (i16 (- (quot (* c 183) 256) 91))]
              (put8 (put8 v (+ 2048 i) (pixel-clamp (+ (vector-at v (+ 2048 i)) cr))) (+ 2304 i) (pixel-clamp (- (vector-at v (+ 2304 i)) cg))))))]
   (color a block (+ i 1)))))
(defn- transformed-blocks [v :vector-i64 count :i64 phase :i64 i :i64] :vector-i64
 (let [block (rem i 3) a (coefficient-block v block) rows (idct-pass a false 0)]
  (if (and (= (+ i 1) count) (= phase 1)) rows
   (let [cols (idct-pass rows true 0)]
    (if (and (= (+ i 1) count) (= phase 2)) cols
     (let [rgb (color cols block 0)]
      (if (= (+ i 1) count) rgb
       (let [next (if (= block 2) (put16 rgb 1413 (- (vector-at rgb 1413) 1)) rgb)]
        (transformed-blocks next count phase (+ i 1))))))))))
(defn- transform-state [v :vector-i64 count :i64 phase :i64] :vector-i64
 (let [a (stages v 3)]
  (if (= count 169) (let [b (transformed-blocks a 168 3 0)] (fail (put16 b 1413 0) 1))
   (if (= count 0) a (transformed-blocks a count phase 0)))))
(defn observe [encoded :i64] :i64
 (let [phase (quot encoded 1048576) rest (rem encoded 1048576) count (quot rest 4096) cell (rem rest 4096)]
  (vector-at (transform-state (vector-alloc 4096) count phase) cell)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 4096) i))
"""
forms+=read(new)
if len({f[1] for f in forms})!=len(forms):raise SystemExit('duplicate definition')
a.directory.mkdir(parents=True,exist_ok=True)
(a.directory/'picojpeg-transform.kotoba').write_text('(ns embench.picojpeg-transform (:export [observe bounds-probe]))\n;; Original YH1V1 non-reduced fixture, all IDCT rows/columns and RGB.\n;; Copyright 2014-2019 Embecosm/Bristol; picojpeg Rich Geldreich, public domain.\n'+'\n'.join(map(emit,forms))+'\n')
shutil.copy2(a.headers_bridge,a.directory/'headers-bridge.c')
s=(a.upstream/'libpicojpeg.c').read_text()
def body(name):
 begin=s.index(name+' (');start=s.index('{',begin);depth=1;i=start+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[start+1:i-1]
transform=body('transformBlock');needle='  idctRows ();\n  idctCols ();';
if transform.count(needle)!=1:raise SystemExit('unreviewed transform observation boundary')
transform=transform.replace(needle,'  idctRows (); save_coeff(rows);\n  idctCols (); save_coeff(cols);',1)
decode=body('decodeNextMCU');needle='  transformBlock (mcuBlock);'
if decode.count(needle)!=1:raise SystemExit('unreviewed decode observation boundary')
decode=decode.replace(needle,'  observed_transform(mcuBlock); save_rgb(); currentBlock=mcuBlock; captures++;',1)
terminal=list(range(263))+list(range(1510,1513))+[1413,1520]+list(range(1536,1600))+list(range(2048,2816))
c='''/* BOOTSTRAP-TOOL: original IDCT/color boundaries; full original transforms retained. */
#define observe observe_headers
#include "headers-bridge.c"
#undef observe
static int64_t rows[168][64],cols[168][64],rgb[168][768];
static int captures,currentBlock;
static void save_coeff(int64_t dst[168][64]){for(int i=0;i<64;i++)dst[captures][i]=gCoeffBuf[i];}
static void save_rgb(void){for(int i=0;i<256;i++){rgb[captures][i]=gMCUBufR[i];rgb[captures][256+i]=gMCUBufG[i];rgb[captures][512+i]=gMCUBufB[i];}}
static void observed_transform(uint8 mcuBlock){
'''+transform+'''\n}
static uint8 observed_decode(void){
'''+decode+'''\n}
static int64_t pixel_value(int cell){if(cell>=1536&&cell<1600)return gCoeffBuf[cell-1536];if(cell>=2048&&cell<2304)return gMCUBufR[cell-2048];if(cell>=2304&&cell<2560)return gMCUBufG[cell-2304];if(cell>=2560&&cell<2816)return gMCUBufB[cell-2560];if(cell==1610)return currentBlock;return cellvalue(cell);}
static int prepare(void){memset(gCoeffBuf,0,sizeof(gCoeffBuf));memset(gMCUBufR,0,sizeof(gMCUBufR));memset(gMCUBufG,0,sizeof(gMCUBufG));memset(gMCUBufB,0,sizeof(gMCUBufB));stages(3);captures=0;currentBlock=0;
 if(lastStatus||gReduce||gRestartInterval||gMaxBlocksPerMCU!=3||gNumMCUSRemaining!=56)return 0;
 pInfo.m_pMCUBufR=gMCUBufR;pInfo.m_pMCUBufG=gMCUBufG;pInfo.m_pMCUBufB=gMCUBufB;
 while(gNumMCUSRemaining){lastStatus=observed_decode();if(lastStatus)return 0;gNumMCUSRemaining--;}
 lastStatus=pjpeg_decode_mcu();return captures==168&&lastStatus==PJPG_NO_MORE_BLOCKS&&verify_benchmark(0);}
int64_t observe(int64_t encoded,EXTRA){int phase=encoded/1048576,rest=encoded%1048576,n=rest/4096,cell=rest%4096;
 if(encoded<0||n>169||phase<1||phase>3||!prepare())return INT64_MIN;
 if(n==169)return pixel_value(cell);if(n==0)return INT64_MIN;
 if((phase==1||phase==2)&&cell>=1536&&cell<1600)return phase==1?rows[n-1][cell-1536]:cols[n-1][cell-1536];
 if(phase==3&&cell>=2048&&cell<2816)return rgb[n-1][cell-2048];return INT64_MIN;}
static const int terminal_fields[]={'''+','.join(map(str,terminal))+'''};
int64_t transform_selfcheck(int64_t n,EXTRA){if(n<1||n>32||!prepare())return 0;int64_t saved[sizeof(terminal_fields)/sizeof(terminal_fields[0])];
 for(unsigned i=0;i<sizeof(terminal_fields)/sizeof(terminal_fields[0]);i++)saved[i]=pixel_value(terminal_fields[i]);
 benchmark_body(1,n);lastStatus=pjpeg_decode_mcu();if(lastStatus!=PJPG_NO_MORE_BLOCKS||!verify_benchmark(0))return 0;
 for(unsigned i=0;i<sizeof(terminal_fields)/sizeof(terminal_fields[0]);i++)if(saved[i]!=pixel_value(terminal_fields[i]))return 0;return 1;}
'''
(a.directory/'c-bridge.c').write_text(c)
(a.directory/'profile.json').write_text(json.dumps({'status':'transform-fragment-only','sourcePins':pins,'coefficientsSha256':hashlib.sha256(a.coefficients.read_bytes()).hexdigest(),'headersBridgeSha256':hashlib.sha256(a.headers_bridge.read_bytes()).hexdigest(),'blocks':168,'mcus':56,'coefficientFields':list(range(1536,1600)),'rgbFields':list(range(2048,2112))+list(range(2304,2368))+list(range(2560,2624)),'terminalFields':terminal,'workspaceCells':4096},indent=2)+'\n')
