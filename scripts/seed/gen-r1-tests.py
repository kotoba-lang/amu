#!/usr/bin/env python3
# scripts/seed/gen-r1-tests.py -- writes seed/tests/r1/{feat,conf,neg}/*.kotoba (owner GATES). BOOTSTRAP-TOOL.
# The programs are SOURCE of truth here (edit this file, rerun, then scripts/seed/oracle.sh r1 to refresh the stage-0
# oracle). feat/ = one R1 feature per program, conf/ = typed adaptations of lang/conformance control/ records/ values/
# programs, neg/ = programs R1 must still REFUSE. Every program: (ns seed.r1 (:export [test])) and (defn test [] :i64 ..).
import os
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'seed', 'tests', 'r1')
HDR = '(ns seed.r1 (:export [test]))\n'
REC = '(defrecord Pt [x :i64 y :i64])\n'
RECV = '[:record :seed.r1/Pt [[:x :i64] [:y :i64]]]'
def T(body): return '(defn test [] :i64\n  ' + body + ')\n'

feat = {
 '01-do-value': ('R1 do: value of the last form', T('(do 1 2 3)')),
 '02-do-nested': ('do nested in let and arithmetic', T('(let [x (do 4 5)] (+ x (do 1 (+ 2 3))))')),
 '03-do-calls': ('do with calls whose values are dropped', '(defn- f [a :i64] :i64 (+ a 1))\n' + T('(do (f 1) (f 2) (f 3))')),
 '04-do-trap-order': ('do evaluates the dropped forms: the quot trap must fire', T('(do (quot 1 0) 5)')),
 '05-when-true': ('when with a true test', T('(when (< 1 2) 5)')),
 '06-when-false': ('when with a false test: stage-0 value is 0', T('(+ 1 (when (> 1 2) 5))')),
 '07-when-multi': ('when with several body forms', T('(when (< 1 2) 10 20 30)')),
 '08-when-skip-trap': ('when false must not evaluate its body', T('(when (> 1 2) (quot 1 0))')),
 '09-cond-first': ('cond: first clause', T('(cond (< 1 2) 11 (< 2 3) 22 :else 33)')),
 '10-cond-middle': ('cond: middle clause', T('(cond (> 1 2) 11 (< 2 3) 22 :else 33)')),
 '11-cond-else': ('cond: :else', T('(cond (> 1 2) 11 (> 2 3) 22 :else 33)')),
 '12-cond-nested': ('cond inside cond', T('(cond (< 1 2) (cond (> 1 2) 1 :else 2) :else 3)')),
 '13-cond-ten': ('cond with ten clauses', T('(let [n 7] (cond (= n 0) 0 (= n 1) 1 (= n 2) 2 (= n 3) 3 (= n 4) 4 (= n 5) 5 (= n 6) 6 (= n 7) 70 (= n 8) 8 :else 9))')),
 '14-cond-loop': ('cond in a loop (collatz steps of 27)', '(defn test [] :i64\n  (loop [n 27 steps 0]\n    (cond (= n 1) steps (= (bit-and n 1) 0) (recur (quot n 2) (+ steps 1)) :else (recur (+ (* 3 n) 1) (+ steps 1)))))\n'),
 '15-case-i64-hit': ('case on i64: hit', T('(case 3 1 10 3 30 0)')),
 '16-case-i64-default': ('case on i64: default', T('(case 9 1 10 3 30 0)')),
 '17-case-negative': ('case with negative keys', T('(case -2 -1 10 -2 20 0)')),
 '18-case-kw-hit': ('case on keywords: hit', T('(case :b :a 1 :b 2 0)')),
 '19-case-kw-default': ('case on keywords: default', T('(case :z :a 1 :b 2 0)')),
 '20-case-grouped': ('case with grouped keys', T('(+ (case 2 (1 2 3) 100 0) (case 7 (1 2 3) 100 5))')),
 '21-case-loop': ('case in a loop', T('(loop [i 0 acc 0] (if (< i 6) (recur (+ i 1) (+ acc (case i 0 1 1 10 2 100 5))) acc))')),
 '22-case-expr': ('case selector is an expression', T('(case (+ 1 2) 1 10 3 30 0)')),
 '23-case-min': ('case with the minimum i64 key', T('(case -9223372036854775808 0 1 -9223372036854775808 2 3)')),
 '24-thread-first': ('->', T('(-> 5 (+ 1) (* 2) (- 3))')),
 '25-thread-last': ('->>', T('(->> 5 (* 2) (- 20))')),
 '26-thread-in-arith': ('-> and ->> as operands', T('(+ (-> 2 (* 3)) (->> 2 (- 10)) 1)')),
 '27-thread-bare': ('-> with a bare symbol step', '(defn- inc1 [a :i64] :i64 (+ a 1))\n' + T('(-> 5 inc1 inc1)')),
 '28-thread-nested': ('-> inside ->>', T('(->> 3 (+ (-> 1 (+ 1))) (* 2))')),
 '29-dotimes-value': ('dotimes value is 0 (stage-0)', T('(+ 7 (dotimes [i 4] (+ i 1)))')),
 '30-dotimes-zero': ('dotimes 0 times: body never runs', T('(+ 7 (dotimes [i 0] (quot 1 0)))')),
 '31-dotimes-trap-last': ('dotimes runs every iteration: traps on i = 2', T('(dotimes [i 3] (quot 1 (- 2 i)))')),
 '32-dotimes-calls': ('dotimes with calls', '(defn- f [a :i64] :i64 (* a a))\n' + T('(+ 3 (dotimes [i 5] (f i)))')),
 '33-dotimes-nested': ('nested dotimes, trap in the inner body at i=1 j=1', T('(dotimes [i 3] (dotimes [j 3] (quot 1 (- (* i j) 1))))')),
 '34-kw-eq': ('keywords are interned: equal spellings compare equal', T('(let [k :alpha j :alpha] (if (= k j) 1 0))')),
 '35-kw-ne': ('keywords are interned: different spellings differ', T('(let [k :alpha j :beta] (if (= k j) 1 0))')),
 '36-rec-basic': ('flat record: construct and read', REC + T('(let [p (->Pt 3 4)] (+ (get p :x) (get p :y)))')),
 '37-rec-bool': ('record with a bool field', '(defrecord Flag [n :i64 on :bool])\n' + T('(let [p (->Flag 3 true)] (if (get p :on) (get p :n) 0))')),
 '38-rec-string': ('record with a string field', '(defrecord Named [n :i64 s :string])\n' + T('(let [p (->Named 4 "hello")] (+ (get p :n) (string-length (get p :s))))')),
 '39-rec-param': ('record as a parameter', REC + '(defn- sum [p ' + RECV + '] :i64 (+ (get p :x) (get p :y)))\n' + T('(sum (->Pt 3 4))')),
 '40-rec-two-types': ('two record types', '(defrecord A [x :i64])\n(defrecord B [x :i64 s :string])\n' + T('(let [a (->A 3) b (->B 4 "hi")] (+ (get a :x) (get b :x) (string-length (get b :s))))')),
 '41-rec-loop': ('record read inside a loop', REC + T('(let [p (->Pt 3 4)] (loop [i 0 acc 0] (if (< i 3) (recur (+ i 1) (+ acc (get p :y))) acc)))')),
 '42-rec-assoc': ('assoc on a record copies', REC + T('(let [p (->Pt 3 4) q (assoc p :x 10)] (+ (get q :x) (get p :x)))')),
 '43-rec-map-ctor': ('map->Rec constructor', REC + T('(let [p (map->Pt {:x 3 :y 4})] (get p :y))')),
 '44-rec-six-fields': ('record with six fields', '(defrecord Six [a :i64 b :i64 c :i64 d :i64 e :i64 f :i64])\n' + T('(let [p (->Six 1 2 3 4 5 6)] (+ (get p :a) (* 10 (get p :f)) (* 100 (get p :c))))')),
 '45-rec-result': ('record as a function result', REC + '(defn- mk [a :i64] ' + RECV + ' (->Pt a 1))\n' + T('(get (mk 5) :x)')),
}
# doseq: stage-0 REFUSES doseq in native aarch64 code (probe, 2026-10-02): oracle = refused; expectations in r1.spec
doseq = {
 '46-doseq-trap': ('doseq over a vector param: runs every element (quot by 0 on the second)', '(defn- s [v :vector-i64] :i64 (doseq [x v] (quot 1 x)))\n' + T('(s (vector-conj (vector-conj (vector-alloc 0) 1) 0))')),
 '47-doseq-no-trap': ('doseq over a vector: completes, value of the call dropped', '(defn- s [v :vector-i64] :i64 (do (doseq [x v] (quot 1 x)) 7))\n' + T('(s (vector-conj (vector-conj (vector-alloc 0) 1) 2))')),
 '48-doseq-empty': ('doseq over an empty vector never runs the body', '(defn- s [v :vector-i64] :i64 (do (doseq [x v] (quot 1 0)) 9))\n' + T('(s (vector-alloc 0))')),
 '49-doseq-literal': ('doseq over a vector literal', T('(do (doseq [x [1 2 0]] (quot 1 x)) 5)')),
}
spec = {'46-doseq-trap': 'trap', '47-doseq-no-trap': '7', '48-doseq-empty': '9', '49-doseq-literal': 'trap'}

