#!/usr/bin/env python3
# BOOTSTRAP-TOOL: compose accepted QR placement forms with full mask/score/body.
import argparse,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('placement',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
# The mask, score, format and whole-body sources must all be reviewed inputs.
pins={f:hashlib.sha256((a.upstream/f).read_bytes()).hexdigest() for f in ('qrencode.c','qrframe.c','ecctable.h','qrbits.h','qrtest.c')}
expected={'qrbits.h':'af772ed9bd01daab613ed2161c47fd065a92ff4932765ab65bfd9877b48af609','qrtest.c':'7556be13dbcb0f98caaf3722d86b93e49cf3c9ea2f9aaf609f2541aca9867a96','qrencode.c':'05d2147e1809578fcdce4ebd6105a555e59dc8c9b5c5b2f4d7a239ea8d9bf5b8','qrframe.c':'3d3400ff94ba165d0cf2945a364527f55291fa144511e0a94f317fdc58992f15','ecctable.h':'54e176fa47d4c20baab098962a0c0f1a8629362499dbc8fbab5d581312b1002c'}
for f,d in expected.items():
 if pins[f]!=d:raise SystemExit('unreviewed QR full profile: '+f)
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
  if t in (')',']'):raise ValueError('unbalanced fragment')
  return t
 out=[]
 while pos<len(ts):out.append(form())
 return out
def emit(x):
 if isinstance(x,list):return ('[' if isinstance(x,Vec) else '(')+' '.join(map(emit,x))+(']' if isinstance(x,Vec) else ')')
 return x
forms=[f for f in read(a.placement.read_text()) if f[0]=='defn-']
new='''
(defn- put-wide [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))
(defn- qr-bit [v :vector-i64 x :i64 y :i64] :i64
 (if (not= (bit-and (vector-at v (+ 768 (quot x 8) (* y 4))) (weight (rem x 8))) 0) 1 0))
(defn- mask? [m :i64 x :i64 y :i64] :bool
 (let [rx (rem x 3) ry (rem y 3) p (bit-and (bit-and x y) 1) same (if (and (not= rx 0) (= rx ry)) 1 0)]
  (if (= m 0) (= (rem (+ x y) 2) 0)
   (if (= m 1) (= (rem y 2) 0)
    (if (= m 2) (= rx 0)
     (if (= m 3) (= (rem (+ x y) 3) 0)
      (if (= m 4) (= (rem (+ (quot x 3) (quot y 2)) 2) 0)
       (if (= m 5) (= (+ p (if (and (not= rx 0) (not= ry 0)) 1 0)) 0)
        (if (= m 6) (= (rem (+ p same) 2) 0) (= (rem (+ same (rem (+ x y) 2)) 2) 0))))))))))
(defn- mask-row [v :vector-i64 m :i64 x :i64 y :i64] :vector-i64
 (if (= x 25) v
  (let [a (if (and (mask? m x y) (not (reserved? v x y)))
           (let [i (+ 768 (quot x 8) (* y 4))] (put v i (bit-xor (vector-at v i) (weight (rem x 8))))) v)]
   (mask-row a m (+ x 1) y))))
(defn- mask-image [v :vector-i64 m :i64 y :i64] :vector-i64
 (if (= y 25) v (mask-image (mask-row v m 0 y) m (+ y 1))))
(defn- blocks-row [v :vector-i64 x :i64 y :i64 score :i64] :i64
 (if (= x 24) score
  (let [b (qr-bit v x y) same (and (= b (qr-bit v (+ x 1) y)) (= b (qr-bit v x (+ y 1))) (= b (qr-bit v (+ x 1) (+ y 1))))]
   (blocks-row v (+ x 1) y (+ score (if same 3 0))))))
(defn- blocks [v :vector-i64 y :i64 score :i64] :i64
 (if (= y 24) score (blocks v (+ y 1) (blocks-row v 0 y score))))
(defn- runs [v :vector-i64 axis :i64 row :i64 i :i64 h :i64 b :i64 bw :i64] :vector-i64
 (if (= i 25) (put-wide (put-wide v 1754 h) 1755 bw)
  (let [next (if (= axis 0) (qr-bit v i row) (qr-bit v row i)) nh (if (= b next) h (+ h 1))
        len (if (= b next) (+ (vector-at v (+ 1728 h)) 1) 1)
        a (put v (+ 1728 nh) len)]
   (runs a axis row (+ i 1) nh next (+ bw (if (= axis 0) (if (= next 1) 1 -1) 0))))))
(defn- long-runs [v :vector-i64 len :i64 i :i64 score :i64] :i64
 (if (> i len) score (let [n (vector-at v (+ 1728 i))] (long-runs v len (+ i 1) (+ score (if (>= n 5) (+ 3 n -5) 0))))))
(defn- pattern-runs [v :vector-i64 len :i64 i :i64 score :i64] :i64
 (if (>= i (- len 1)) score
  (let [n (vector-at v (+ 1728 i)) a (vector-at v (+ 1728 i -1))
        same (and (= (vector-at v (+ 1728 i -2)) (vector-at v (+ 1728 i 2)))
          (= (vector-at v (+ 1728 i 2)) a) (= a (vector-at v (+ 1728 i 1))) (= (* a 3) n))
        white (or (= (vector-at v (+ 1728 i -3)) 0) (> (+ i 3) len)
          (>= (* (vector-at v (+ 1728 i -3)) 3) (* n 4))
          (>= (* (vector-at v (+ 1728 i 3)) 3) (* n 4)))]
   (pattern-runs v len (+ i 2) (+ score (if (and same white) 40 0))))))
(defn- run-score [v :vector-i64 len :i64] :i64 (pattern-runs v len 3 (long-runs v len 0 0)))
(defn- all-runs [v :vector-i64 axis :i64 row :i64 score :i64 bw :i64] :vector-i64
 (if (= row 25) (put-wide (put-wide v 1756 score) 1757 bw)
  (let [a (runs (put v 1728 0) axis row 0 0 0 bw) h (vector-at a 1754) next-bw (vector-at a 1755) s (run-score a h)]
   (all-runs a axis (+ row 1) (+ score s) next-bw))))
(defn- imbalance [big :i64 count :i64] :i64
 (if (> big 625) (imbalance (- big 625) (+ count 1)) (* count 10)))
(defn- badcheck [v :vector-i64] :vector-i64
 (let [score (blocks v 0 0) a (all-runs v 0 0 score 0) bw (vector-at a 1757)
       b (if (< bw 0) (- 0 bw) bw) next (+ (vector-at a 1756) (imbalance (* b 10) 0))]
  (all-runs a 1 0 next 0)))
(defn- copy-image [v :vector-i64 to :i64 from :i64 i :i64] :vector-i64
 (if (= i 100) v (copy-image (put v (+ to i) (vector-at v (+ from i))) to from (+ i 1))))
(defn- mask-scores [v :vector-i64 i :i64 best :i64 minimum :i64] :vector-i64
 (if (= i 8) (put-wide (put-wide (put-wide v 1790 best) 1791 minimum) 1792 i)
  (let [a (badcheck (mask-image v i 0)) s (vector-at a 1756) b (put-wide a (+ 1780 i) s)
        win (< s minimum) nb (if win i best) nm (if win s minimum)]
   (if (= nb 7) (put-wide (put-wide (put-wide b 1790 nb) 1791 nm) 1792 i)
    (mask-scores (copy-image b 768 0 0) (+ i 1) nb nm)))))
(defn- fmt-word [m :i64] :i64
 (if (< m 4) (if (< m 2) (if (= m 0) 30660 29427) (if (= m 2) 32170 30877))
  (if (< m 6) (if (= m 4) 26159 25368) (if (= m 6) 27713 26998))))
(defn- fmt-low [v :vector-i64 i :i64 bits :i64] :vector-i64
 (if (= i 8) v
  (let [a (if (= (rem bits 2) 1) (data-bit (data-bit v (- 24 i) 8) 8 (if (< i 6) i (+ i 1))) v)]
   (fmt-low a (+ i 1) (quot bits 2)))))
(defn- fmt-high [v :vector-i64 i :i64 bits :i64] :vector-i64
 (if (= i 7) v
  (let [a (if (= (rem bits 2) 1) (data-bit (data-bit v 8 (+ 18 i)) (if (= i 0) 7 (- 6 i)) 8) v)]
   (fmt-high a (+ i 1) (quot bits 2)))))
(defn- final-format [v :vector-i64] :vector-i64
 (let [m (vector-at v 1790) i (vector-at v 1792) a (if (not= m i) (mask-image v m 0) v) bits (fmt-word m)]
  (fmt-high (fmt-low a 0 bits) 0 (quot bits 256))))
(defn- clear [v :vector-i64 from :i64 to :i64] :vector-i64
 (if (= from to) v (clear (put v from 0) (+ from 1) to)))
(defn- filled [v :vector-i64 c :i64] :vector-i64
 (let [a (prepare (clear (clear (clear v 1536 1636) 1664 1705) 1728 1754) c)]
  (copy-image (place-byte a 0 0 (vector-at a 0) 352) 0 768 0)))
(defn- body [v :vector-i64 c :i64] :vector-i64 (final-format (mask-scores (filled v c) 0 0 30000)))
(defn- bodies [v :vector-i64 n :i64 c :i64] :vector-i64
 (if (= n 0) v (bodies (body v c) (- n 1) c)))
(defn- verify-first [v :vector-i64 i :i64] :bool
 (if (= i 22) true
  (and (= (vector-at v i) (expected i)) (verify-first v (+ i 1)))))
(defn batch [n :i64] :i64
 (if (= n 0) 0 (let [v (bodies (vector-alloc 2048) n 0)] (if (verify-first v 0) 1 0))))
(defn observe [encoded :i64] :i64
 (let [c (quot encoded 1048576) code (rem encoded 1048576) stage (quot code 2048) cell (rem code 2048)
       a (filled (vector-alloc 2048) c)
       v (if (= stage 9) (final-format (mask-scores a 0 0 30000))
          (if (= stage 0) a (let [m (- stage 1) b (badcheck (mask-image a m 0))] (put-wide b (+ 1780 m) (vector-at b 1756)))))]
  (vector-at v cell)))
(defn repeat-observe [encoded :i64] :i64
 (let [n (quot encoded 2048) cell (rem encoded 2048)] (vector-at (bodies (vector-alloc 2048) n 0) cell)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 2048) i))
'''
# Extract reviewed constants, not snapshots of expected native output.
s=(a.upstream/'qrtest.c').read_text();nums=[int(x) for x in re.search(r'expected\[22\] = \{(.*?)\}',s,re.S).group(1).replace('\n',' ').split(',') if x.strip()]
def tree(xs,base=0):
 if len(xs)==1:return str(xs[0])
 n=len(xs)//2;return '(if (< i '+str(base+n)+') '+tree(xs[:n],base)+' '+tree(xs[n:],base+n)+')'
forms+=read('(defn- expected [i :i64] :i64 '+tree(nums)+')\n'+new)
if len({f[1] for f in forms})!=len(forms):raise SystemExit('duplicate definitions')
a.directory.mkdir(parents=True,exist_ok=True)
(a.directory/'qr-full.kotoba').write_text('(ns embench.qr-full (:export [batch observe repeat-observe bounds-probe]))\n;; Full v2/L original byte mode, ECC, frame, placement, eight masks, scoring and format.\n;; Copyright 2014-2019 Embecosm/Bristol, qrduino contributors; GPL-3.0-or-later.\n'+'\n'.join(map(emit,forms))+'\n')
(a.directory/'profile.json').write_text(json.dumps({'status':'full-active-v2-profile','sourcePins':pins,'placementSha256':hashlib.sha256(a.placement.read_bytes()).hexdigest(),'workspaceCells':2048,'stages':10,'fields':list(range(100))+list(range(768,868))+list(range(1536,1636))+list(range(1664,1705))},indent=2)+'\n')
s=(a.upstream/'qrencode.c').read_text();begin=s.index('qrencode ()\n{');body=s[begin:];body=body[body.index('{')+1:body.index('\n}\n')]
if body.count('      badness = badcheck ();')!=1:raise SystemExit('QR mask observation boundary changed')
body=body.replace('      badness = badcheck ();','      badness = badcheck ();\n      scores[i]=badness;',1)
body=body.replace('  addfmt (best);','  selected=best; minimum=mindem; stopped=i;\n  addfmt (best);',1)
c='''/* BOOTSTRAP-TOOL: full original QR oracle, mask score snapshots and body selfchecks.
 * Copyright 2014-2019 Embecosm/Bristol, qrduino contributors; GPL-3.0-or-later. */
#include <stdint.h>
#include <limits.h>
#include "beebsc.h"
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/qrduino/qrencode.c"
#include "../upstream/src/qrduino/qrtest.c"
static unsigned char obsheap[8192] __attribute__((aligned));
static const char *payloads[]={"http://www.mageec.com","AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA","","0123456789012345678901234567890123456789"};
static unsigned scores[8],selected,minimum,stopped;
static int setup(int c){memset(obsheap,0,sizeof(obsheap));init_heap_beebs(obsheap,8192);initeccsize(1,22);memcpy(strinbuf,payloads[c],strlen(payloads[c])+1);initframe();memset(scores,0,sizeof(scores));return VERSION==2&&WD==25&&WDB==4;}
static void observed_encode(void){
'''+body+'''
}
static int64_t cellvalue(int cell){
 if(cell>=0&&cell<100)return strinbuf[cell];if(cell>=768&&cell<868)return qrframe[cell-768];
 if(cell>=1536&&cell<1636)return framebase[cell-1536];if(cell>=1664&&cell<1705)return framask[cell-1664];
 if(cell>=1780&&cell<1788)return scores[cell-1780];if(cell==1790)return selected;if(cell==1791)return minimum;if(cell==1792)return stopped;return INT64_MIN;}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe(int64_t encoded,EXTRA){int c=encoded/1048576,code=encoded%1048576,stage=code/2048,cell=code%2048;
 if(encoded<0||c>3||stage>9||!setup(c))return INT64_MIN;
 if(stage==9)observed_encode();else{stringtoqr();fillframe();memcpy(strinbuf,qrframe,100);if(stage){applymask(stage-1);scores[stage-1]=badcheck();}}
 return cellvalue(cell);}
int64_t repeat_observe(int64_t encoded,EXTRA){int n=encoded/2048,cell=encoded%2048;if(n<1||n>32)return INT64_MIN;
 for(int i=0;i<n;i++){if(!setup(0))return INT64_MIN;observed_encode();freeframe();freeecc();}return cellvalue(cell);}
int64_t oracle_selfcheck(int64_t c,EXTRA){if(c<0||c>3||!setup(c))return 0;observed_encode();unsigned char final[100],data[100];memcpy(final,qrframe,100);memcpy(data,strinbuf,100);
 if(!setup(c))return 0;qrencode();return memcmp(final,qrframe,100)==0&&memcmp(data,strinbuf,100)==0&&check_heap_beebs(obsheap);}
int64_t batch(int64_t n,EXTRA){if(n<0||n>32)return 0;if(!n)return 0;benchmark_body(1,n);return verify_benchmark(0);}
int64_t original_repeat_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;benchmark_body(1,n);unsigned char final[100],data[100];memcpy(final,qrframe,100);memcpy(data,strinbuf,100);int ok=verify_benchmark(0);
 for(int i=0;i<n;i++){if(!setup(0))return 0;observed_encode();freeframe();freeecc();}
 return ok&&memcmp(final,qrframe,100)==0&&memcmp(data,strinbuf,100)==0&&check_heap_beebs(obsheap);}
'''
(a.directory/'c-bridge.c').write_text(c)
