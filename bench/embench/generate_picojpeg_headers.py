#!/usr/bin/env python3
# BOOTSTRAP-TOOL: AST-compose checked reader with original header/table parsing.
import argparse,pathlib,hashlib,json,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('reader',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'libpicojpeg.c':'ed1fb932e9c2c15796bbe6caea8e2e53e61d1349fae4afc1d71847eeebb9185d','picojpeg.h':'50dbd519c3e7b5732cc2e58d9e47195a3e5652f5d14f9d997f102b844e64db36','picojpeg_test.c':'fab1ba5e93f854512ff10910e2b304b20f42a6d579db1793c7aa87e398188f8a'}
for f,d in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed picojpeg headers profile: '+f)
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
forms=[]
for f in read(a.reader.read_text()):
 if f[0]!='defn-' or f[1]=='actions':continue
 if f[1]=='init':f[1]='reader-init'
 forms.append(f)
s=(a.upstream/'libpicojpeg.c').read_text();win=[int(x) for x in re.findall(r'\d+',re.search(r'gWinogradQuant\[\] = \{(.*?)\};',s,re.S).group(1))]
def tree(xs,start=0):
 if len(xs)==1:return str(xs[0])
 n=len(xs)//2;return '(if (< i '+str(start+n)+') '+tree(xs[:n],start)+' '+tree(xs[n:],start+n)+')'
