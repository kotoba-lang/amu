#!/bin/bash
# probe matrix: measure current amu --jvm-free admitted subset
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu
run_case() {
  name="$1"; body="$2"
  printf '(ns p (:export [f]))\n%s\n' "$body" > /tmp/p_$name.kotoba
  out=$(bin/amu check /tmp/p_$name.kotoba --jvm-free 2>&1); code=$?
  if [ $code -eq 0 ]; then echo "$name: ADMITTED";
  else msg=$(echo "$out" | tr -d '\n' | sed 's/.*"message" *"\([^"]*\)".*/\1/');
       echo "$name: REJECT exit=$code :: $msg"; fi
}
run_case defmap '(def m {:a 1 :b 2})'
run_case strlit '(defn f [] :string "hi")'
run_case string-concat '(defn f [a :string b :string] :string (string-concat a b))'
run_case string-eq '(defn f [a :string b :string] :bool (string=? a b))'
run_case count '(defn f [m] :i64 (count m))'
run_case keys '(defn f [m] (keys m))'
run_case reduce-kv '(defn f [m] :i64 (reduce-kv (fn [acc k v] (+ acc v)) 0 m))'
run_case mapv '(defn f [xs] (mapv inc xs))'
run_case filterv '(defn f [xs] (filterv even? xs))'
run_case contains '(defn f [m] :bool (contains? m :a))'
run_case kwproj '(defn f [m] :i64 (:a m))'
run_case min '(defn f [a :i64 b :i64] :i64 (min a b))'
run_case hashfn '(defn f [xs] (mapv #(+ % 1) xs))'
run_case parse-long '(defn f [s :string] (parse-long s))'
run_case reduce '(defn f [xs] :i64 (reduce + 0 xs))'
run_case seq '(defn f [m] (seq m))'
run_case get '(defn f [m] (get m :a))'
run_case assoc '(defn f [m] (assoc m :c 3))'
run_case into-map '(defn f [m] (into {} m))'
