#!/usr/bin/env python3
# BOOTSTRAP-TOOL: AST-compose unchanged MD5 arithmetic with owned repeated body.
import argparse,ast,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('port',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'src/md5sum/md5.c':'59c2d7bb48faae3cf16dbd3330800dc544e86c1562ec3bebbcb177a6e761c3cf','support/beebsc.c':'b066ac5ff79fdd591da69264919183d03376f5b78985b0eb310cf629dcf8b42c'}
for f,h in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=h:raise SystemExit('unreviewed MD5 profile: '+f)
portpin='9ac1ac3b19119c38332367394304481a4fc273aa3907aaff814c24ea85b01424'
if hashlib.sha256(a.port.read_bytes()).hexdigest()!=portpin:raise SystemExit('unreviewed MD5 helper component')
module=ast.parse(pathlib.Path(__file__).with_name('generate_picojpeg_coefficients.py').read_text());helpers=[x for x in module.body if isinstance(x,(ast.ClassDef,ast.FunctionDef)) and x.name in ('Vec','read','emit')];exec(compile(ast.Module(body=helpers,type_ignores=[]),'checked AST reader','exec'))
names={'mask32','shifts','constants','word-at','rotate-left','round-f','round-g'};forms=[f for f in read(a.port.read_text()) if f[0]=='defn-' and f[1] in names]
if {f[1] for f in forms}!=names:raise SystemExit('unreviewed MD5 helpers')
new='''
(defn- put [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))
(defn- clear-padding [v :vector-i64 i :i64] :vector-i64
 (if (= i 1080) v (clear-padding (put v (+ 1000 i) 0) (+ i 1))))
(defn- input [v :vector-i64 i :i64] :vector-i64
 (if (= i 1000) v (input (put v i (bit-and i 255)) (+ i 1))))
(defn- copy-input [v :vector-i64 i :i64] :vector-i64
 (if (= i 1000) v (copy-input (put v (+ 1000 i) (vector-at v i)) (+ i 1))))
(defn- initial [v :vector-i64] :vector-i64
 (let [w (copy-input (clear-padding (input v 0) 0) 0)]
  (put (put (put (put (put (put (put w 2000 128) 2016 64) 2017 31) 2080 1732584193) 2081 4023233417) 2082 2562383102) 2083 271733878)))
(defn- trace [v :vector-i64 block :i64 i :i64] :vector-i64
 (if (= i 4) v (trace (put v (+ 2084 (+ (* block 4) i)) (vector-at v (+ 2080 i))) block (+ i 1))))
(defn- rounds [v :vector-i64 offset :i64 block :i64 r :vector-i64 k :vector-i64
 i :i64 a0 :i64 b0 :i64 c0 :i64 d0 :i64 a :i64 b :i64 c :i64 d :i64] :vector-i64
 (if (= i 64)
  (put (put (put (put v 2080 (mask32 (+ a0 a))) 2081 (mask32 (+ b0 b))) 2082 (mask32 (+ c0 c))) 2083 (mask32 (+ d0 d)))
  (let [f (round-f i b c d) g (round-g i) sum (mask32 (+ (+ a f) (+ (vector-at k i) (word-at v offset g)))) next-b (mask32 (+ b (rotate-left sum (vector-at r i))))]
   (rounds v offset block r k (+ i 1) a0 b0 c0 d0 d next-b b c))))
(defn- compress-all [v :vector-i64 r :vector-i64 k :vector-i64 block :i64 record :bool] :vector-i64
 (if (= block 16) v
  (let [a (vector-at v 2080) b (vector-at v 2081) c (vector-at v 2082) d (vector-at v 2083) w (rounds v (+ 1000 (* block 64)) block r k 0 a b c d a b c d)]
   (compress-all (if record (trace w block 0) w) r k (+ block 1) record))))
(defn- bodies [v :vector-i64 r :vector-i64 k :vector-i64 n :i64 i :i64 record :bool] :vector-i64
 (if (= i n) v (bodies (compress-all (initial v) r k 0 record) r k n (+ i 1) record)))
(defn- state [n :i64 record :bool] :vector-i64 (bodies (vector-alloc (if record 2148 2084)) (shifts) (constants) n 0 record))
(defn bench [n :i64] :i64
 (if (= n 0) 0
  (let [v (state n false) result (bit-xor (bit-xor (vector-at v 2080) (vector-at v 2081)) (bit-xor (vector-at v 2082) (vector-at v 2083)))]
   (if (= result 871789492) 1 0))))
(defn- pack4 [v :vector-i64 base :i64 i :i64 acc :i64] :i64
 (if (= i 4) acc (pack4 v base (+ i 1) (+ (* acc 256) (vector-at v (+ base i))))))
(defn observe [encoded :i64] :i64
 (let [v (state (quot encoded 1024) true) field (rem encoded 1024)]
  (if (< field 520) (pack4 v (* field 4) 0 0) (vector-at v (+ 2080 (- field 520))))))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 2148) i))
'''
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'md5-full.kotoba').write_text('(ns embench.md5-full (:export [bench observe bounds-probe]))\n;; Complete original 1000-byte MD5 profile; SPDX-License-Identifier: MIT.\n'+'\n'.join(map(emit,forms+read(new)))+'\n')
s=(a.upstream/'src/md5sum/md5.c').read_text();start=s.index('void md5(');end=s.index('\nvoid\ninitialise_benchmark',start);md5=s[start:end].replace('void md5(','static void observed_md5(',1);needle='        h3 += d;';assert md5.count(needle)==1;md5=md5.replace(needle,needle+'\n        snapshot[offset/64][0]=h0;snapshot[offset/64][1]=h1;snapshot[offset/64][2]=h2;snapshot[offset/64][3]=h3;',1)
start=s.index('benchmark_body(unsigned int lsf, unsigned int gsf, int len)\n{');end=s.index('\nint\nverify_benchmark',start);body=s[start:end].replace('benchmark_body(','observed_body(',1).replace('md5(msg, len);','observed_md5(msg, len);',1)
c='''/* BOOTSTRAP-TOOL: original C body and diagnostic post-block capture. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/support/beebsc.c"
#include "../upstream/src/md5sum/md5.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static uint32_t snapshot[16][4];
'''+md5+'\nstatic int\n'+body+'''
int64_t bench(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n,MSG_SIZE));}
int64_t observe(int64_t encoded,EXTRA){int n=encoded/1024,f=encoded%1024;memset(heap,0,sizeof(heap));memset(snapshot,0,sizeof(snapshot));h0=h1=h2=h3=0;if(n)observed_body(1,n,MSG_SIZE);if(f<520){int64_t acc=0;for(int i=0;i<4;i++)acc=acc*256+(unsigned char)heap[f*4+i];return acc;}if(f<524){uint32_t digest[4]={h0,h1,h2,h3};return digest[f-520];}if(f<588)return snapshot[(f-524)/4][(f-524)%4];return INT64_MIN;}
int64_t oracle_selfcheck(int64_t n,EXTRA){int a=observed_body(1,n,MSG_SIZE);uint32_t digest[4]={h0,h1,h2,h3};unsigned char saved[2080];memcpy(saved,heap,2080);int b=benchmark_body(1,n,MSG_SIZE);return a==b&&verify_benchmark(a)&&verify_benchmark(b)&&digest[0]==h0&&digest[1]==h1&&digest[2]==h2&&digest[3]==h3&&memcmp(saved,heap,2080)==0;}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'sourcePins':pins,'helperComponentSha256':portpin,'workspaceCells':2148,'inputBytes':1000,'paddedAllocationBytes':1080,'processedBlocks':16,'fields':list(range(588)),'iterations':[0,1,2,17,32],'verification':'original XOR once after batch'},indent=2)+'\n')