conf = {
 'c01-case-threading': ('control/case_threading.kotoba (51): if-let/when-let (not R1) replaced by their values 4 and 5',
   T('(+ (-> 5 (+ 1) (* 2) (- 3)) (->> 5 (* 2) (- 20)) (case :b :a 1 (:b :c) 23 0) 4 5)')),
 'c02-condp': ('control/condp.kotoba (50): condp (not R1) written as cond',
   T('(+ (cond (= 2 1) 10 (= 2 2) 20 :else 0) (cond (= 3 1) 10 (= 3 2) 20 :else 30))')),
 'c03-dotimes': ('control/dotimes.kotoba (7)', T('(+ 7 (dotimes [i 4] (+ i 1)))')),
 'c04-match-desugar': ('control/match_desugar.kotoba (21): defdesugar/match (not R1) written as a function and cond',
   '(defn- clamp [x :i64 lo :i64 hi :i64] :i64 (cond (< x lo) lo (> x hi) hi :else x))\n' +
   T('(+ (loop [n 5 acc 0] (if (= n 0) acc (recur (- n 1) (+ acc n)))) (clamp 9 0 6))')),
 'c05-simple-sugar': ('control/simple_sugar.kotoba (26): if-not/when-not/cond->>/as-> (not R1) written with cond/when/->>/let',
   '(defn- subtract [a :i64 b :i64] :i64 (- a b))\n' +
   T('(+ (cond (= 0 0) 4 :else (quot 1 0)) (when (= 0 0) (+ 2 3)) (->> 3 (subtract 10)) (let [x 2] (let [x (+ x 3)] (* x 2))))')),
 'c06-records': ('records/basic.kotoba (16): protocols (not R1) replaced by plain functions over flat records',
   '(defrecord LocalBox [x :i64])\n(defrecord ExtendedBox [x :i64])\n' +
   '(defn- value-l [b [:record :seed.r1/LocalBox [[:x :i64]]]] :i64 (get b :x))\n' +
   '(defn- value-e [b [:record :seed.r1/ExtendedBox [[:x :i64]]]] :i64 (get b :x))\n' +
   T('(+ (value-l (->LocalBox 7)) (value-e (map->ExtendedBox {:x 9})))')),
 'c07-values': ('values/string_symbol.kotoba (10): destructuring (not R1) replaced by lets; the non-ASCII string is an R3 feature, ASCII here',
   T('(let [name 3 age 4] (+ name age (string-length "cat")))')),
 'c08-doseq': ('control/doseq.kotoba (7): the nine doseq forms reduced to the R1 vector form; the 7 base is kept',
   '(defn- s [v :vector-i64] :i64 (do (doseq [x v] (quot 1 0)) 0))\n' + T('(+ 7 (s (vector-alloc 0)))')),
}
spec['c08-doseq'] = '7'

