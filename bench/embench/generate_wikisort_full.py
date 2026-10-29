#!/usr/bin/env python3
# BOOTSTRAP-TOOL: original 400-element/cache-512 profile, all nine generators.
import argparse,pathlib,hashlib,json,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={}
# Filled with reviewed upstream hashes below; refuse changed algorithm/RNG.
EXPECTED = {'src/wikisort/libwikisort.c':'8cad015cb2e79a78ad85b1d467db60310e7265e45ce2d4584777cd6501a8e93d','support/beebsc.c':'b066ac5ff79fdd591da69264919183d03376f5b78985b0eb310cf629dcf8b42c'}
for f,d in EXPECTED.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed WikiSort profile: '+f)
 pins[f]=d
s=(a.upstream/'src/wikisort/libwikisort.c').read_text();pairs=re.findall(r'\{\s*(-?\d+)\s*,\s*(-?\d+)\s*\}',s[s.index('Test exp[]'):s.index('initialise_benchmark')]);values=[int(x) for pair in pairs for x in pair]
if len(values)!=800:raise SystemExit('original verifier shape changed')
def tree(xs,start=0):
 if len(xs)==1:return str(xs[0])
 m=len(xs)//2;return '(if (< i '+str(start+m)+') '+tree(xs[:m],start)+' '+tree(xs[m:],start+m)+')'
