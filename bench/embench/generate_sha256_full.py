#!/usr/bin/env python3
# BOOTSTRAP-TOOL: AST-compose unchanged SHA arithmetic with full ctx lifecycle.
import argparse,ast,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('port',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pin='afe00fb383d29260d82d4bede97d895d2f7bd9070644aa9eecf73feac780980b';helperpin='ac86858674db820b039c11af020f0c8096a2ea84684c21ac26122006d5094f4a'
if hashlib.sha256(a.upstream.read_bytes()).hexdigest()!=pin:raise SystemExit('unreviewed SHA256 profile')
if hashlib.sha256(a.port.read_bytes()).hexdigest()!=helperpin:raise SystemExit('unreviewed SHA256 helper')
module=ast.parse(pathlib.Path(__file__).with_name('generate_picojpeg_coefficients.py').read_text());helpers=[x for x in module.body if isinstance(x,(ast.ClassDef,ast.FunctionDef)) and x.name in ('Vec','read','emit')];exec(compile(ast.Module(body=helpers,type_ignores=[]),'checked AST reader','exec'))
names={'mask32','constants','word-at','ror32','small0','small1','big0','big1'};forms=[f for f in read(a.port.read_text()) if f[0]=='defn-' and f[1] in names]
if {f[1] for f in forms}!=names:raise SystemExit('unreviewed SHA256 helpers')
new='''
(defn- message [] :vector-i64 [97 98 99 100 98 99 100 101 99 100 101 102 100 101 102 103 101 102 103 104 102 103 104 105 103 104 105 106 104 105 106 107 105 106 107 108 106 107 108 109 107 108 109 110 108 109 110 111 109 110 111 112 110 111 112 113])
(defn- initial-word [i :i64] :i64
 (if (= i 0) 1779033703 (if (= i 1) 3144134277 (if (= i 2) 1013904242 (if (= i 3) 2773480762 (if (= i 4) 1359893119 (if (= i 5) 2600822924 (if (= i 6) 528734635 1541459225))))))))
(defn- put [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))
(defn- fill [v :vector-i64 start :i64 end :i64] :vector-i64
 (if (= start end) v (fill (put v start 0) (+ start 1) end)))
(defn- init-words [v :vector-i64 i :i64] :vector-i64
 (if (= i 8) (put (put v 168 0) 169 0) (init-words (put v (+ 128 i) (initial-word i)) (+ i 1))))
(defn- copy-input [v :vector-i64 msg :vector-i64 i :i64] :vector-i64
 (if (= i 56) (put v 169 56) (copy-input (put v i (vector-at msg i)) msg (+ i 1))))
(defn- snapshot-copy [v :vector-i64 source :i64 dest :i64 i :i64 n :i64] :vector-i64
 (if (= i n) v (snapshot-copy (put v (+ dest i) (vector-at v (+ source i))) source dest (+ i 1) n)))
(defn- snapshot-context [v :vector-i64 base :i64 bytes :i64] :vector-i64
 (snapshot-copy (snapshot-copy v 128 base 0 8) 168 (+ base 8) 0 2))
(defn- snapshot-context-block [v :vector-i64 base :i64 bytes :i64] :vector-i64
 (snapshot-copy (snapshot-context v base bytes) 0 (+ base 10) 0 bytes))
(defn- schedule [v :vector-i64 i :i64] :vector-i64
 (if (= i 64) v
  (let [value (if (< i 16) (word-at v 0 i)
   (mask32 (+ (+ (small1 (vector-at v (+ 64 (- i 2)))) (vector-at v (+ 64 (- i 7)))) (+ (small0 (vector-at v (+ 64 (- i 15)))) (vector-at v (+ 64 (- i 16)))))))]
   (schedule (put v (+ 64 i) value) (+ i 1)))))
(defn- finish [v :vector-i64 a :i64 b :i64 c :i64 d :i64 e :i64 f :i64 g :i64 h :i64] :vector-i64
 (put (put (put (put (put (put (put (put v 128 (mask32 (+ (vector-at v 128) a))) 129 (mask32 (+ (vector-at v 129) b))) 130 (mask32 (+ (vector-at v 130) c))) 131 (mask32 (+ (vector-at v 131) d))) 132 (mask32 (+ (vector-at v 132) e))) 133 (mask32 (+ (vector-at v 133) f))) 134 (mask32 (+ (vector-at v 134) g))) 135 (mask32 (+ (vector-at v 135) h))))
(defn- rounds [v :vector-i64 k :vector-i64 i :i64 a :i64 b :i64 c :i64 d :i64 e :i64 f :i64 g :i64 h :i64] :vector-i64
 (if (= i 64) (finish v a b c d e f g h)
  (let [choice (bit-xor (bit-and e f) (bit-and (bit-not e) g)) majority (bit-xor (bit-xor (bit-and a b) (bit-and a c)) (bit-and b c))
        t1 (mask32 (+ (+ h (big1 e)) (+ choice (+ (vector-at k i) (vector-at v (+ 64 i)))))) t2 (mask32 (+ (big0 a) majority))]
   (rounds v k (+ i 1) (mask32 (+ t1 t2)) a b c (mask32 (+ d t1)) e f g))))
(defn- compress [v :vector-i64 k :vector-i64 base :i64 record :bool] :vector-i64
 (let [w (schedule v 0) out (rounds w k 0 (vector-at w 128) (vector-at w 129) (vector-at w 130) (vector-at w 131) (vector-at w 132) (vector-at w 133) (vector-at w 134) (vector-at w 135))]
  (if record (snapshot-copy (snapshot-copy out 0 base 0 64) 128 (+ base 64) 0 8) out)))
(defn- write-output [v :vector-i64 i :i64] :vector-i64
 (if (= i 32) v
  (let [word (vector-at v (+ 128 (quot i 4))) shift (* (- 3 (rem i 4)) 8)]
   (write-output (put v (+ 136 i) (bit-and (u64-shift-right word shift) 255)) (+ i 1)))))
(defn- body [v :vector-i64 msg :vector-i64 k :vector-i64 record :bool] :vector-i64
 (let [a (init-words (fill v 136 168) 0) b (if record (snapshot-context a 170 0) a)
       c (copy-input b msg 0) d (if record (snapshot-context-block c 180 56) c)
       first (compress (fill (put d 56 128) 57 64) k 246 record)
       second (compress (put (put (fill first 0 64) 62 1) 63 192) k 318 record)
       out (init-words (write-output second 0) 0)]
  (if record (snapshot-context-block out 390 64) out)))
(defn- bodies [v :vector-i64 msg :vector-i64 k :vector-i64 n :i64 i :i64 record :bool] :vector-i64
 (if (= i n) v (bodies (body v msg k record) msg k n (+ i 1) record)))
(defn- state [n :i64 record :bool] :vector-i64
 (bodies (vector-alloc (if record 464 170)) (message) (constants) n 0 record))
(defn- expected-byte [i :i64] :i64 (if (= i 0) 36 (if (= i 1) 141 (if (= i 2) 106 (if (= i 3) 97 (if (= i 4) 210 (if (= i 5) 6 (if (= i 6) 56 184))))))))
(defn- verify [v :vector-i64 i :i64 ok :bool] :bool
 (if (= i 8) ok (verify v (+ i 1) (and ok (= (vector-at v (+ 136 i)) (expected-byte i))))))
(defn bench [n :i64] :i64 (if (= n 0) 0 (if (verify (state n false) 0 true) 1 0)))
(defn- pack4 [v :vector-i64 base :i64 i :i64 acc :i64] :i64
 (if (= i 4) acc (pack4 v base (+ i 1) (+ (* acc 256) (vector-at v (+ base i))))))
(defn observe [encoded :i64] :i64
 (let [v (state (quot encoded 512) true) field (rem encoded 512)]
  (if (< field 8) (pack4 v (+ 136 (* field 4)) 0 0) (vector-at v (+ 170 (- field 8))))))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 464) i))
'''
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'sha256-full.kotoba').write_text('(ns embench.sha256-full (:export [bench observe bounds-probe]))\n;; Nettle SHA256 original input; GPL-3.0-or-later, Niels Moller/Embecosm.\n'+'\n'.join(map(emit,forms+read(new)))+'\n')
s=a.upstream.read_text();start=s.index('static void\nsha256_write_digest');end=s.index('\nvoid\nsha256_digest',start);digest=s[start:end].replace('sha256_write_digest','observed_write_digest',1)
start=s.index('benchmark_body(unsigned int lsf, unsigned int gsf)\n{');end=s.index('\n\n\n/*',start);body=s[start:end].replace('benchmark_body(','observed_body(',1)
body=body.replace('nettle_sha256.init (&ctx);','nettle_sha256.init (&ctx);snapctx(&ctx,0,0);',1).replace('nettle_sha256.update (&ctx, sizeof (msg), msg);','nettle_sha256.update (&ctx, sizeof (msg), msg);snapctx(&ctx,10,56);',1).replace('nettle_sha256.digest (&ctx, nettle_sha256.digest_size, buffer);','observed_digest (&ctx, nettle_sha256.digest_size, buffer);',1)
c='''/* BOOTSTRAP-TOOL: unchanged C benchmark plus initialized ctx snapshots. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/src/nettle-sha256/nettle-sha256.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static uint64_t snapshot[294];static int compress_index;
static void snapctx(struct sha256_ctx *ctx,int base,int bytes){for(int i=0;i<8;i++)snapshot[base+i]=ctx->state[i];snapshot[base+8]=ctx->count;snapshot[base+9]=ctx->index;for(int i=0;i<bytes;i++)snapshot[base+10+i]=ctx->block[i];}
static void observed_compress(struct sha256_ctx *ctx,const uint8_t *input){_nettle_sha256_compress(ctx->state,input,K);int base=76+72*compress_index++;for(int i=0;i<64;i++)snapshot[base+i]=input[i];for(int i=0;i<8;i++)snapshot[base+64+i]=ctx->state[i];}
#undef COMPRESS
#define COMPRESS(ctx,data) observed_compress(ctx,data)
'''+digest+'''
static void observed_digest(struct sha256_ctx *ctx,size_t length,uint8_t *out){observed_write_digest(ctx,length,out);sha256_init(ctx);snapctx(ctx,220,64);}
static int
'''+body+'''
int64_t bench(int64_t n,EXTRA){if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t observe(int64_t encoded,EXTRA){int n=encoded/512,f=encoded%512;memset(buffer,0,sizeof(buffer));memset(snapshot,0,sizeof(snapshot));compress_index=0;if(n){for(int i=0;i<n;i++){compress_index=0;observed_body(1,1);}}if(f<8){int64_t acc=0;for(int i=0;i<4;i++)acc=acc*256+buffer[f*4+i];return acc;}if(f<302)return snapshot[f-8];return INT64_MIN;}
int64_t oracle_selfcheck(int64_t n,EXTRA){for(int i=0;i<n;i++){compress_index=0;observed_body(1,1);}uint8_t saved[32];memcpy(saved,buffer,32);int a=verify_benchmark(0);int b=benchmark_body(1,n);return a&&verify_benchmark(b)&&memcmp(saved,buffer,32)==0;}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'sourcePins':{'src/nettle-sha256/nettle-sha256.c':pin},'helperComponentSha256':helperpin,'benchmarkWorkspaceCells':170,'workspaceCells':464,'fields':list(range(302)),'iterations':[0,1,2,17,32],'verification':'original first 8 bytes once after batch; diagnostics compare all 32 bytes','exclusions':'uninitialized block tail after init/update and ctx struct padding'},indent=2)+'\n')