neg = {   # name: (why, body)
 'n01-fn': ('fn is R4', T('((fn [x :i64] (+ x 1)) 2)')),
 'n02-condp': ('condp is not in R1', T('(condp = 2 1 10 2 20 0)')),
 'n03-if-let': ('if-let is not in R1', T('(if-let [x 4] x 0)')),
 'n04-when-let': ('when-let is not in R1', T('(when-let [x 4] x)')),
 'n05-if-not': ('if-not is not in R1', T('(if-not (< 1 2) 4 5)')),
 'n06-when-not': ('when-not is not in R1', T('(when-not (< 1 2) 4)')),
 'n07-assert': ('assert is R3 (abort)', T('(assert (= 3 3))')),
 'n08-match': ('match is not in R1', T('(match 3 3 1 :else 0)')),
 'n09-map-literal': ('map literal outside a record constructor', T('(get {:a 1} :a)')),
 'n10-set-literal': ('set literal is R3', T('(count #{1 2})')),
 'n11-cond-no-else': ('cond must end with :else', T('(cond (< 1 2) 1 (< 2 3) 2)')),
 'n12-cond-else-middle': (':else must be last', T('(cond :else 1 (< 1 2) 2)')),
 'n13-cond-i64-test': ('cond test must be bool', T('(cond 1 5 :else 6)')),
 'n14-when-i64-test': ('when test must be bool', T('(when 1 5)')),
 'n15-do-empty': ('(do) has no value', T('(do)')),
 'n16-dotimes-bool': ('dotimes count must be i64', T('(dotimes [i (< 1 2)] 1)')),
 'n17-dotimes-no-binding': ('dotimes needs [i n]', T('(dotimes [] 1)')),
 'n18-dotimes-two-bindings': ('dotimes takes exactly one binding', T('(dotimes [i 2 j 3] 1)')),
 'n19-thread-number': ('-> step must be a call or a symbol', T('(-> 5 3)')),
 'n20-case-dup-keys': ('duplicate case keys', T('(case 1 1 10 1 20 0)')),
 'n21-case-mixed-keys': ('i64 and keyword keys in one case', T('(case 1 1 10 :a 20 0)')),
 'n22-case-string-keys': ('string case keys', T('(case 1 "a" 10 0)')),
 'n23-case-kw-on-i64': ('keyword keys on an i64 selector', T('(case 1 :a 10 :b 20 0)')),
 'n24-case-no-default': ('case without a default', T('(case 1 1 10 2 20)')),
 'n25-kw-result': ('a keyword is not an i64 result', '(defn test [] :i64 :a)\n'),
 'n26-kw-arith': ('keyword as an arithmetic operand', T('(+ :a 1)')),
 'n27-rec-unknown-field': ('get of an undeclared field', REC + T('(get (->Pt 1 2) :z)')),
 'n28-rec-field-type': ('constructor argument of the wrong type', REC + T('(get (->Pt true 2) :x)')),
 'n29-rec-arity': ('constructor with too few arguments', REC + T('(get (->Pt 1) :x)')),
 'n30-rec-dup-field': ('duplicate field in a record', '(defrecord Bad [x :i64 x :i64])\n' + T('1')),
 'n31-rec-dup-name': ('two records with one name', REC + REC + T('1')),
 'n32-rec-bad-field-type': ('record field of an unsupported type', '(defrecord Bad [x :f64])\n' + T('1')),
 'n33-rec-get-nonlit': ('get with a computed key', REC + T('(let [k 1] (get (->Pt 1 2) k))')),
 'n34-rec-get-on-i64': ('get on a non-record', T('(get 5 :x)')),
 'n35-rec-protocol': ('defprotocol is R5', '(defprotocol P (v [this]))\n' + T('1')),
 'n36-dotimes-binder-use-outside': ('the dotimes binder is not visible after the form', T('(do (dotimes [i 2] 1) i)')),
 'n37-multimethod': ('defmulti is not in R1', '(defmulti m identity)\n' + T('1')),
 'n38-doseq-map': ('doseq over a map literal', T('(doseq [x {:a 1}] x)')),
 'n39-doseq-i64': ('doseq over an i64', T('(doseq [x 5] x)')),
 'n40-try': ('try/throw is R3', T('(try 1 (catch :e e 2))')),
}

def w(sub, name, why, body):
    d = os.path.join(R, sub); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, name + '.kotoba'), 'w').write(';; ' + why + '\n' + HDR + body)
for k, (why, body) in feat.items(): w('feat', k, 'R1 feat: ' + why, body)
for k, (why, body) in doseq.items(): w('feat', k, 'R1 feat (stage-0 refuses doseq; expectation in r1.spec): ' + why, body)
for k, (why, body) in conf.items(): w('conf', k, 'R1 conf from lang/conformance ' + why, body)
for k, (why, body) in neg.items(): w('neg', k, 'R1 negative: ' + why, body)
open(os.path.join(R, 'r1.spec'), 'w').write(
  ';; hand-derived expectations for programs stage-0 REFUSES (see r1.oracle); not stage-0 measurements.\n' +
  ''.join('%s %s\n' % (('conf/' if k.startswith('c') else 'feat/') + k, v) for k, v in sorted(spec.items())))
print(len(feat) + len(doseq), 'feat,', len(conf), 'conf,', len(neg), 'neg')
