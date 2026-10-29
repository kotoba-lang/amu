#!/usr/bin/env python3
# BOOTSTRAP-TOOL: pinned generated-transition extraction; execution is Kotoba.
import argparse, hashlib, itertools, json, pathlib, re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
b=a.upstream.read_bytes()
if hashlib.sha256(b).hexdigest()!='7d15a238b045f23d5206406fe0d5a15bd4050cf0ccd7e4c3dc49fb71429e2081':raise SystemExit('unreviewed NSichneu profile')
s=b.decode();markers=list(re.finditer(r'/\* Permutation for Place P([12]) : ([0-9, ]+) \*/',s));assert len(markers)==126
end=s.index('\n      }\n\n  return 0;',markers[-1].end())
def normalize(text):
 return re.sub(r'[\s()]','',re.sub(r'/\*.*?\*/','',text,flags=re.S))
records=[]
for k,m in enumerate(markers):
 place=int(m[1]);v=[int(i) for i in m[2].split(',')]
 block=s[m.end():markers[k+1].start() if k+1<len(markers) else end]
 if place==1:
  x,y,z=v;expected=f'''if ((P1_is_marked >= 3) && (P3_is_marked + 3 <= 6) && (P1_marking_member_0[{y}] == P1_marking_member_0[{z}])) {{
 long x;long y;long z;x=P1_marking_member_0[{x}];y=P1_marking_member_0[{y}];
 if (x<y) {{P1_is_marked-=3;z=x-y;P3_marking_member_0[P3_is_marked+0]=x;P3_marking_member_0[P3_is_marked+1]=y;P3_marking_member_0[P3_is_marked+2]=z;P3_is_marked+=3;}} }}'''
 else:
  x,y,z,w=v;minimum=max(v)+1;missing=next(i for i in range(5) if i not in v) if 4 in v else -1
  missing=-1 if missing==0 else missing
  compact='' if missing<0 else f'P2_marking_member_0[0]=P2_marking_member_0[{missing}];'
  expected=f'''if ((P2_is_marked >= {minimum}) && (P3_is_marked + 3 <= 6) && (P2_marking_member_0[{y}] == P2_marking_member_0[{z}]) && (P2_marking_member_0[{y}] == P2_marking_member_0[{w}])) {{
 long a;long b;long c;a=P2_marking_member_0[{x}];b=P2_marking_member_0[{y}];
 if (b>a) {{{compact}P2_is_marked-=4;c=a+b;P3_marking_member_0[P3_is_marked+0]=a;P3_marking_member_0[P3_is_marked+1]=b;P3_marking_member_0[P3_is_marked+2]=c;P3_is_marked+=3;}} }}'''
 assert normalize(block)==normalize(expected),(k,normalize(block),normalize(expected))
 records.append({'place':place,'indices':v,'minimum':3 if place==1 else minimum,'compactFrom':-1 if place==1 else missing})
