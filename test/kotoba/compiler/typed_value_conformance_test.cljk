(ns kotoba.compiler.typed-value-conformance-test
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.kir :as ir]))

(def corpus
  (-> "kotoba/compiler/typed-value-conformance.edn" io/resource slurp edn/read-string))

(defn- web-result [compiled]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (.getBytes ^String (:source compiled) "UTF-8"))
        probe (str "import('data:text/javascript;base64," encoded
                   "').then(m=>{const value=m.instantiateKotoba({}).main();"
                   "if(typeof value!=='bigint')process.exit(2);console.log(value.toString())})")]
    (shell/sh "node" "--input-type=module" "-e" probe)))

(defn- wasm-result [compiled]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder) ^bytes (:bytes compiled))
        probe (str "import('./runtime/browser-host.mjs').then(async m=>{"
                   "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                   "const value=h.instance.exports.main();"
                   "if(typeof value!=='bigint')process.exit(2);console.log(value.toString())})")]
    (shell/sh "node" "--input-type=module" "-e" probe encoded)))

(deftest shared-positive-corpus-agrees-on-reference-and-web
  (is (= 1 (:kotoba.typed-value-conformance/version corpus)))
  (is (= :kotoba.typed-value/canonical-v1 (:abi corpus)))
  (doseq [{:keys [id source expect]} (:positive corpus)]
    (testing (name id)
      (let [compiled (compiler/compile-source source :js-kotoba-v1)
            wasm-compiled (compiler/compile-source source :wasm32-kotoba-v1)
            reference (ir/execute (:kir compiled) 'main [])
            web (web-result compiled)
            wasm (wasm-result wasm-compiled)]
        (is (= expect reference))
        (is (zero? (:exit web)) (:err web))
        (is (= (str expect "\n") (:out web)))
        (is (zero? (:exit wasm)) (:err wasm))
        (is (= (str expect "\n") (:out wasm)))))))

(deftest shared-negative-corpus-fails-closed
  (doseq [{:keys [id source phase]} (:negative corpus)]
    (testing (name id)
      (is (contains? #{nil :runtime} phase))
      (if phase
        (let [compiled (compiler/compile-source source :js-kotoba-v1)]
          (is (thrown? clojure.lang.ExceptionInfo
                       (ir/execute (:kir compiled) 'main [])))
          (is (not (zero? (:exit (web-result compiled)))))
          (is (not (zero? (:exit (wasm-result
                                  (compiler/compile-source source :wasm32-kotoba-v1)))))))
        (is (thrown? clojure.lang.ExceptionInfo
                     (compiler/check-source source)))))))

;; ---------------------------------------------------------------------------
;; The out-of-range half of `typed-list-nth`, which does NOT fit the shared
;; corpus's `:phase :runtime` shape.
;;
;; That shape is `compile-source` succeeds, then `ir/execute` throws. A
;; CONSTANT out-of-range index never reaches execute: `kir/lower` evaluates the
;; entry to fold it, so the trap arrives from `compile-source` itself. Measured
;; 2026-09-08, putting the case in the corpus anyway:
;;
;;   ERROR in (shared-negative-corpus-fails-closed) (kir.cljc:1173)
;;   clojure.lang.ExceptionInfo: list-index-out-of-bounds
;;   {:phase :ir, :trap :list-index-out-of-bounds, :index 3, :count 3}
;;
;; That is the right behaviour and the wrong test, so it is asserted here
;; instead. `:set-duplicate` and `:map-duplicate-key` DO fit the corpus shape;
;; the difference is that constant folding reaches an index bound and does not
;; reach those.
;;
;; Both ends, because a bounds check written as `index >= length` alone admits
;; every negative index and still passes a test that only tried the high end.

(defn- constant-list-nth [index]
  (str "(defn main [] (typed-list-nth [:list :i64] "
       "(typed-list-new [:list :i64] 4 5 6) " index "))"))

(deftest a-constant-out-of-range-list-index-is-refused-while-folding
  (doseq [index [3 -1 100]]
    (testing (str "index " index)
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"list-index-out-of-bounds"
                            (compiler/compile-source (constant-list-nth index)
                                                     :js-kotoba-v1))))
    (testing (str "and on the wasm route too, index " index)
      (is (thrown-with-msg? clojure.lang.ExceptionInfo #"list-index-out-of-bounds"
                            (compiler/compile-source (constant-list-nth index)
                                                     :wasm32-kotoba-v1)))))
  (testing "an in-range constant index folds to the item, so the refusal is about the RANGE"
    (is (= 6 (ir/execute (:kir (compiler/compile-source (constant-list-nth 2)
                                                        :js-kotoba-v1))
                         'main [])))))

;; And the runtime half, where the index is not a constant: `main` reads it
;; back through an argument the folder cannot see, so the trap lands in the
;; BACKENDS rather than in lowering. Both are probed with their own runner
;; because the corpus's probes only ever call a zero-argument `main`.

(def ^:private runtime-index-source
  (str "(ns t (:export [main at]))\n"
       "(defn at [index :i64] :i64 "
       "(typed-list-nth [:list :i64] (typed-list-new [:list :i64] 4 5 6) index))\n"
       "(defn main [] :i64 (at 1))"))

(defn- probe-at [compiled kind index]
  (let [encoded (.encodeToString (java.util.Base64/getEncoder)
                                 (if (= kind :web)
                                   (.getBytes ^String (:source compiled) "UTF-8")
                                   ^bytes (:bytes compiled)))
        body (if (= kind :web)
               (str "import('data:text/javascript;base64," encoded
                    "').then(m=>{const x=m.instantiateKotoba({});"
                    "console.log(x.at(" index "n).toString())})")
               (str "import('./runtime/browser-host.mjs').then(async m=>{"
                    "const h=await m.instantiateKotoba(Buffer.from(process.argv[1],'base64'));"
                    "console.log(h.instance.exports.at(" index "n).toString())})"))]
    (if (= kind :web)
      (shell/sh "node" "--input-type=module" "-e" body)
      (shell/sh "node" "--input-type=module" "-e" body encoded))))

(deftest a-runtime-list-index-reads-in-range-and-traps-out-of-range-on-both-backends
  (let [web (compiler/compile-source runtime-index-source :js-kotoba-v1)
        wasm (compiler/compile-source runtime-index-source :wasm32-kotoba-v1)]
    (doseq [[kind compiled] [[:web web] [:wasm wasm]]]
      (testing (str (name kind) " reads every in-range index")
        (doseq [[index expected] [[0 "4"] [1 "5"] [2 "6"]]]
          (let [result (probe-at compiled kind index)]
            (is (zero? (:exit result)) (:err result))
            (is (= (str expected "\n") (:out result))))))
      (testing (str (name kind) " traps at both ends of the range")
        (doseq [index [3 -1]]
          (let [result (probe-at compiled kind index)]
            (is (not (zero? (:exit result)))
                (str "index " index " must trap, got " (pr-str (:out result))))))))))
