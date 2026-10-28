#!/usr/bin/env python3
# BOOTSTRAP-TOOL: pinned QR v2/L codeword fragment, not a full benchmark port.
import argparse,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'qrencode.c':'05d2147e1809578fcdce4ebd6105a555e59dc8c9b5c5b2f4d7a239ea8d9bf5b8','qrframe.c':'3d3400ff94ba165d0cf2945a364527f55291fa144511e0a94f317fdc58992f15','qrtest.c':'7556be13dbcb0f98caaf3722d86b93e49cf3c9ea2f9aaf609f2541aca9867a96','ecctable.h':'54e176fa47d4c20baab098962a0c0f1a8629362499dbc8fbab5d581312b1002c'}
for f,d in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed QR profile: '+f)
s=(a.upstream/'qrencode.c').read_text();a.directory.mkdir(parents=True,exist_ok=True);tables={}
def selector(values,start=0):
 if len(values)==1:return str(values[0])
 mid=len(values)//2;return f'(if (< i {start+mid}) {selector(values[:mid],start)} {selector(values[mid:],start+mid)})'
head='''(ns embench.qr-codewords (:export [observe table-cell bounds-probe]))
;; QR v2/L byte mode padding, RS polynomial, ECC and single-block interleave.
;; Fragment only: matrix framing, placement, mask scoring and format absent.
;; Copyright 2014-2019 Embecosm / University of Bristol, qrduino contributors.
;; SPDX-License-Identifier: GPL-3.0-or-later.
'''
for name in ('g0log','g0exp'):
 text=re.search(r'const unsigned char '+name+r'\[256\].*?= \{(.*?)\};',s,re.S).group(1)
 values=[int(x.strip(),0) for x in text.split(',') if x.strip()];assert len(values)==256;tables[name]=values
 head+=f'(defn- {name} [i :i64] :i64 {selector(values)})\n'