assert [tuple(r['indices']) for r in records[:6]]==list(itertools.permutations(range(3)))
assert len(set(tuple(r['indices']) for r in records[6:]))==120
assert set(tuple(r['indices']) for r in records[6:])==set(itertools.permutations(range(5),4))
head='''(ns embench.nsichneu-full (:export [batch stage-cell test-nsichneu]))
;; Complete pinned Embench NSichneu: all 6 T1 and 120 T2 transitions.
;; Copyright 1998/1999 C-LAB Paderborn, 2014-2019 Embecosm/University of Bristol.
;; Contributors Friedhelm Stappert, James Pallister, Jeremy Bennett.
;; SPDX-License-Identifier: GPL-3.0-or-later.
;; State: 3 marking counts, P1[3], P2[5], P3[6].
(defn- put-output [s :vector-i64 x :i64 y :i64 z :i64] :vector-i64
  (let [n (vector-at s 2) s1 (vector-assoc! s (+ 11 n) x)
        s2 (vector-assoc! s1 (+ 12 n) y) s3 (vector-assoc! s2 (+ 13 n) z)]
    (vector-assoc! s3 2 (+ n 3))))
(defn- t1 [s :vector-i64 ix :i64 iy :i64 iz :i64] :vector-i64
  (if (and (>= (vector-at s 0) 3) (<= (+ (vector-at s 2) 3) 6)
           (= (vector-at s (+ 3 iy)) (vector-at s (+ 3 iz))))
    (let [x (vector-at s (+ 3 ix)) y (vector-at s (+ 3 iy))]
      (if (< x y)
        (let [n (vector-at s 0) next (vector-assoc! s 0 (- n 3))]
          (put-output next x y (- x y))) s)) s))
(defn- demark2 [s :vector-i64 x :i64 y :i64 missing :i64] :vector-i64
  (let [n (vector-at s 1)]
    (if (< missing 0)
      (put-output (vector-assoc! s 1 (- n 4)) x y (+ x y))
      (let [left (vector-at s (+ 6 missing)) s1 (vector-assoc! s 6 left)
            s2 (vector-assoc! s1 1 (- n 4))] (put-output s2 x y (+ x y))))))
(defn- t2 [s :vector-i64 ia :i64 ib :i64 ic :i64 id :i64 minimum :i64 missing :i64] :vector-i64
  (if (and (>= (vector-at s 1) minimum) (<= (+ (vector-at s 2) 3) 6)
           (= (vector-at s (+ 6 ib)) (vector-at s (+ 6 ic)))
           (= (vector-at s (+ 6 ib)) (vector-at s (+ 6 id))))
    (let [x (vector-at s (+ 6 ia)) y (vector-at s (+ 6 ib))]
      (if (> y x)
        (demark2 s x y missing) s)) s))
(defn- reset-counts [s :vector-i64] :vector-i64
  (let [s1 (vector-assoc! s 0 3) s2 (vector-assoc! s1 1 5)] (vector-assoc! s2 2 0)))
'''
# Keep every transition as a statically ordered call, not a reduced model or
# a constant answer. The oracle can also stop at any boundary for comparison.
parts=[head]
for k,r in enumerate(records):
 args=' '.join(map(str,r['indices']+([] if r['place']==1 else [r['minimum'],r['compactFrom']])))
 parts.append(f'(defn- step-{k+1} [s :vector-i64 limit :i64] :vector-i64\n  (let [next (t{r["place"]} s {args})]\n    (if (= limit {k+1}) next '+('next' if k==125 else f'(step-{k+2} next limit)')+')))\n')
# Forward references are resolved by the seed; no host linker is involved.
for k,r in enumerate(records):
 args=' '.join(map(str,r['indices']+([] if r['place']==1 else [r['minimum'],r['compactFrom']])))
 action=f'(t{r["place"]} s {args})'
 result=action if k==125 else f'(full-{k+2} {action})'
 parts.append(f'(defn- full-{k+1} [s :vector-i64] :vector-i64\n  {result})\n')
parts.append('(defn- run-full [s :vector-i64] :vector-i64 (full-1 (reset-counts s)))\n')
parts.append('''(defn- run-stages [s :vector-i64 limit :i64] :vector-i64
  (let [start (reset-counts s)] (if (= limit 0) start (step-1 start limit))))
(defn- repeats [s :vector-i64 remaining :i64] :vector-i64
  (if (= remaining 0) s (repeats (run-full s) (- remaining 1))))
(defn- verify [s :vector-i64] :i64
  (if (and (= (vector-at s 0) 3) (= (vector-at s 1) 5) (= (vector-at s 2) 0))
    (loop [i 3] (if (= i 17) 1 (if (= (vector-at s i) 0) (recur (+ i 1)) 0))) 0))
(defn batch [iterations :i64] :i64
  (if (<= iterations 0) 0 (verify (repeats (vector-alloc 17) iterations))))
(defn- seed-case [s :vector-i64 test :i64 i :i64] :vector-i64
  (if (= i 17) s
    (let [value (if (= test 0) 0
                  (if (= test 1) (if (= i 3) -2 (if (< i 6) 1 (if (= i 6) -3 2)))
                    (if (= test 2) (if (= i 4) -2 (if (< i 6) 1 (if (= i 7) -3 2)))
                      (if (= test 3) (if (< i 6) (- i 4) (- (rem i 3) 1))
                        (if (= test 4) -7
                          (if (= test 5) (+ 5 (rem (* i 7) 3))
                            (if (< i 6) 0
                              (if (>= i 11) 9
                                (if (= test 6) (if (= i 6) -3 (if (= i 9) 3 2))
                                  (if (= i 6) 7 (if (= i 7) -3 2)))))))))))
          next (vector-assoc! s i value)]
      (seed-case next test (+ i 1)))))
(defn stage-cell [encoded :i64] :i64
  (let [test (quot encoded 4096) code (rem encoded 4096)
        stage (quot code 17) cell (rem code 17)
        seeded (seed-case (vector-alloc 17) test 3)
        done (run-stages seeded stage)] (vector-at done cell)))
(defn test-nsichneu [] :i64 (batch 1))
''')
a.output.write_text(''.join(parts));a.output.with_suffix('.transitions.json').write_text(json.dumps(records,indent=2)+'\n')
