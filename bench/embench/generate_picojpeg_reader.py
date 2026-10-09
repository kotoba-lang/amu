#!/usr/bin/env python3
# BOOTSTRAP-TOOL: original fixture and input/bit-reservoir primitive fragment.
import argparse,pathlib,hashlib,json,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'libpicojpeg.c':'ed1fb932e9c2c15796bbe6caea8e2e53e61d1349fae4afc1d71847eeebb9185d','picojpeg.h':'50dbd519c3e7b5732cc2e58d9e47195a3e5652f5d14f9d997f102b844e64db36','picojpeg_test.c':'fab1ba5e93f854512ff10910e2b304b20f42a6d579db1793c7aa87e398188f8a'}
for f,d in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed picojpeg reader profile: '+f)
s=(a.upstream/'picojpeg_test.c').read_text();data=[int(x,16) for x in re.findall(r'0x([0-9a-fA-F]+)',re.search(r'jpeg_data\[\] = \{(.*?)\};',s,re.S).group(1))]
def tree(xs,name='i',start=0):
 if len(xs)==1:return str(xs[0])
 n=len(xs)//2;return '(if (< '+name+' '+str(start+n)+') '+tree(xs[:n],name,start)+' '+tree(xs[n:],name,start+n)+')'
head='(ns embench.picojpeg-reader (:export [observe bounds-probe]))\n;; Input/bit reader fragment only; marker/Huffman/IDCT/color decoder remains open.\n;; Copyright 2014-2019 Embecosm/Bristol; picojpeg Rich Geldreich, public domain.\n'
source='''
(defn- put [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))
(defn- put8 [v :vector-i64 i :i64 x :i64] :vector-i64 (put v i (bit-and x 255)))
(defn- put16 [v :vector-i64 i :i64 x :i64] :vector-i64 (put v i (bit-and x 65535)))
(defn- copy-input [v :vector-i64 n :i64 offset :i64 i :i64] :vector-i64
 (if (= i n) v (copy-input (put8 v (+ 4 i) (jpeg-byte (+ offset i))) n offset (+ i 1))))
(defn- refill [v :vector-i64] :vector-i64
 (let [offset (vector-at v 261) remain (- JPEG_LENGTH offset) n (if (< remain 252) remain 252)
       a (put (put8 (put8 v 256 4) 257 n) 261 (+ offset n))]
  (copy-input a n offset 0)))
(defn- char [v :vector-i64] :vector-i64
 (let [a (if (= (vector-at v 257) 0) (refill v) v)]
  (if (= (vector-at a 257) 0)
   (let [tem (bit-xor (vector-at a 258) 255)] (put (put8 a 258 tem) 263 (if (not= tem 0) 255 217)))
   (let [offset (vector-at a 256) ret (vector-at a offset)]
    (put (put8 (put8 a 257 (- (vector-at a 257) 1)) 256 (+ offset 1)) 263 ret)))))
(defn- stuff [v :vector-i64 c :i64] :vector-i64
 (let [offset (bit-and (- (vector-at v 256) 1) 255) left (vector-at v 257)]
  (put8 (put8 (put8 v 256 offset) offset c) 257 (+ left 1))))
(defn- octet [v :vector-i64 flag :i64] :vector-i64
 (let [a (char v) c (vector-at a 263)]
  (if (and (not= flag 0) (= c 255))
   (let [b (char a) n (vector-at b 263) d (if (not= n 0) (stuff (stuff b n) 255) b)] (put d 263 c)) a)))
(defn- refill-bits [v :vector-i64 flag :i64 pre :i64 post :i64] :vector-i64
 (let [a (put16 v 259 (* (vector-at v 259) (pow pre))) b (octet a flag)
       bits (bit-or (vector-at b 259) (vector-at b 263))]
  (put16 b 259 (* bits (pow post)))))
(defn- bits [v :vector-i64 width :i64 flag :i64] :vector-i64
 (let [left (vector-at v 260) ret (vector-at v 259) large (> width 8)
       a (if large (refill-bits v flag left (- 8 left)) v)
       next-ret (if large (bit-or (bit-and ret 65280) (quot (vector-at a 259) 256)) ret)
       n (if large (- width 8) width)
       b (if (< left n)
          (put8 (refill-bits a flag left (- n left)) 260 (- 8 (- n left)))
          (put16 (put8 a 260 (- left n)) 259 (* (vector-at a 259) (pow n))))]
  (put b 263 (quot next-ret (pow (- 16 width))))))
(defn- bit [v :vector-i64] :vector-i64
 (let [ret (if (not= (bit-and (vector-at v 259) 32768) 0) 1 0)
       a (if (= (vector-at v 260) 0)
          (let [b (octet v 1)] (put8 (put16 b 259 (bit-or (vector-at b 259) (vector-at b 263))) 260 8)) v)
       b (put16 (put8 a 260 (- (vector-at a 260) 1)) 259 (* (vector-at a 259) 2))]
  (put b 263 ret)))
(defn- fix [v :vector-i64] :vector-i64
 (let [a (if (> (vector-at v 260) 0) (stuff v (vector-at v 259)) v)
       b (stuff a (quot (vector-at a 259) 256)) c (put8 b 260 8)]
  (put (bits (bits c 8 1) 8 1) 263 -1)))
(defn- init [v :vector-i64] :vector-i64 (put (bits (bits (put8 v 260 8) 8 0) 8 0) 263 0))
(defn- actions [v :vector-i64 mode :i64 limit :i64 i :i64] :vector-i64
 (if (= i limit) v
  (let [n (+ 1 (rem i 16)) op (rem i 5)
        a (if (= mode 0) (char v)
           (if (= mode 1) (bits v n 0) (if (= mode 2) (bits v n 1)
            (if (= op 0) (bits v n (rem i 2)) (if (= op 1) (bit v)
             (if (= op 2) (char v) (if (= op 3) (octet v 1) (fix v))))))))]
   (actions a mode limit (+ i 1)))))
(defn observe [encoded :i64] :i64
 (let [mode (quot encoded 1048576) code (rem encoded 1048576) limit (quot code 512) cell (rem code 512)
       v (vector-alloc 512) a (if (= mode 0) (put8 v 260 8) (init v))]
  (vector-at (actions a mode limit 0) cell)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 512) i))
'''.replace('JPEG_LENGTH',str(len(data)))
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'picojpeg-reader.kotoba').write_text(head+'(defn- jpeg-byte [i :i64] :i64 '+tree(data)+')\n(defn- pow [i :i64] :i64 '+tree([1<<i for i in range(17)])+')\n'+source)
c='''/* BOOTSTRAP-TOOL: unchanged original reader primitives on original fixture. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/src/picojpeg/libpicojpeg.c"
#include "../upstream/src/picojpeg/picojpeg_test.c"
static int last;
static void reset(int mode){memset(gInBuf,0,sizeof(gInBuf));jpeg_off=0;g_pNeedBytesCallback=pjpeg_need_bytes_callback;g_pCallback_data=0;gCallbackStatus=0;gInBufOfs=gInBufLeft=gTemFlag=gBitBuf=0;gBitsLeft=8;last=0;if(mode)init();}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe(int64_t encoded,EXTRA){int mode=encoded/1048576,code=encoded%1048576,limit=code/512,cell=code%512;if(encoded<0||mode>3)return INT64_MIN;reset(mode);
 for(int i=0;i<limit;i++){int n=1+i%16,op=i%5;if(mode==0)last=getChar();else if(mode==1)last=getBits1(n);else if(mode==2)last=getBits2(n);else if(op==0)last=getBits(n,i%2);else if(op==1)last=getBit();else if(op==2)last=getChar();else if(op==3)last=getOctet(1);else{fixInBuffer();last=-1;}}
 if(cell<256)return gInBuf[cell];switch(cell){case 256:return gInBufOfs;case 257:return gInBufLeft;case 258:return gTemFlag;case 259:return gBitBuf;case 260:return gBitsLeft;case 261:return jpeg_off;case 262:return gCallbackStatus;case 263:return last;default:return INT64_MIN;}}
int64_t decoder_selfcheck(int64_t n,EXTRA){benchmark_body(1,n);return verify_benchmark(0);}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'status':'input-reader-fragment-only','sourcePins':pins,'jpegLength':len(data),'fields':list(range(264)),'prefixes':[0,1,2,7,16,252,253,1024]},indent=2)+'\n')
