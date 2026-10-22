#!/usr/bin/env python3
# seed/tests/r5/gen-feat.py -- writes seed/tests/r5/feat/ (the R5 feature programs) and appends nothing else.
# BOOTSTRAP-TOOL, owner R5D. Deterministic; rerun after editing a program here, then `oracle-r5.sh feat/`.
# Each project is feat/<case>/main.kotoba with its modules under feat/<case>/src (the --source-path).
import os, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, 'feat')
shutil.rmtree(F, ignore_errors=True)
def w(rel, text):
    p = os.path.join(F, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w').write(text.strip('\n') + '\n')
P = {}   # case -> (entry, srcpath or '-', fn, args, note)
def proj(case, main, mods, fn='main', args='-', note=''):
    w(case + '/main.kotoba', main)
    for path, text in mods.items(): w(case + '/src/' + path, text)
    P[case] = (case + '/main.kotoba', case + '/src' if mods else '-', fn, args, note)

# ---- positives: modules, names, exports -------------------------------------------------------------------------
proj('p01-require-as', '''
(ns p01.main (:require [p01.lib :as l]) (:export [main]))
(defn main [] :i64 (l/twice 21))''', {'p01/lib.kotoba': '''
(ns p01.lib (:export [twice]))
(defn twice [x :i64] :i64 (* 2 x))'''}, note='42')
proj('p02-refer', '''
(ns p02.main (:require [p02.lib :refer [twice]]) (:export [main]))
(defn main [] :i64 (+ (twice 5) 1))''', {'p02/lib.kotoba': '''
(ns p02.lib (:export [twice]))
(defn twice [x :i64] :i64 (* 2 x))'''}, note='11')
proj('p03-private-isolated', '''
(ns p03.main (:require [p03.lib :as l]) (:export [main]))
(defn- helper [x :i64] :i64 (+ x 1000))
(defn main [] :i64 (+ (helper 1) (l/run 2)))''', {'p03/lib.kotoba': '''
(ns p03.lib (:export [run]))
(defn- helper [x :i64] :i64 (* x 10))
(defn run [x :i64] :i64 (helper x))'''}, note='1001 + 20 = 1021: each module keeps its own private helper')
proj('p04-diamond', '''
(ns p04.main (:require [p04.b :as b] [p04.c :as c]) (:export [main]))
(defn main [] :i64 (+ (* 100 (b/plus 1)) (c/base)))''', {'p04/b.kotoba': '''
(ns p04.b (:require [p04.c :as c]) (:export [plus]))
(defn plus [x :i64] :i64 (+ x (c/base)))''', 'p04/c.kotoba': '''
(ns p04.c (:export [base]))
(defn base [] :i64 7)'''}, note='800 + 7 = 807: c is linked once')
proj('p05-implicit-export', '''
(ns p05.main (:require [p05.lib :as l]) (:export [main]))
(defn main [] :i64 (l/pub 4))''', {'p05/lib.kotoba': '''
(ns p05.lib)
(defn- sq [x :i64] :i64 (* x x))
(defn pub [x :i64] :i64 (+ (sq x) 1))'''}, note='17: no :export, the public defn is the interface (ADR 0353 floor 1)')
proj('p06-attr-map-export', '''
(ns p06.main {:kotoba/export [main]} (:require [p06.lib :as l]))
(defn main [] :i64 (l/k))''', {'p06/lib.kotoba': '''
(ns p06.lib "a docstring" {:kotoba/export [k]})
(defn k [] :i64 9)'''}, note='9: docstring + attr-map spelling of :export')
proj('p07-loop-in-lib', '''
(ns p07.main (:require [p07.lib :as l]) (:export [main]))
(defn main [] :i64 (l/sum-to 100))''', {'p07/lib.kotoba': '''
(ns p07.lib (:export [sum-to]))
(defn sum-to [n :i64] :i64 (loop [i 1 acc 0] (if (> i n) acc (recur (+ i 1) (+ acc i)))))'''}, note='5050: a loop helper inside an imported module')
proj('p08-same-export-name', '''
(ns p08.main (:require [p08.a :as a] [p08.b :as b]) (:export [main]))
(defn f [] :i64 1)
(defn main [] :i64 (+ (f) (* 10 (a/f)) (* 100 (b/f))))''', {'p08/a.kotoba': '''
(ns p08.a (:export [f]))
(defn f [] :i64 2)''', 'p08/b.kotoba': '''
(ns p08.b (:export [f]))
(defn f [] :i64 3)'''}, note='321: three functions named f in three namespaces')
proj('p09-string-across', '''
(ns p09.main (:require [p09.lib :as l]) (:export [main]))
(defn main [] :i64 (string-byte-length (l/greet "kotoba")))''', {'p09/lib.kotoba': '''
(ns p09.lib (:export [greet]))
(defn greet [s :string] :string (string-concat "hi " s))'''}, note='9: a :string parameter and result across modules')
proj('p10-abort-import', '''
(ns p10.main (:require [p10.lib :as l]) (:export [main]))
(defn- use-tail [x :i64] :i64 (l/need-pos x))
(defn- use-let [x :i64] :i64 (let [y (l/need-pos x)] (+ y 1)))
(defn main [] :i64
  (+ (try (use-tail 5) (catch e 100))
     (try (use-let -1) (catch e 1000))
     (try (l/need-pos -2) (catch e 10000))))''', {'p10/lib.kotoba': '''
(ns p10.lib (:export [need-pos]))
(defn need-pos [x :i64] :i64 (if (< x 0) (throw "negative") x))'''}, note='5 + 1000 + 10000 = 11005: ADR 0363, an imported aborting function propagates its abort')
proj('p11-multi-arity-export', '''
(ns p11.main (:require [p11.lib :as l]) (:export [main]))
(defn main [] :i64 (+ (l/f 1) (l/f 2 3)))''', {'p11/lib.kotoba': '''
(ns p11.lib (:export [f]))
(defn f ([x :i64] :i64 (* x 10)) ([x :i64 y :i64] :i64 (+ x y)))'''}, note='10 + 5 = 15: a multi-arity export (R4 + R5)')
proj('n16-imported-handler', '''
(ns n16.main (:require [n16.lib :as l]) (:export [main]))
(defn- tick [] (perform :state/put (+ 1 (perform :state/get))))
(defn main [] :i64 (handle (do (tick) (tick)) (with l/cell 40)))''', {'n16/lib.kotoba': '''
(ns n16.lib (:export [twice]))
(defhandler cell [:state :i64]
  (get [s] (resume s s))
  (put [s v] (resume v v)))
(defn twice [x :i64] :i64 (* 2 x))'''}, note='a handler of another module named qualified in `with`: stage-0 refuses (handle shape); handlers are not importable')
proj('p13-state-in-loop-call', '''
(ns p13.main (:export [main]))
(defhandler acc [:state :i64]
  (get [s] (resume s s))
  (put [s v] (resume v v)))
(defn- add! [x :i64] :i64 (perform :state/put (+ x (perform :state/get))))
(defn- run [n :i64] :i64 (loop [i 0] (if (= i n) (perform :state/get) (do (add! i) (recur (+ i 1))))))
(defn main [] :i64 (handle (run 5000) (with acc 0)))''', {}, note='12497500: 5000 non-tail stateful calls (pair-per-call pressure on stage-0 native)')
proj('p13b-state-in-loop-call-400', '''
(ns p13b.main (:export [main]))
(defhandler acc [:state :i64]
  (get [s] (resume s s))
  (put [s v] (resume v v)))
(defn- add! [x :i64] :i64 (perform :state/put (+ x (perform :state/get))))
(defn- run [n :i64] :i64 (loop [i 0] (if (= i n) (perform :state/get) (do (add! i) (recur (+ i 1))))))
(defn main [] :i64 (handle (run 400) (with acc 0)))''', {}, note='79800: p13 at 400 calls')
proj('p14-local-state-string', '''
(ns p14.main (:export [main]))
(defn main [] :i64
  (let [a (atom "ab")]
    (swap! a string-concat "cd")
    (reset! a (string-concat @a "e"))
    (string-byte-length @a)))''', {}, note='5: a string cell, swap! and reset!')
proj('p15-local-state-cond', '''
(ns p15.main (:export [main]))
(defn- f [n :i64] :i64
  (let [a (atom 1)]
    (cond (> n 10) (swap! a + 100)
          (> n 0) (swap! a * 7)
          :else (reset! a -1))
    (+ @a (* 1000 n))))
(defn main [] :i64 (+ (f 20) (f 3) (f -5)))''', {}, note='(20101) + (3007) + (-5001) = 18107: one write per cond arm')
proj('p16-reader-cond-ns', '''
(ns p16.main
  (:require #?(:kotoba [p16.k :as u] :default [p16.d :as u]))
  #?(:kotoba (:export [main])))
(defn main [] :i64 (+ (u/v) #?(:clj 1000 :kotoba 1 :default 2000)))''', {'p16/k.kotoba': '''
(ns p16.k (:export [v]))
(defn v [] :i64 10)''', 'p16/d.kotoba': '''
(ns p16.d (:export [v]))
(defn v [] :i64 20)'''}, note='11: #? inside the ns form selects the :kotoba require; d is never read')
proj('p17-ext-priority', '''
(ns p17.main (:require [p17.u :as u]) (:export [main]))
(defn main [] :i64 (u/v))''', {'p17/u.kotoba': '''
(ns p17.u (:export [v]))
(defn v [] :i64 1)''', 'p17/u.cljk': '''
(ns p17.u (:export [v]))
(defn v [] :i64 2)''', 'p17/u.cljc': '''
(ns p17.u (:export [v]))
(defn v [] :i64 3)'''}, note='1: .kotoba before .cljk before .cljc in one root (project_files extensions)')
proj('p18-cljk-only', '''
(ns p18.main (:require [p18.u :as u]) (:export [main]))
(defn main [] :i64 (u/v))''', {'p18/u.cljk': '''
(ns p18.u (:export [v]))
(defn v [] :i64 #?(:kotoba 2 :clj 20))''', 'p18/u.cljc': '''
(ns p18.u (:export [v]))
(defn v [] :i64 3)'''}, note='2: no .kotoba, the .cljk wins over .cljc; its :kotoba arm is read')
proj('p19-dash-underscore', '''
(ns p19.main (:require [p19.my-lib :as m]) (:export [main]))
(defn main [] :i64 (m/v))''', {'p19/my_lib.kotoba': '''
(ns p19.my-lib (:export [v]))
(defn v [] :i64 19)'''}, note='19: namespace my-lib lives in my_lib.kotoba')
proj('p21-reader-default-first', '''
(ns p21.main (:export [main]))
(defn main [] :i64 (+ #?(:default 5 :kotoba 1) #?(:cljs 30 :kotoba 10 :default 70)))''', {}, note='the first clause whose feature matches wins; is :default matched before a later :kotoba? (stage-0 decides)')
proj('p22-reader-no-match', '''
(ns p22.main (:export [main]))
#?(:clj (defn host-only [] :i64 99))
(defn main [] :i64 (+ 1 #?(:clj 100) #?@(:cljs [1000 1000]) 2))''', {}, note='3: a conditional with no matching clause reads as nothing (top level, argument, splice)')
proj('p23-handle-catch', '''
(ns p23.main (:export [main]))
(defn- chk [x :i64] :i64 (if (< x 0) (throw 7) x))
(defn main [] :i64 (+ (handle (chk -1) (catch e (* e 100))) (handle (chk 5) (catch e 1))))''', {}, note='705: (handle body (catch e ..)) eliminates :abort like try (state-ability.edn :install)')
proj('p24-deref-when', '''
(ns p24.main (:export [main]))
(defn- f [n :i64] :i64
  (let [a (atom 10)]
    (when (> n 0) (swap! a + n))
    (do (reset! a (* (deref a) 2)) (deref a))))
(defn main [] :i64 (+ (f 1) (* 1000 (f 0))))''', {}, note='22 + 20000 = 20022: deref long form, a write under when')
proj('p25-stateful-two-handlers', '''
(ns p25.main (:export [main]))
(defhandler plain [:state :i64]
  (get [s] (resume s s))
  (put [s v] (resume v v)))
(defhandler doubling [:state :i64]
  (get [s] (resume s s))
  (put [s v] (resume v (* 2 v))))
(defn- inc! [] :i64 (perform :state/put (+ 1 (perform :state/get))))
(defn main [] :i64
  (+ (handle (do (inc!) (inc!) (perform :state/get)) (with plain 1))
     (* 100 (handle (do (inc!) (inc!) (perform :state/get)) (with doubling 1)))))''', {}, note='3 + 100 * 10 = 1003: one function specialized under two handlers of the same S (1 -> 4 -> 10)')

# ---- negatives: the linker's refusals (texts from project.cljk / project_files.cljk) -----------------------------
proj('n01-cycle', '''
(ns n01.main (:require [n01.a :as a]) (:export [main]))
(defn main [] :i64 (a/f))''', {'n01/a.kotoba': '''
(ns n01.a (:require [n01.b :as b]) (:export [f]))
(defn f [] :i64 (b/g))''', 'n01/b.kotoba': '''
(ns n01.b (:require [n01.a :as a]) (:export [g]))
(defn g [] :i64 1)'''}, note='cyclic module dependency rejected')
proj('n02-missing', '''
(ns n02.main (:require [n02.nothere :as x]) (:export [main]))
(defn main [] :i64 (x/f))''', {'n02/other.kotoba': '''
(ns n02.other (:export [f]))
(defn f [] :i64 1)'''}, note='required module n02.nothere is missing from the explicit source paths')
proj('n03-dup-alias', '''
(ns n03.main (:require [n03.a :as x] [n03.b :as x]) (:export [main]))
(defn main [] :i64 (x/f))''', {'n03/a.kotoba': '(ns n03.a (:export [f]))\n(defn f [] :i64 1)',
                                'n03/b.kotoba': '(ns n03.b (:export [f]))\n(defn f [] :i64 2)'}, note='duplicate import alias')
proj('n04-private-call', '''
(ns n04.main (:require [n04.lib :as l]) (:export [main]))
(defn main [] :i64 (l/hidden 1))''', {'n04/lib.kotoba': '''
(ns n04.lib (:export [shown]))
(defn- hidden [x :i64] :i64 x)
(defn shown [x :i64] :i64 (hidden x))'''}, note='a defn- is not an import')
proj('n05-unknown-export', '''
(ns n05.main (:require [n05.lib :as l]) (:export [main]))
(defn main [] :i64 (l/nothere 1))''', {'n05/lib.kotoba': '''
(ns n05.lib (:export [f]))
(defn f [x :i64] :i64 x)'''}, note='qualified call is not an admitted exported import')
proj('n06-two-ns', '''
(ns n06.main (:require [n06.lib :as l]) (:export [main]))
(defn main [] :i64 (l/f))''', {'n06/lib.kotoba': '''
(ns n06.lib (:export [f]))
(ns n06.lib2)
(defn f [] :i64 1)'''}, note='project module requires exactly one namespace')
proj('n07-use-clause', '''
(ns n07.main (:use [n07.lib]) (:export [main]))
(defn main [] :i64 1)''', {'n07/lib.kotoba': '(ns n07.lib (:export [f]))\n(defn f [] :i64 1)'}, note='namespace clause :use is not admitted')
proj('n08-ns-mismatch', '''
(ns n08.main (:require [n08.lib :as l]) (:export [main]))
(defn main [] :i64 (l/f))''', {'n08/lib.kotoba': '''
(ns n08.other (:export [f]))
(defn f [] :i64 1)'''}, note='the file found for n08.lib declares another namespace')
proj('n09-abort-import-unhandled', '''
(ns n09.main (:require [n09.lib :as l]) (:export [main]))
(defn main [] :i64 (l/need-pos -1))''', {'n09/lib.kotoba': '''
(ns n09.lib (:export [need-pos]))
(defn need-pos [x :i64] :i64 (if (< x 0) (throw "negative") x))'''}, note='unhandled abort at export boundary (the imported abort reaches main)')
proj('n10-stateful-lib-export', '''
(ns n10.main (:require [n10.lib :as l]) (:export [main]))
(defhandler cell [:state :i64]
  (get [s] (resume s s))
  (put [s v] (resume v v)))
(defn main [] :i64 (handle (l/bump) (with cell 1)))''', {'n10/lib.kotoba': '''
(ns n10.lib (:export [bump]))
(defn bump [] :i64 (perform :state/put (+ 1 (perform :state/get))))'''}, note='a stateful export is refused at its own module boundary')
proj('n11-exports-nothing', '''
(ns n11.main (:require [n11.lib :as l]) (:export [main]))
(defn main [] :i64 1)''', {'n11/lib.kotoba': '''
(ns n11.lib)
(defn- f [] :i64 1)'''}, note='project module n11.lib exports nothing')
proj('n12-capability-undeclared', '''
(ns n12.main (:capabilities #{:io/write}) (:export [main]))
(defn main [] :i64 (do (perform :clock/now 0) 1))''', {}, note='a capability outside the declared :capabilities set')
proj('n13-capability-not-granted', '''
(ns n13.main (:capabilities #{:clock/now}) (:export [main]))
(defn main [] :i64 (perform :clock/now 0))''', {}, note='declared, but the compile policy {:allow #{}} does not grant it')
proj('n14-qualified-unknown-alias', '''
(ns n14.main (:export [main]))
(defn main [] :i64 (zz/f 1))''', {}, note='a qualified call with no :require')
# depth limit: a chain of 66 modules (root depth 1, max-project-depth 64)
chain = {}
for i in range(1, 66):
    nxt = i + 1
    if i < 65:
        chain['n15/m%d.kotoba' % i] = '(ns n15.m%d (:require [n15.m%d :as n]) (:export [f]))\n(defn f [] :i64 (+ 1 (n/f)))' % (i, nxt)
    else:
        chain['n15/m%d.kotoba' % i] = '(ns n15.m%d (:export [f]))\n(defn f [] :i64 1)' % i
proj('n15-depth-66', '''
(ns n15.main (:require [n15.m1 :as m]) (:export [main]))
(defn main [] :i64 (m/f))''', chain, note='project dependency depth exceeds limit (66 > 64)')
chain = {}
for i in range(1, 64):
    if i < 63:
        chain['p20/m%d.kotoba' % i] = '(ns p20.m%d (:require [p20.m%d :as n]) (:export [f]))\n(defn f [] :i64 (+ 1 (n/f)))' % (i, i + 1)
    else:
        chain['p20/m%d.kotoba' % i] = '(ns p20.m%d (:export [f]))\n(defn f [] :i64 1)' % i
proj('p20-depth-64', '''
(ns p20.main (:require [p20.m1 :as m]) (:export [main]))
(defn main [] :i64 (m/f))''', chain, note='63: a chain at depth 64, the bound itself')

with open(os.path.join(HERE, 'feat-cases.tsv'), 'w') as o:
    o.write('# generated by gen-feat.py: label entry srcpath fn args note (appended to the oracle run by oracle-r5.sh)\n')
    for case in sorted(P):
        e, sp, fn, args, note = P[case]
        o.write('\t'.join(['feat/' + case, 'feat/' + e, ('feat/' + sp) if sp != '-' else '-', fn, args, note]) + '\n')
print(len(P), 'feature cases')
