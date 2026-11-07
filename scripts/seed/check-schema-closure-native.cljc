;; Check native KIR record-schema closure; this script stages bytes and compares CIDs.
;;
;; The frozen CIDs were measured from the pinned reference on 2026-11-02 and independently reconstructed with the
;; native 04 encoder. They are data, not a runtime fallback or cache admission. Source schema closure remains
;; separate. Ported from check-schema-closure-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-schema-closure-native.cljc -- --compiler C --output DIR
(ns check-schema-closure-native
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as mac])
  (:import json operator pathlib platform subprocess sys))

(def extra ["seed/04-definition-cid.kotoba" "seed/05-definition-graph.kotoba"
            "seed/05-checked-definition.kotoba" "seed/06-definition-groups.kotoba"])

(def entry
  (str "\n(defn- seed-main [] :i64\n"
       " (if (not= (io-argc) 1) 2\n"
       "  (let [K (io-fs2-text 65 (io-arg 0) \"\") status (dcs-run-resource K 1)]\n"
       "   (if (= status 0) 0 (let [e (io-err (string-concat \"SCHEMA:\" (string-concat (mem-u2dec status) \"\\n\")))] 1)))))\n"))

(def golden
  {"simple" "bafyreiagssxmxbxfy7i3zq4m6ayucfkyjylomcruexauvgvw6dtjqtfeeu"
   "wide" "bafyreidaytqoaqbuviy36bdr4cqhxp44t7fyi4p7imewkf43pyz2patx34"
   "transitive" "bafyreiadno3ibxqnk6ifmempx2gx2f6agdxrtw33aesdteniywuddrhpou"
   "transitive-edit" "bafyreihfv6o5vy2qm5ovfbog7g5fo5o7k7urmvhuupo7jazxcsgiyz5gdy"
   "cycle" "bafyreic4u2yz7lplpnqy6e6kcxjo2mgbkvp3zfla7552pgtcd45cxy7bii"})

(def scc
  {"simple" ["bafyreihtokury6llizbq7wmkyqcfxbercbjmyphgbhzuqws354lgcnhenq"
             "bafyreie7ddqj6iifuc4cu4vhjasuba7cjxamxiboevo3urztubufhhwosy"
             "bafyreibtoqy7rc5f5axhbriw5tlmixzxeud6z76wmuh7libnydnbyxb6se"]
   "wide" ["bafyreibsizl5lawwbx6q4cke72mcgrumbdkua6sxt37k2d7k7hno5j2moi"
           "bafyreiepwb6pqth2fa2qksm3soohtlhdk62omqs3awruva5nmgya6wen3i"
           "bafyreiesxu6f72as4v3bgyywftdz3nrl3b6v7rny4kji4mzw5ozls32esi"]})

(def schemas
  {"simple" "{:s/r [:record :s/r [[:a :i64]]]}"
   "wide" "{:s/r [:record :s/r [[:a :i64] [:b :i64]]]}"
   "unrelated" "{:s/r [:record :s/r [[:a :i64]]] :s/u [:record :s/u [[:z :string]]]}"
   "transitive" "{:s/r [:record :s/r [[:n [:ref :s/n]]]] :s/n [:record :s/n [[:v :i64]]]}"
   "transitive-edit" "{:s/r [:record :s/r [[:n [:ref :s/n]]]] :s/n [:record :s/n [[:v :string]]]}"
   "reordered" "{:s/n [:record :s/n [[:v :i64]]] :s/r [:record :s/r [[:n [:ref :s/n]]]]}"
   "cycle" "{:s/r [:record :s/r [[:next [:ref :s/n]]]] :s/n [:record :s/n [[:prev [:ref :s/r]]]]}"
   "missing" "{}"
   "missing-transitive" "{:s/r [:record :s/r [[:n [:ref :s/n]]]]}"
   "duplicate" "{:s/r [:record :s/r [[:a :i64]]] :s/r [:record :s/r [[:a :string]]]}"
   "bad-name" "{:s/r [:record :s/wrong [[:a :i64]]]}"
   "bad-type" "{:s/r [:record :s/r [[:a :not-a-type]]]}"
   "bad-unused" "{:s/r [:record :s/r [[:a :i64]]] :s/bad [:record :s/bad [[:z :not-a-type]]]}"
   "duplicate-field" "{:s/r [:record :s/r [[:a :i64] [:a :string]]]}"
   "bad-legacy" "{:Foo [:record {:x :i64}]}"})

