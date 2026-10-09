#!/usr/bin/env python3
# BOOTSTRAP-TOOL: AST composition of checked fragments and new placement algorithm.
import argparse,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('codewords',type=pathlib.Path);p.add_argument('frame',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'qrencode.c':'05d2147e1809578fcdce4ebd6105a555e59dc8c9b5c5b2f4d7a239ea8d9bf5b8','qrframe.c':'3d3400ff94ba165d0cf2945a364527f55291fa144511e0a94f317fdc58992f15','ecctable.h':'54e176fa47d4c20baab098962a0c0f1a8629362499dbc8fbab5d581312b1002c'}
for f,d in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed QR placement profile: '+f)
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
def change(x,old,new):
 if isinstance(x,list):return type(x)(change(y,old,new) for y in x)
 return new if x==old else x
cw=read(a.codewords.read_text());fr=read(a.frame.read_text());forms=[]
for f in cw:
 if f[0]!='defn-':continue
 name=f[1]
 if name=='stages':break
 if name=='copy-poly':continue
 if name in ('interleave','copy-back'):f=change(f,'800','768')
 if name=='polynomial':f=read('(defn- polynomial [v :vector-i64] :vector-i64 (poly-logs (poly-outer (put v 768 1) 0) 0))')[0]
 forms.append(f)
for f in fr:
 if f[0]!='defn-':continue
 name=f[1]
 if name=='stages':break
 if name=='put':continue
 if name=='bit-index':f=read('(defn- bit-index [x :i64 y :i64] :i64 (+ 1536 (quot x 8) (* y 4)))')[0]
 if name=='reserve':f=change(f,'128','1664')
 forms.append(f)