source=head+'''(defn- put [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i (bit-and x 255)))
(defn- payload [c :i64] :string (if (= c 0) "http://www.mageec.com" (if (= c 1) "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" (if (= c 2) "" "0123456789012345678901234567890123456789"))))
(defn- fill [v :vector-i64 s :string i :i64] :vector-i64
 (if (= i (string-length s)) v (fill (put v i (string-code-point-at s i)) s (+ i 1))))
(defn- shift [v :vector-i64 i :i64] :vector-i64
 (if (< i 0) v
  (let [byte (vector-at v i) a (put v (+ i 2) (bit-or (vector-at v (+ i 2)) (* byte 16))) b (put a (+ i 1) (quot byte 16))] (shift b (- i 1)))))
(defn- pads [v :vector-i64 i :i64] :vector-i64
 (if (>= i 34) v (pads (put (put v i 236) (+ i 1) 17) (+ i 2))))
(defn- encode [v :vector-i64 size :i64] :vector-i64
 (let [n (if (>= size 32) 32 size) shifted (shift (put v (+ n 1) 0) (- n 1)) a (put shifted 1 (bit-or (vector-at shifted 1) (* n 16))) b (put a 0 (bit-or 64 (quot n 16)))] (pads b (+ n 2))))
(defn- modnn [x :i64] :i64 (if (>= x 255) (let [a (- x 255)] (modnn (+ (quot a 256) (bit-and a 255)))) x))
(defn- poly-inner [v :vector-i64 i :i64 j :i64] :vector-i64
 (if (= j 0) v
  (let [x (vector-at v (+ 768 j)) prev (vector-at v (+ 768 j -1)) next (if (= x 0) prev (bit-xor prev (g0exp (modnn (+ (g0log x) i)))))] (poly-inner (put v (+ 768 j) next) i (- j 1)))))
(defn- poly-outer [v :vector-i64 i :i64] :vector-i64
 (if (= i 10) v
  (let [a (poly-inner (put v (+ 768 i 1) 1) i i) b (put a 768 (g0exp (modnn (+ (g0log (vector-at a 768)) i))))] (poly-outer b (+ i 1)))))
(defn- poly-logs [v :vector-i64 i :i64] :vector-i64
 (if (= i 11) v (poly-logs (put v (+ 768 i) (g0log (vector-at v (+ 768 i)))) (+ i 1))))
(defn- copy-poly [v :vector-i64 i :i64] :vector-i64
 (if (= i 11) v (copy-poly (put v (+ 800 i) (vector-at v (+ 768 i))) (+ i 1))))
(defn- polynomial [v :vector-i64] :vector-i64 (copy-poly (poly-logs (poly-outer (put v 768 1) 0) 0) 0))
(defn- zero-ecc [v :vector-i64 i :i64] :vector-i64 (if (= i 10) v (zero-ecc (put v (+ 34 i) 0) (+ i 1))))
(defn- ecc-inner [v :vector-i64 fb :i64 j :i64] :vector-i64
 (if (= j 10) v
  (let [next (vector-at v (+ 34 j)) x (if (= fb 255) next (bit-xor next (g0exp (modnn (+ fb (vector-at v (+ 768 (- 10 j))))))))] (ecc-inner (put v (+ 34 j -1) x) fb (+ j 1)))))
(defn- ecc-outer [v :vector-i64 i :i64] :vector-i64
 (if (= i 34) v
  (let [fb (g0log (bit-xor (vector-at v i) (vector-at v 34))) a (ecc-inner v fb 1) b (put a 43 (if (= fb 255) 0 (g0exp (modnn (+ fb (vector-at a 768))))))] (ecc-outer b (+ i 1)))))
(defn- ecc [v :vector-i64] :vector-i64 (ecc-outer (zero-ecc v 0) 0))
(defn- interleave [v :vector-i64 i :i64] :vector-i64
 (if (= i 44) v (interleave (put v (+ 800 i) (vector-at v i)) (+ i 1))))
(defn- copy-back [v :vector-i64 i :i64] :vector-i64
 (if (= i 44) v (copy-back (put v i (vector-at v (+ 800 i))) (+ i 1))))
(defn- stages [v :vector-i64 c :i64 limit :i64] :vector-i64
 (let [s (payload c) a (fill v s 0)] (if (= limit 0) a
  (let [b (encode a (string-length s))] (if (= limit 1) b
   (let [d (polynomial b)] (if (= limit 2) d
    (let [e (ecc d)] (if (= limit 3) e (copy-back (interleave e 0) 0))))))))))
(defn observe [encoded :i64] :i64
 (let [c (quot encoded 8192) code (rem encoded 8192) stage (quot code 1024) cell (rem code 1024) result (stages (vector-alloc 1024) c stage)] (vector-at result cell)))
(defn table-cell [i :i64] :i64 (if (< i 256) (g0log i) (g0exp (- i 256))))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 1024) i))
'''
(a.directory/'qr-codewords.kotoba').write_text(source)
# Observation-only copy of stringtoqr, exact original body plus snapshots.
begin=s.index('stringtoqr (void)\n{');end=s.index('\n//========================================================================\n// Frame data insert',begin);body=s[begin:end];body=body[body.index('{')+1:body.rfind('}')]
assert body.count('// calculate and append ECC')==1
body=body.replace('// calculate and append ECC','snapshot(1);\n  // calculate and append ECC',1)
body=body.replace('initrspoly (eccblkwid, qrframe);','initrspoly (eccblkwid, qrframe);\n  memcpy(poly,qrframe,11);snapshot(2);',1)
body=body.replace('  unsigned j;','  snapshot(3);\n  unsigned j;',1);body+='\nsnapshot(4);\n'
c='''/* BOOTSTRAP-TOOL: original QR codeword functions with snapshots only.
 * Copyright 2014-2019 Embecosm/Bristol; GPL-3.0-or-later. */
#include <stdint.h>
#include <limits.h>
#include <string.h>
#include "../upstream/src/qrduino/qrencode.c"
#include "../upstream/support/beebsc.h"
static unsigned char heap[8192] __attribute__((aligned));
static int64_t states[5][1024];static unsigned char poly[11];
static const char *payloads[]={"http://www.mageec.com","AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA","","0123456789012345678901234567890123456789"};
static void snapshot(int stage){for(int i=0;i<768;i++)states[stage][i]=strinbuf[i];for(int i=0;i<11;i++)states[stage][768+i]=poly[i];for(int i=0;i<44;i++)states[stage][800+i]=qrframe[i];}
static void observed(int c){memset(states,0,sizeof(states));memset(heap,0,sizeof(heap));memset(poly,0,sizeof(poly));init_heap_beebs(heap,8192);initecc(1,2);memcpy(strinbuf,payloads[c],strlen(payloads[c])+1);snapshot(0);
'''+body+'''}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe(int64_t encoded,EXTRA){int c=encoded/8192,code=encoded%8192,stage=code/1024,cell=code%1024;if(encoded<0||c>3||stage>4)return INT64_MIN;observed(c);return states[stage][cell];}
int64_t table_cell(int64_t i,EXTRA){if(i<0||i>=512)return INT64_MIN;return i<256?g0log[i]:g0exp[i-256];}
int64_t oracle_selfcheck(int64_t c,EXTRA){if(c<0||c>3)return 0;observed(c);int64_t saved[1024];memcpy(saved,states[4],sizeof(saved));memset(heap,0,sizeof(heap));init_heap_beebs(heap,8192);initecc(1,2);memcpy(strinbuf,payloads[c],strlen(payloads[c])+1);stringtoqr();for(int i=0;i<768;i++)if(strinbuf[i]!=saved[i])return 0;for(int i=0;i<44;i++)if(qrframe[i]!=saved[800+i])return 0;return check_heap_beebs(heap);}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'status':'fragment-only','version':2,'eccLevel':1,'dataBytes':34,'eccBytes':10,'blocks':1,'sourcePins':pins,'tables':tables},indent=2)+'\n')