(defn module [schema functions]
  (str "{:format :kotoba.kir/v4 :entry nil :exports [] :effects #{} :schemas " schema
       " :functions [" (str/join " " functions) "]}\n"))

(defn kfn ([name body] (kfn name body "[x]" "[[:ref :s/r]]"))
  ([name body param types]
   (str "{:name " name " :params " param " :param-types " types " :result :i64 :effects #{} :body " body "}")))

(defn main [compiler out]
  (let [darwin (mac/available?)
        machine (platform/machine)
        _ (u/chk (or darwin (and (= "Linux" (platform/system)) (contains? #{"aarch64" "x86_64"} machine))))
        target (if (= machine "aarch64") "aarch64-linux" "x86_64-linux")
        root u/root
        product (u/read-json (.joinpath root "native-product.json"))
        [root-image packager] (if darwin (mac/root-images) [nil nil])
        _ (if darwin
            (u/chk (u/deq (u/pin compiler) (u/pin root-image)))
            (u/chk (u/deq (u/pin compiler) (u/geti product (if (= machine "aarch64") "rootImage" "image")))))
        _ (.mkdir out ** :parents false :mode 0700 :exist_ok false)
        listed (vec (filter #(and (seq %) (not (.startswith % "#"))) (.splitlines (.read_text (.joinpath root "seed/CORE-STATIC-MANIFEST")))))
        _ (u/chk (= "seed/99-entry.kotoba" (last listed)))
        paths (vec (concat (butlast listed) extra))
        text (str (str/join "\n" (for [p paths] (.read_text (.joinpath root p)))) entry)
        env (python/dict {"PATH" "/nonexistent" "KEXE_STACK_BYTES" "8388608" "KEXE_FUEL" "10000000000"
                          "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str out)})
        report (u/pydict "schema" "amu.native-kir-schema-closure.v1" "host" (python/list [(platform/system) machine])
                         "compiler" (u/pin compiler)
                         "observer" (u/pin (.joinpath root "scripts/seed/check-schema-closure-native.cljc"))
                         "modules" (u/pydict-from (for [p paths] [p (u/pin (.joinpath root p))]))
                         "inputs" (u/pydict) "calls" (python/list)
                         "nativeVerdictAuthority" false "sourceClosureQualified" false
                         "persistentBuildQualified" false "resourceProofQualified" false)
        save (fn [] (.write_text (.joinpath out "observations.json") (u/json-dump report)))
        run (fn [name image args code]
              (let [result (if darwin
                             (mac/run image out args)
                             (subprocess/run (python/list (map str (cons image args))) ** :cwd out :env env :capture_output true :timeout 300))]
                (doseq [stream ["stdout" "stderr"]]
                  (.write_bytes (.joinpath out (str name "." stream)) (python/getattr result stream)))
                (.append (u/geti report "calls")
                         (u/pydict "name" name "exit" (.-returncode result)
                                   "stdout" (u/pin (.joinpath out (str name ".stdout")))
                                   "stderr" (u/pin (.joinpath out (str name ".stderr")))))
                (save)
                (u/chk (= code (.-returncode result)) (str name " " (.-returncode result)))
                result))
        build (fn [name source]
                (let [file (.joinpath out (str name ".kotoba"))]
                  (.write_text file source)
                  (if darwin
                    (first (mac/build compiler packager out (.-name file) name))
                    (let [image (.joinpath out (str name ".elf"))
                          result (subprocess/run (python/list (map str [compiler "compile" file "--target" target "--output" image "--format" "static"]))
                                                 ** :cwd out :env env :capture_output true :timeout 300)]
                      (u/chk (zero? (.-returncode result)) name)
                      (.chmod image 0700)
                      image))))
        producer (build "producer" text)
        old1 "(dsq-walk M S A V schemas (vector-at V (+ 2 (* 2 i))) 0)"
        start (.index text "(defn- dsq-schemas ")
        before (subs text 0 start)
        after (subs text start)
        _ (u/chk (= 1 (.count after old1)))
        mutant-transitive (build "mutant-transitive" (str before (.replace after old1 "0" 1)))
        old2 "(dsq-walk M S A V schemas (dcp-field M S map \":param-types\") 0)"
        _ (u/chk (= 1 (.count text old2)))
        mutant-params (build "mutant-params" (.replace text old2 "0" 1))
        old3 "(dsq-catalog M S A doc)"
        _ (u/chk (= 1 (.count text old3)))
        mutant-catalog (build "mutant-catalog" (.replace text old3 "A" 1))
        _ (operator/setitem report "images"
                        (u/pydict-from (for [[n i] [["producer" producer] ["mutant-transitive" mutant-transitive]
                                                    ["mutant-params" mutant-params] ["mutant-catalog" mutant-catalog]]]
                                         [n (u/pin i)])))
        _ (save)
        evaluate (fn evaluate
                   ([name source] (evaluate name source producer 0))
                   ([name source image code]
                    (let [path (.joinpath out (str name ".kir"))]
                      (.write_text path source)
                      (operator/setitem (u/geti report "inputs") name (u/pin path))
                      (let [p (run name image [(if darwin (.-name path) path)] code)]
                        (if (pos? code)
                          (do (u/chk (and (not (u/nonempty? (.-stdout p))) (.startswith (.-stderr p) (.encode "SCHEMA:"))))
                              {})
                          (do (u/chk (not (u/nonempty? (.-stderr p))))
                              (let [lines (vec (.splitlines (.decode (.-stdout p))))]
                                (u/chk (= "DCP1 6 2" (first lines)))
                                (reduce (fn [rows line]
                                          (let [row (vec (.split line))]
                                            (u/chk (and (= 4 (count row)) (not (contains? rows (first row)))))
                                            (assoc rows (first row) (vec (rest row)))))
                                        {} (rest lines)))))))))
        f42 (fn [s] (module (get schemas s) [(kfn "f" "42")]))
        g42 (fn [s] (module (get schemas s) [(kfn "g" "42" "[]" "[]")]))]
    (doseq [name ["simple" "wide" "unrelated" "transitive" "transitive-edit" "reordered" "cycle"]]
      (let [expected (case name "unrelated" "simple" "reordered" "transitive" name)]
        (u/chk (= (get golden expected) (first (get (evaluate name (f42 name)) "f"))) name)))
    (doseq [name ["missing" "missing-transitive" "duplicate" "bad-name" "bad-type" "bad-unused" "duplicate-field"]]
      (evaluate name (f42 name) producer 1))
    (let [pure (first (get (evaluate "pure" (module "{}" [(kfn "g" "42" "[]" "[]")])) "g"))
          _ (evaluate "bad-legacy" (g42 "bad-legacy") producer 1)
          mixed (evaluate "mixed" (module (get schemas "simple") [(kfn "f" "42") (kfn "g" "42" "[]" "[]")]))]
      (u/chk (and (= (get golden "simple") (first (get mixed "f"))) (= pure (first (get mixed "g")))))
      (doseq [name ["simple" "wide" "unrelated"]]
        (let [functions [(kfn "f" "(if true 42 (g x))") (kfn "g" "(if true 43 (f x))")]
              actual (evaluate (str "scc-" name) (module (get schemas name) functions))
              [group f g] (get scc (if (= name "unrelated") "simple" name))]
          (u/chk (= actual {"f" [f group "0"] "g" [g group "1"]}) name)))
      (u/chk (not= (get golden "transitive") (first (get (evaluate "mutant-transitive" (f42 "transitive") mutant-transitive 0) "f"))))
      (u/chk (= (get golden "simple") (first (get (evaluate "mutant-transitive-control" (f42 "simple") mutant-transitive 0) "f"))))
      (u/chk (not= (get golden "simple") (first (get (evaluate "mutant-params" (f42 "simple") mutant-params 0) "f"))))
      ;; Removing the catalog check must admit the otherwise unreferenced bad schema; the normal producer refuses the
      ;; same module atomically.
      (u/chk (= pure (first (get (evaluate "mutant-catalog" (g42 "bad-legacy") mutant-catalog 0) "g")))))
    (operator/setitem report "status" "PASS_NATIVE_KIR_SCHEMA_CLOSURE")
    (save)
    (println (u/geti report "status") (count (u/geti report "calls")) "calls")
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
        (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-schema-closure-native.cljc") (str/ends-with? % "/check-schema-closure-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