new='''(defn- initial-frame [v :vector-i64] :vector-i64
 (black-mask (timing (format-y (format-x (format-first (gap-x (gap-y (set-bit (aligns (finders v) 18 15) 8 17) 0) 0) 0) 0) 0) 0) 0))
(defn- copy-base [v :vector-i64 i :i64] :vector-i64
 (if (= i 100) v (copy-base (put v (+ 768 i) (vector-at v (+ 1536 i))) (+ i 1))))
(defn- reserved? [v :vector-i64 x :i64 y :i64] :bool
 (let [lo (if (> x y) y x) hi (if (> x y) x y) bt (+ (quot (+ (* hi hi) hi) 2) lo)]
  (not= (bit-and (vector-at v (+ 1664 (quot bt 8))) (weight (rem bt 8))) 0)))
(defn- data-bit [v :vector-i64 x :i64 y :i64] :vector-i64
 (let [i (+ 768 (quot x 8) (* y 4))] (put v i (bit-or (vector-at v i) (weight (rem x 8))))))
(defn- position [v :vector-i64 x :i64 y :i64 dy :i64 hv :i64] :vector-i64
 (put (put (put (put v 1760 x) 1761 y) 1762 dy) 1763 hv))
(defn- advance [v :vector-i64] :vector-i64
 (let [x (vector-at v 1760) y (vector-at v 1761) dy (vector-at v 1762) hv (vector-at v 1763)]
  (if (= hv 1) (position v (- x 1) y dy 0)
   (let [next-x (+ x 1)]
    (if (= dy 1)
     (if (not= y 0) (position v next-x (- y 1) dy 1)
      (let [a (- next-x 2)] (if (= a 6) (position v (- a 1) 9 0 1) (position v a y 0 1))))
     (if (not= y 24) (position v next-x (+ y 1) dy 1)
      (let [a (- next-x 2)] (if (= a 6) (position v (- a 1) (- y 8) 1 1) (position v a y 1 1)))))))))
(defn- next-free [v :vector-i64] :vector-i64
 (let [a (advance v)] (if (reserved? a (vector-at a 1760) (vector-at a 1761)) (next-free a) a)))
(defn- place-byte [v :vector-i64 i :i64 j :i64 d :i64 limit :i64] :vector-i64
 (if (>= (+ (* i 8) j) limit) v
  (if (= j 8) (place-byte v (+ i 1) 0 (vector-at v (+ i 1)) limit)
   (let [a (if (not= (bit-and d 128) 0) (data-bit v (vector-at v 1760) (vector-at v 1761)) v)]
    (place-byte (next-free a) i (+ j 1) (bit-and (* d 2) 255) limit)))))
(defn- prepare [v :vector-i64 c :i64] :vector-i64
 (let [s (payload c) a (put (fill v s 0) (string-length s) 0) b (initial-frame a)
       d (copy-back (interleave (ecc (polynomial (encode b (string-length s)))) 0) 0)]
  (position (copy-base d 0) 24 24 1 1)))
(defn observe [encoded :i64] :i64
 (let [c (quot encoded 1048576) code (rem encoded 1048576) limit (quot code 2048) cell (rem code 2048)
       a (prepare (vector-alloc 2048) c) result (place-byte a 0 0 (vector-at a 0) limit)] (vector-at result cell)))
(defn bounds-probe [i :i64] :i64 (vector-at (vector-alloc 2048) i))
'''
forms+=read(new);names=[f[1] for f in forms];assert len(set(names))==len(names)
a.directory.mkdir(parents=True,exist_ok=True)
head='''(ns embench.qr-placement (:export [observe bounds-probe]))
;; AST-composed v2/L codewords + base frame + original data placement path.
;; Fragment only: masks, penalties, selection and final format remain open.
;; Copyright 2014-2019 Embecosm/Bristol, qrduino contributors; GPL-3.0-or-later.
'''
(a.directory/'qr-placement.kotoba').write_text(head+'\n'.join(map(emit,forms))+'\n')
s=(a.upstream/'qrencode.c').read_text();begin=s.index('fillframe (void)\n{');end=s.index('\n//========================================================================\n// Masking',begin);body=s[begin:end];body=body[body.index('{')+1:body.rfind('}')]
assert body.count('  ffgohv = 1;')==1;body=body.replace('  ffgohv = 1;','  ffgohv = 1;\n  snapshot(0,x,y,ffdecy,ffgohv);',1)
assert body.count('  while (ismasked (x, y));')==1;body=body.replace('  while (ismasked (x, y));','  while (ismasked (x, y));\n  snapshot(++bits,x,y,ffdecy,ffgohv);',1)
c='''/* BOOTSTRAP-TOOL: unchanged original codewords/frame + placement snapshots.
 * Copyright 2014-2019 Embecosm/Bristol, qrduino contributors; GPL-3.0-or-later. */
#include <stdint.h>
#include <limits.h>
#include "beebsc.h"
#include "../upstream/src/qrduino/qrencode.c"
static unsigned char heap[8192] __attribute__((aligned));
static unsigned char images[353][100],positions[353][4];
static const char *payloads[]={"http://www.mageec.com","AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA","","0123456789012345678901234567890123456789"};
static void snapshot(int n,int x,int y,int dy,int hv){memcpy(images[n],qrframe,100);positions[n][0]=x;positions[n][1]=y;positions[n][2]=dy;positions[n][3]=hv;}
static int prepare(int c){memset(heap,0,sizeof(heap));init_heap_beebs(heap,8192);initeccsize(1,22);memcpy(strinbuf,payloads[c],strlen(payloads[c])+1);initframe();stringtoqr();return VERSION==2&&WD==25&&WDB==4;}
static void observed(void){int bits=0;
'''+body+'''}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe(int64_t encoded,EXTRA){int c=encoded/1048576,code=encoded%1048576,n=code/2048,cell=code%2048;
 if(encoded<0||c>3||n>352||!prepare(c))return INT64_MIN;observed();
 if(cell>=768&&cell<868)return images[n][cell-768];if(cell>=1760&&cell<1764)return positions[n][cell-1760];
 if(cell<44)return strinbuf[cell];if(cell>=1536&&cell<1636)return framebase[cell-1536];if(cell>=1664&&cell<1705)return framask[cell-1664];return INT64_MIN;}
int64_t oracle_selfcheck(int64_t c,EXTRA){if(c<0||c>3||!prepare(c))return 0;observed();unsigned char saved[100];memcpy(saved,images[352],100);
 if(!prepare(c))return 0;fillframe();return memcmp(saved,qrframe,100)==0&&check_heap_beebs(heap);}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'status':'placement-fragment-only','bits':352,'sourcePins':pins,'componentSha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.codewords,a.frame)},'composition':'parsed forms; contextual relocation; no component source edits'},indent=2)+'\n')
