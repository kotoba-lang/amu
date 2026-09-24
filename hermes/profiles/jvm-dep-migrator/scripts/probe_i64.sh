#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu
run_case() {
  name="$1"; body="$2"
  printf '(ns p (:export [f]))\n%s\n' "$body" > /tmp/q_$name.kotoba
  out=$(bin/amu check /tmp/q_$name.kotoba --jvm-free 2>&1); code=$?
  if [ $code -eq 0 ]; then echo "$name: ADMITTED";
  else msg=$(echo "$out" | tr -d '\n' | sed 's/.*"message" *"\([^"]*\)".*/\1/');
       echo "$name: REJECT exit=$code :: $msg"; fi
}
run_case add '(defn f [x :i64 y :i64] :i64 (+ x y))'
run_case sub '(defn f [x :i64 y :i64] :i64 (- x y))'
run_case mul '(defn f [x :i64 y :i64] :i64 (* x y))'
run_case bit-and '(defn f [x :i64 y :i64] :i64 (bit-and x y))'
run_case bit-or '(defn f [x :i64 y :i64] :i64 (bit-or x y))'
run_case bit-xor '(defn f [x :i64 y :i64] :i64 (bit-xor x y))'
run_case bit-not '(defn f [x :i64] :i64 (bit-not x))'
run_case shl '(defn f [x :i64 n :i64] :i64 (bit-shift-left x n))'
run_case ashr '(defn f [x :i64 n :i64] :i64 (bit-shift-right x n))'
run_case lshr '(defn f [x :i64 n :i64] :i64 (unsigned-bit-shift-right x n))'
run_case lt '(defn f [x :i64 y :i64] :bool (< x y))'
run_case eq '(defn f [x :i64 y :i64] :bool (= x y))'
run_case letif '(defn f [x :i64] :i64 (let [v x] (if (< v 0) (- v) v)))'
run_case and '(defn f [x :i64] :bool (and (<= 0 x) (< x 64)))'
run_case throw '(defn f [x :i64] :i64 (if (<= 0 x) x (throw (ex-info "oob" {:n x}))))'
run_case when-not '(defn f [x :i64] :i64 (when-not (< x 0) x))'
run_case defint '(def min-i64 -9223372036854775808)'
run_case unchecked-add '(defn f [x :i64 y :i64] :i64 (unchecked-add x y))'
run_case defn-multi-arity '(defn f ([x :i64] :i64 x) ([x :i64 y :i64] :i64 (+ x y)))'