head='(ns embench.wikisort-full (:export [batch observe repeat-observe bounds-probe]))\n;; Original 400-item/cache-512 path, nine generators and stable value/index pairs.\n;; Copyright 2014-2019 Embecosm/Bristol and WikiSort contributors; GPL-3.0-or-later.\n'
source='''
(defn- put [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))
(defn- bump [v :vector-i64 i :i64] :vector-i64 (put v i (+ (vector-at v i) 1)))
(defn- int32 [x :i64] :i64 (let [u (bit-and x 4294967295)] (if (>= u 2147483648) (- u 4294967296) u)))
(defn- value [v :vector-i64 i :i64] :i64 (vector-at v (* i 2)))
(defn- item [v :vector-i64 to :i64 from :i64] :vector-i64
 (let [x (value v from) j (vector-at v (+ (* from 2) 1))] (put (put v (* to 2) x) (+ (* to 2) 1) j)))
(defn- fill [v :vector-i64 c :i64 i :i64] :vector-i64
 (if (= i 400) v
  (let [random? (or (= c 1) (= c 2) (= c 3) (= c 7) (= c 8))
        next (if random? (bit-and (+ (* (vector-at v 1830) 1103515245) 12345) 2147483647) (vector-at v 1830))
        r (quot next 65536)
        x (if (= c 0) (if (= i 0) 10 (if (< i 200) 11 (if (= i 399) 10 9)))
           (if (= c 1) r (if (= c 2) (+ (- 400 i) (* r 429496729) -2)
            (if (= c 3) (+ i (* r 429496729) -2) (if (= c 4) i
             (if (= c 5) (- 400 i) (if (= c 6) 1000
              (if (= c 7) (if (<= (quot r 1932735283) 1) i (- i 2)) (+ 1000 (rem r 4))))))))))
        a (put v 1830 next)]
   (fill (put (put a (* i 2) (int32 x)) (+ (* i 2) 1) i) c (+ i 1)))))
(defn- insertion-inner [v :vector-i64 start :i64 j :i64 x :i64 index :i64] :vector-i64
 (if (and (> j start) (< x (value v (- j 1))))
  (insertion-inner (item v j (- j 1)) start (- j 1) x index)
  (put (put v (* j 2) x) (+ (* j 2) 1) index)))
(defn- insertion [v :vector-i64 start :i64 end :i64 i :i64] :vector-i64
 (if (= i end) v
  (let [x (value v i) index (vector-at v (+ (* i 2) 1))]
   (insertion (insertion-inner v start i x index) start end (+ i 1)))))
(defn- copy-forward [v :vector-i64 to :i64 from :i64 n :i64 i :i64] :vector-i64
 (if (= i n) v (copy-forward (item v (+ to i) (+ from i)) to from n (+ i 1))))
(defn- copy-backward [v :vector-i64 to :i64 from :i64 i :i64] :vector-i64
 (if (< i 0) v (copy-backward (item v (+ to i) (+ from i)) to from (- i 1))))
(defn- rotate [v :vector-i64 start :i64 mid :i64 end :i64] :vector-i64
 (let [left (- mid start) right (- end mid) a (bump v 1833)]
  (if (<= left right)
   (let [b (copy-forward a 400 start left 0) c (copy-forward b start mid right 0)]
    (copy-forward c (+ start right) 400 left 0))
   (let [b (copy-forward a 400 mid right 0) c (copy-backward b (+ start right) start (- left 1))]
    (copy-forward c start 400 right 0)))))
(defn- merge-loop [v :vector-i64 a :i64 alast :i64 b :i64 blast :i64 dst :i64] :vector-i64
 (if (or (= a alast) (= b blast)) (copy-forward v dst a (- alast a) 0)
  (if (>= (value v b) (value v a))
   (merge-loop (item v dst a) (+ a 1) alast b blast (+ dst 1))
   (merge-loop (item v dst b) a alast (+ b 1) blast (+ dst 1)))))
(defn- wiki-merge [v :vector-i64 start :i64 mid :i64 end :i64] :vector-i64
 (let [a (copy-forward (bump v 1834) 400 start (- mid start) 0)]
  (merge-loop a 400 (+ 400 (- mid start)) mid end start)))
(defn- floor-power [n :i64] :i64
 (let [a (bit-or n (quot n 2)) b (bit-or a (quot a 4)) c (bit-or b (quot b 16))
       d (bit-or c (quot c 256)) e (bit-or d (quot d 65536)) f (bit-or e (quot e 4294967296))]
  (- f (quot f 2))))
(defn- insertion-chunks [v :vector-i64 decimal :i64 fractional :i64 base :i64 ds :i64 fs :i64] :vector-i64
 (if (= decimal 400) v
  (let [f (+ fractional fs) carry (>= f base) end (+ decimal ds (if carry 1 0)) nf (if carry (- f base) f)]
   (insertion-chunks (insertion (bump v 1831) decimal end (+ decimal 1)) end nf base ds fs))))
(defn- merge-pairs [v :vector-i64 decimal :i64 fractional :i64 base :i64 ds :i64 fs :i64] :vector-i64
 (if (= decimal 400) v
  (let [f (+ fractional fs) carry (>= f base) mid (+ decimal ds (if carry 1 0)) nf (if carry (- f base) f)
        g (+ nf fs) again (>= g base) end (+ mid ds (if again 1 0)) ng (if again (- g base) g)
        a (if (< (value v (- end 1)) (value v decimal)) (rotate v decimal mid end)
           (if (< (value v mid) (value v (- mid 1))) (wiki-merge v decimal mid end) v))]
   (merge-pairs a end ng base ds fs))))
(defn- levels [v :vector-i64 ms :i64 power :i64 base :i64 ds :i64 fs :i64] :vector-i64
 (if (>= ms power) v
  (let [a (merge-pairs (bump v 1832) 0 0 base ds fs) f (* fs 2) carry (>= f base)
        nd (+ (* ds 2) (if carry 1 0)) nf (if carry (- f base) f)]
   (levels a (* ms 2) power base nd nf))))
(defn- sort [v :vector-i64] :vector-i64
 (let [p (floor-power 400) base (quot p 16) fs (rem 400 base) ds (quot 400 base)]
  (levels (insertion-chunks v 0 0 base ds fs) 16 p base ds fs)))
(defn- cases [v :vector-i64 c :i64 stop :i64 phase :i64] :vector-i64
 (let [a (fill v c 0)]
  (if (and (= c stop) (= phase 0)) a
   (let [b (sort a)] (if (= c stop) b (cases b (+ c 1) stop phase))))))
(defn- reset [v :vector-i64 i :i64] :vector-i64
 (if (= i 1835) v (reset (put v i 0) (+ i 1))))
(defn- body [v :vector-i64] :vector-i64 (cases (reset v 1830) 0 8 1))
(defn- bodies [v :vector-i64 n :i64] :vector-i64
 (if (= n 0) v (bodies (body v) (- n 1))))
(defn- verify [v :vector-i64 i :i64] :bool
 (if (= i 800) true (and (= (vector-at v i) (expected i)) (verify v (+ i 1)))))
(defn batch [n :i64] :i64
 (if (= n 0) 0 (let [v (bodies (vector-alloc 2048) n)] (if (verify v 0) 1 0))))
(defn observe [encoded :i64] :i64
 (let [stage (quot encoded 2048) cell (rem encoded 2048) c (quot stage 2) phase (rem stage 2)]
  (vector-at (cases (vector-alloc 2048) 0 c phase) cell)))
(defn repeat-observe [encoded :i64] :i64
 (let [n (quot encoded 2048) cell (rem encoded 2048)] (vector-at (bodies (vector-alloc 2048) n) cell)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 2048) i))
'''
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'wikisort-full.kotoba').write_text(head+'(defn- expected [i :i64] :i64 '+tree(values)+')\n'+source)
# Retain the entire original WikiSort in the C observation copy, including dormant branches.
begin=s.index('WikiSort (Test array[]');body=s[begin:];body=body[:body.index('\n#undef CACHE_SIZE')+len('\n#undef CACHE_SIZE')];body=body[body.index('{')+1:]
replacements={
'      InsertionSort (array, MakeRange (0, size), compare);':'      counts[0]++; InsertionSort (array, MakeRange (0, size), compare);',
'      InsertionSort (array, MakeRange (start, end), compare);':'      counts[0]++; InsertionSort (array, MakeRange (start, end), compare);',
'      long block_size = sqrt (decimal_step);':'      counts[1]++; long block_size = sqrt (decimal_step);',
'      Rotate (array, mid - start, MakeRange (start, end), cache,':'      counts[2]++; Rotate (array, mid - start, MakeRange (start, end), cache,',
'  memcpy (&cache[0], &array[A.start],':'  counts[3]++; memcpy (&cache[0], &array[A.start],',
'\t      if (Range_length (level1) > 0)':'\t      fallback++; if (Range_length (level1) > 0)'}
for old,new in replacements.items():
 if body.count(old)!=1:raise SystemExit('WikiSort observation boundary changed: '+old)
 body=body.replace(old,new,1)