new='''
(defn- fail [v :vector-i64 n :i64] :vector-i64 (put8 v 1520 n))
(defn- i16 [x :i64] :i64 (let [n (bit-and x 65535)] (if (>= n 32768) (- n 65536) n)))
(defn- sar3 [x :i64] :i64 (if (< x 0) (- 0 (quot (+ (- 0 x) 7) 8)) (quot x 8)))
(defn- win-quant [v :vector-i64 base :i64 i :i64] :vector-i64
 (if (= i 64) v (let [x (vector-at v (+ base i)) q (i16 (sar3 (+ (* x (winograd i)) 4)))]
  (win-quant (put v (+ base i) q) base (+ i 1)))))
(defn- quant-values [v :vector-i64 base :i64 precision :i64 i :i64] :vector-i64
 (if (= i 64) v (let [a (bits v 8 0) hi (vector-at a 263) b (if (not= precision 0) (bits a 8 0) a)
       n (if (not= precision 0) (+ (* hi 256) (vector-at b 263)) hi)]
  (quant-values (put b (+ base i) (i16 n)) base precision (+ i 1)))))
(defn- quant-tables [v :vector-i64 left :i64] :vector-i64
 (if (= left 0) (fail v 0)
  (let [a (bits v 8 0) selector (vector-at a 263) n (bit-and selector 15) precision (quot selector 16)]
   (if (> n 1) (fail a 6)
    (let [b (put8 a 1405 (bit-or (vector-at a 1405) (if (= n 0) 1 2))) base (+ 512 (* n 64))
          c (win-quant (quant-values b base precision 0) base 0) amount (if (= precision 0) 65 129)]
     (if (< left amount) (fail c 21) (quant-tables c (bit-and (- left amount) 65535))))))))
(defn- read-quant [v :vector-i64] :vector-i64
 (let [a (bits v 16 0) left (vector-at a 263)] (if (< left 2) (fail a 5) (quant-tables a (- left 2)))))
(defn- huff-value-base [t :i64] :i64 (if (= t 0) 832 (if (= t 1) 848 (if (= t 2) 864 1120))))
(defn- huff-counts [v :vector-i64 i :i64 count :i64] :vector-i64
 (if (= i 16) (put16 v 1524 count)
  (let [a (bits v 8 0) n (vector-at a 263)] (huff-counts (put8 a (+ 1380 i) n) (+ i 1) (bit-and (+ count n) 65535)))))
(defn- huff-values [v :vector-i64 base :i64 count :i64 i :i64] :vector-i64
 (if (= i count) v (let [a (bits v 8 0)] (huff-values (put8 a (+ base i) (vector-at a 263)) base count (+ i 1)))))
(defn- huff-create [v :vector-i64 t :i64 i :i64 j :i64 code :i64] :vector-i64
 (if (= i 16) v
  (let [n (vector-at v (+ 1380 i)) base (+ 640 (* t 48))
        a (put16 (put16 (put8 v (+ base 32 i) (if (= n 0) 0 j)) (+ base i) (if (= n 0) 0 code))
            (+ base 16 i) (if (= n 0) 65535 (+ code n -1)))
        next-j (if (= n 0) j (bit-and (+ j n) 255)) next-code (if (= n 0) code (bit-and (+ code n) 65535))]
   (huff-create a t (+ i 1) next-j (bit-and (* next-code 2) 65535)))))
(defn- huff-tables [v :vector-i64 left :i64] :vector-i64
 (if (= left 0) (fail v 0)
  (let [a (bits v 8 0) index (vector-at a 263)]
   (if (or (> (bit-and index 15) 1) (> (bit-and index 240) 16)) (fail a 3)
    (let [t (+ (bit-and (quot index 8) 2) (bit-and index 1))
          b (put8 a 1404 (bit-or (vector-at a 1404) (pow t))) c (huff-counts b 0 0) count (vector-at c 1524)]
     (if (> count (if (< t 2) 12 255)) (fail c 2)
      (let [d (huff-values c (huff-value-base t) count 0) amount (+ 17 count)]
       (if (< left amount) (fail d 4) (huff-tables (huff-create d t 0 0 0) (- left amount))))))))))
(defn- read-huff [v :vector-i64] :vector-i64
 (let [a (bits v 16 0) left (vector-at a 263)] (if (< left 2) (fail a 4) (huff-tables a (- left 2)))))
(defn- skip-bytes [v :vector-i64 n :i64] :vector-i64
 (if (= n 0) v (skip-bytes (bits v 8 0) (- n 1))))
(defn- skip-marker [v :vector-i64] :vector-i64
 (let [a (bits v 16 0) n (vector-at a 263)] (if (< n 2) (fail a 12) (fail (skip-bytes a (- n 2)) 0))))
(defn- read-dri [v :vector-i64] :vector-i64
 (let [a (bits v 16 0)] (if (not= (vector-at a 263) 4) (fail a 13)
  (let [b (bits a 16 0)] (fail (put16 b 1403 (vector-at b 263)) 0)))))
(defn- seek-ff [v :vector-i64] :vector-i64
 (let [a (bits v 8 0)] (if (= (vector-at a 263) 255) a (seek-ff a))))
(defn- skip-ff [v :vector-i64] :vector-i64
 (let [a (bits v 8 0)] (if (= (vector-at a 263) 255) (skip-ff a) a)))
(defn- next-marker [v :vector-i64] :vector-i64
 (let [a (skip-ff (seek-ff v)) n (vector-at a 263)] (if (= n 0) (next-marker a) (put8 a 1521 n))))
(defn- stop-marker? [n :i64] :bool
 (or (= n 192) (= n 193) (= n 194) (= n 195) (= n 197) (= n 198) (= n 199)
     (= n 201) (= n 202) (= n 203) (= n 205) (= n 206) (= n 207) (= n 216) (= n 217) (= n 218)))
(defn- markers [v :vector-i64] :vector-i64
 (let [a (next-marker v) n (vector-at a 1521)]
  (if (stop-marker? n) (fail a 0)
   (if (= n 204) (fail a 17)
    (if (or (= n 200) (and (>= n 208) (<= n 215)) (= n 1)) (fail a 18)
     (let [b (if (= n 196) (read-huff a) (if (= n 219) (read-quant a) (if (= n 221) (read-dri a) (skip-marker a))))]
      (markers (fail b 0))))))))
(defn- soi-search [v :vector-i64 last :i64 left :i64] :vector-i64
 (if (= left 1) (fail v 19)
  (let [a (bits v 8 0) n (vector-at a 263)]
   (if (= last 255)
    (if (= n 216) (if (= (quot (vector-at a 259) 256) 255) (fail a 0) (fail a 19))
     (if (= n 217) (fail a 19) (soi-search a n (- left 1))))
    (soi-search a n (- left 1))))))
(defn- locate-soi [v :vector-i64] :vector-i64
 (let [a (bits v 8 0) last (vector-at a 263) b (bits a 8 0) n (vector-at b 263)]
  (if (and (= last 255) (= n 216)) (fail b 0) (soi-search b n 4096))))
(defn- frame-components [v :vector-i64 i :i64] :vector-i64
 (if (= i (vector-at v 1402)) (fail v 0)
  (let [a (bits v 8 0) b (bits (put8 a (+ 1420 i) (vector-at a 263)) 4 0)
        c (bits (put8 b (+ 1430 i) (vector-at b 263)) 4 0)
        d (bits (put8 c (+ 1440 i) (vector-at c 263)) 8 0) q (vector-at d 263) e (put8 d (+ 1450 i) q)]
   (if (> q 1) (fail e 36) (frame-components e (+ i 1))))))
(defn- read-sof [v :vector-i64] :vector-i64
 (let [a (bits v 16 0) left (vector-at a 263) b (bits a 8 0)]
  (if (not= (vector-at b 263) 8) (fail b 7)
   (let [c (bits b 16 0) y (vector-at c 263) d (put16 c 1401 y)]
    (if (or (= y 0) (> y 16384)) (fail d 8)
     (let [e (bits d 16 0) x (vector-at e 263) f (put16 e 1400 x)]
      (if (or (= x 0) (> x 16384)) (fail f 9)
       (let [g (bits f 8 0) comps (vector-at g 263) h (put8 g 1402 comps)]
        (if (> comps 3) (fail h 10) (if (not= left (+ (* comps 3) 8)) (fail h 11) (frame-components h 0)))))))))))
(defn- locate-sof [v :vector-i64] :vector-i64
 (let [a (locate-soi v)] (if (not= (vector-at a 1520) 0) a
  (let [b (markers a) n (vector-at b 1521)] (if (not= (vector-at b 1520) 0) b
   (if (= n 192) (read-sof b) (fail b (if (= n 194) 37 (if (= n 201) 17 20)))))))))
(defn- org [v :vector-i64 yblocks :i64 i :i64] :vector-i64
 (if (= i yblocks) (put8 (put8 v (+ 1490 i) 1) (+ 1491 i) 2)
  (org (put8 v (+ 1490 i) 0) yblocks (+ i 1))))
(defn- geometry [v :vector-i64 scan :i64 blocks :i64 x :i64 y :i64] :vector-i64
 (let [a (put8 (put8 (put8 (put8 v 1407 scan) 1408 blocks) 1409 x) 1410 y)
       rows (quot (+ (vector-at a 1400) x -1) x) cols (quot (+ (vector-at a 1401) y -1) y)]
  (fail (put16 (put16 (put16 a 1411 rows) 1412 cols) 1413 (* rows cols)) 0)))
(defn- init-frame [v :vector-i64] :vector-i64
 (let [comps (vector-at v 1402) h (vector-at v 1430) s (vector-at v 1440)]
  (if (= comps 1) (if (and (= h 1) (= s 1)) (geometry (put8 v 1490 0) 0 1 8 8) (fail v 27))
   (if (not= comps 3) (fail v 26)
    (if (or (not= (vector-at v 1431) 1) (not= (vector-at v 1441) 1) (not= (vector-at v 1432) 1) (not= (vector-at v 1442) 1)) (fail v 27)
     (if (and (= h 1) (= s 1)) (geometry (org v 1 0) 1 3 8 8)
      (if (and (= h 1) (= s 2)) (geometry (org v 2 0) 3 4 8 16)
       (if (and (= h 2) (= s 1)) (geometry (org v 2 0) 2 4 16 8)
        (if (and (= h 2) (= s 2)) (geometry (org v 4 0) 4 6 16 16) (fail v 27))))))))))
(defn- find-component [v :vector-i64 cc :i64 i :i64] :i64
 (if (= i (vector-at v 1402)) i (if (= cc (vector-at v (+ 1420 i))) i (find-component v cc (+ i 1)))))
(defn- scan-components [v :vector-i64 i :i64] :vector-i64
 (if (= i (vector-at v 1406)) v
  (let [a (bits v 8 0) cc (vector-at a 263) b (bits a 8 0) n (vector-at b 263) ci (find-component b cc 0)]
   (if (>= ci (vector-at b 1402)) (fail b 15)
    (let [c (put8 (put8 (put8 b (+ 1460 i) ci) (+ 1470 ci) (bit-and (quot n 16) 15)) (+ 1480 ci) (bit-and n 15))]
     (scan-components c (+ i 1)))))))
(defn- read-sos [v :vector-i64] :vector-i64
 (let [a (bits v 16 0) left (bit-and (- (vector-at a 263) 3) 65535) b (bits a 8 0) n (vector-at b 263) c (put8 b 1406 n)]
  (if (or (not= left (+ (* n 2) 3)) (< n 1) (> n 3)) (fail c 14)
   (let [d (scan-components c 0)] (if (not= (vector-at d 1520) 0) d
    (let [e (bits d 8 0) f (bits (put8 e 1500 (vector-at e 263)) 8 0)
          g (bits (put8 f 1501 (vector-at f 263)) 4 0) h (bits (put8 g 1502 (vector-at g 263)) 4 0)]
     (fail (put8 h 1503 (vector-at h 263)) 0)))))))
(defn- pow18 [i :i64] :i64 (if (= i 17) 131072 (pow i)))
(defn- check-huff [v :vector-i64 i :i64] :vector-i64
 (if (= i (vector-at v 1406)) (fail v 0)
  (let [c (vector-at v (+ 1460 i)) dc (vector-at v (+ 1470 c)) ac (+ (vector-at v (+ 1480 c)) 2) valid (vector-at v 1404)]
   (if (or (= (bit-and valid (pow18 dc)) 0) (= (bit-and valid (pow18 ac)) 0)) (fail v 24) (check-huff v (+ i 1))))))
(defn- check-quant [v :vector-i64 i :i64] :vector-i64
 (if (= i (vector-at v 1406)) (fail v 0)
  (let [c (vector-at v (+ 1460 i)) mask (if (= (vector-at v (+ 1450 c)) 0) 1 2)]
   (if (= (bit-and (vector-at v 1405) mask) 0) (fail v 23) (check-quant v (+ i 1))))))
(defn- init-scan [v :vector-i64] :vector-i64
 (let [a (markers v)] (if (not= (vector-at a 1520) 0) a
  (if (not= (vector-at a 1521) 218) (fail a 18)
   (let [b (read-sos a) c (if (= (vector-at b 1520) 0) (check-huff b 0) b)
         d (if (= (vector-at c 1520) 0) (check-quant c 0) c)]
    (if (not= (vector-at d 1520) 0) d
     (let [e (put (put (put d 1510 0) 1511 0) 1512 0) interval (vector-at e 1403)
           f (if (not= interval 0) (put16 (put16 e 1415 interval) 1414 0) e)]
      (fail (fix f) 0))))))))
(defn- stages [v :vector-i64 stage :i64] :vector-i64
 (let [a (reader-init v)] (if (= stage 0) a
  (let [b (locate-sof a)] (if (or (= stage 1) (not= (vector-at b 1520) 0)) b
   (let [c (init-frame b)] (if (or (= stage 2) (not= (vector-at c 1520) 0)) c (init-scan c))))))))
(defn observe [encoded :i64] :i64
 (let [stage (quot encoded 2048) cell (rem encoded 2048)] (vector-at (stages (vector-alloc 2048) stage) cell)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 2048) i))
'''
forms+=read('(defn- winograd [i :i64] :i64 '+tree(win)+')\n'+new)
if len({f[1] for f in forms})!=len(forms):raise SystemExit('duplicate definitions')
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'picojpeg-headers.kotoba').write_text('(ns embench.picojpeg-headers (:export [observe bounds-probe]))\n;; Header/table fragment only; MCU coefficient/IDCT/color decoding remains open.\n;; Copyright 2014-2019 Embecosm/Bristol; picojpeg Rich Geldreich, public domain.\n'+'\n'.join(map(emit,forms))+'\n')
fields=list(range(263))+list(range(512,640))+list(range(640,1376))+list(range(1400,1416))+sum([list(range(base,base+3)) for base in (1420,1430,1440,1450,1460,1470,1480)],[])+list(range(1490,1496))+list(range(1500,1504))+list(range(1510,1513))+[1520]
(a.directory/'profile.json').write_text(json.dumps({'status':'headers-fragment-only','sourcePins':pins,'readerSha256':hashlib.sha256(a.reader.read_bytes()).hexdigest(),'stages':4,'fields':fields,'workspaceCells':2048},indent=2)+'\n')
arrays={512:('gQuant0',64),576:('gQuant1',64),832:('gHuffVal0',16),848:('gHuffVal1',16),864:('gHuffVal2',256),1120:('gHuffVal3',256),1420:('gCompIdent',3),1430:('gCompHSamp',3),1440:('gCompVSamp',3),1450:('gCompQuant',3),1460:('gCompList',3),1470:('gCompDCTab',3),1480:('gCompACTab',3),1490:('gMCUOrg',6),1510:('gLastDC',3)}
scalars={256:'gInBufOfs',257:'gInBufLeft',258:'gTemFlag',259:'gBitBuf',260:'gBitsLeft',261:'jpeg_off',262:'gCallbackStatus',1400:'gImageXSize',1401:'gImageYSize',1402:'gCompsInFrame',1403:'gRestartInterval',1404:'gValidHuffTables',1405:'gValidQuantTables',1406:'gCompsInScan',1407:'gScanType',1408:'gMaxBlocksPerMCU',1409:'gMaxMCUXSize',1410:'gMaxMCUYSize',1411:'gMaxMCUSPerRow',1412:'gMaxMCUSPerCol',1413:'gNumMCUSRemaining',1414:'gNextRestartNum',1415:'gRestartsLeft',1500:'spectral_start',1501:'spectral_end',1502:'successive_high',1503:'successive_low',1520:'lastStatus'}
c='''/* BOOTSTRAP-TOOL: unchanged original header functions and full-init comparison. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/src/picojpeg/libpicojpeg.c"
#include "../upstream/src/picojpeg/picojpeg_test.c"
static unsigned char lastStatus;
static void reset(void){memset(gInBuf,0,sizeof(gInBuf));jpeg_off=0;g_pNeedBytesCallback=pjpeg_need_bytes_callback;g_pCallback_data=0;gCallbackStatus=0;
'''
for name,count in arrays.values():c+='memset('+name+',0,sizeof('+name+'));\n'
for t in range(4):c+='memset(&gHuffTab'+str(t)+',0,sizeof(gHuffTab'+str(t)+'));\n'
for name in scalars.values():c+=name+'=0;\n'
c+='}\nstatic void stages(int stage){reset();lastStatus=init();if(stage==0||lastStatus)return;lastStatus=locateSOFMarker();if(stage==1||lastStatus)return;lastStatus=initFrame();if(stage==2||lastStatus)return;lastStatus=initScan();}\nstatic int64_t cellvalue(int cell){if(cell>=0&&cell<256)return gInBuf[cell];\n'
for base,(name,count) in arrays.items():c+='if(cell>='+str(base)+'&&cell<'+str(base+count)+')return '+name+'[cell-'+str(base)+'];\n'
c+='if(cell>=640&&cell<832){int t=(cell-640)/48,k=(cell-640)%48;HuffTable *h=getHuffTable(t);if(k<16)return h->mMinCode[k];if(k<32)return h->mMaxCode[k-16];return h->mValPtr[k-32];}\nswitch(cell){\n'
for i,name in scalars.items():c+='case '+str(i)+':return '+name+';\n'
c+='default:return INT64_MIN;}}\nstatic const int fields[]={'+','.join(map(str,fields))+'};\n'
c+='''#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe(int64_t encoded,EXTRA){int stage=encoded/2048,cell=encoded%2048;if(encoded<0||stage>3)return INT64_MIN;stages(stage);return cellvalue(cell);}
int64_t oracle_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;stages(3);if(lastStatus)return 0;int64_t saved[sizeof(fields)/sizeof(fields[0])];for(unsigned i=0;i<sizeof(fields)/sizeof(fields[0]);i++)saved[i]=cellvalue(fields[i]);
 for(int j=0;j<n;j++){jpeg_off=0;lastStatus=pjpeg_decode_init(&pInfo,pjpeg_need_bytes_callback,0,0);if(lastStatus)return 0;for(unsigned i=0;i<sizeof(fields)/sizeof(fields[0]);i++)if(saved[i]!=cellvalue(fields[i]))return 0;
 if(pInfo.m_width!=gImageXSize||pInfo.m_height!=gImageYSize||pInfo.m_comps!=gCompsInFrame||pInfo.m_MCUSPerRow!=gMaxMCUSPerRow||pInfo.m_MCUSPerCol!=gMaxMCUSPerCol)return 0;}return 1;}
int64_t decoder_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;benchmark_body(1,n);return verify_benchmark(0);}
'''
(a.directory/'c-bridge.c').write_text(c)