c='''/* BOOTSTRAP-TOOL: full original WikiSort body + branch counters.
 * Copyright 2014-2019 Embecosm/Bristol and WikiSort contributors; GPL-3.0-or-later. */
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/support/beebsc.c"
#include "../upstream/src/wikisort/libwikisort.c"
static long counts[4],fallback;
static void observed_sort(Test array[],long size,Comparison compare){
'''+body+'''\n}
static TestCasePtr modes[9]={TestingPathological,TestingRandom,TestingMostlyDescending,TestingMostlyAscending,TestingAscending,TestingDescending,TestingEqual,TestingJittered,TestingMostlyEqual};
static void reset(void){srand_beebs(0);memset(counts,0,sizeof(counts));fallback=0;}
static void cases(int stop,int phase){reset();for(int c=0;c<=stop;c++){for(int i=0;i<400;i++){array1[i].value=modes[c](i,400);array1[i].index=i;}if(c!=stop||phase)observed_sort(array1,400,TestCompare);}}
static int64_t cellvalue(int cell){if(cell>=0&&cell<800)return (cell&1)?array1[cell/2].index:array1[cell/2].value;if(cell==1830)return seed;if(cell>=1831&&cell<1835)return counts[cell-1831];return INT64_MIN;}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe(int64_t encoded,EXTRA){int stage=encoded/2048,cell=encoded%2048;if(stage<0||stage>17||RAND_MAX!=2147483647||sizeof(long)!=8)return INT64_MIN;cases(stage/2,stage%2);return cellvalue(cell);}
int64_t repeat_observe(int64_t encoded,EXTRA){int n=encoded/2048,cell=encoded%2048;if(n<1||n>32)return INT64_MIN;for(int i=0;i<n;i++)cases(8,1);return cellvalue(cell);}
int64_t batch(int64_t n,EXTRA){if(n<1||n>32)return 0;benchmark_body(1,n);return verify_benchmark(0);}
int64_t oracle_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;benchmark_body(1,n);Test saved[400];memcpy(saved,array1,sizeof(saved));int ok=verify_benchmark(0);for(int i=0;i<n;i++)cases(8,1);return ok&&!fallback&&memcmp(saved,array1,sizeof(saved))==0&&verify_benchmark(0);}
int64_t unsupported_branches(int64_t stage,EXTRA){cases(stage/2,stage%2);return fallback;}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'status':'full-original-400/cache-512-profile','sourcePins':pins,'maxSize':400,'cacheSize':512,'workspaceCells':2048,'fields':list(range(800))+list(range(1830,1835)),'stages':18},indent=2)+'\n')
