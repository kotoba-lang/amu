(ns kotoba.compiler.aggregate-abi-test
  (:require [clojure.edn :as edn]
            [clojure.test :refer [deftest is]]
            [kotoba.native.aggregate-abi :as aggregate-abi]
            [kotoba.native.machine-ir :as machine]))

(defn- dependency-pin [coordinate]
  (get-in (edn/read-string (slurp "deps.edn")) [:deps coordinate :git/sha]))

(deftest pinned-closure-carries-the-complete-native-boundary
  ;; Advanced 2026-08-31: `elf64.clj` and `elf64.cljc` are a twin and the JVM
  ;; loads the `.clj`, but nothing measured that they agreed. They had drifted
  ;; to 74 entries against 69 -- three names only in `.cljc`, eight only in
  ;; `.clj` -- and because the JVM packager is the one that runs, the three it
  ;; was missing made three aiueos kernel objects stop building. They surfaced
  ;; as `:kotoba/internal-error`, "internal compiler error", which reads like a
  ;; crash in THIS compiler and is not one. Both tables now carry the union,
  ;; and `elf64-twin-parity-test` keeps them there. The advance also upstreams
  ;; the three ecdsa entries aiueos was patching in locally and puts the ecdsa
  ;; objects in the fuel tier a scalar multiplication needs.
  (is (= "db7b711946495b96d25a39390bcb71797461e261"
         (dependency-pin 'io.github.kotoba-lang/kotoba-native)))
  ;; Advanced 2026-08-31 for two more instances of ADR-0286's class -- a KIR
  ;; i64 is a BigInt under ClojureScript and reached a host operation that
  ;; cannot take one. There, `hetero-vector-at`; here, `uleb` (every
  ;; capability contract writes one) and, in kotoba-wasm, the `[:capability
  ;; id]` import key, which ClojureScript cannot hash at all. Together they
  ;; made `compile --jvm-free --target wasm32-browser` an internal compiler
  ;; error for any guest declaring a capability, while `check --jvm-free`
  ;; passed. The same advance also drops an npm package (`@noble/hashes`) out
  ;; of `kotoba.kir.value`'s ClojureScript require graph.
  (is (= "ff7a3ae2672f8ecdda54aa1abba3d480a2963733"
         (dependency-pin 'io.github.kotoba-lang/kotoba-kir)))
  (is (= "d007aa108d1eab91172c763a1c9d3cb2a0803a9e"
         (dependency-pin 'io.github.kotoba-lang/kotoba-verifier)))
  (is (= 7 (:abi/version aggregate-abi/contract)))
  (is (= :recursive-word-handles
         (get-in aggregate-abi/contract
                 [:portable/record :boundary/field-representation])))
  (is (= 32
         (get-in aggregate-abi/contract
                 [:portable/record :boundary/max-nesting-depth])))
  (is (= :word-pair-chain-admitted (get-in aggregate-abi/contract
                        [:extracted :record-boundary])))
  (is (= :recursive-payload-pair-handle-admitted (get-in aggregate-abi/contract
                        [:extracted :variant-boundary])))
  (is (= :sealed-callable-admitted (get-in aggregate-abi/contract
                                            [:extracted :call-admission])))
  (is (= {:indirect :closed-ordinal-dispatch
          :apply :bounded-pair-chain
          :max-apply-arguments 4
          :arbitrary-address false}
         (get-in aggregate-abi/contract [:extracted :callable-dispatch])))
  (is (= {:mode :closed-module-graph
          :ambient-symbols false
          :unresolved-symbols false}
         (get-in aggregate-abi/contract [:extracted :linkage])))
  (is (= :all-allocator-registers
         (get-in aggregate-abi/contract
                 [:targets :x86-64 :call-clobbers])))
  (is (= :all-allocator-registers
         (get-in aggregate-abi/contract
                 [:targets :aarch64 :call-clobbers]))))

(deftest pinned-aarch64-constant-selector-is-small-and-bounded
  (let [magic -9223372032559808509
        chunks (#'machine/a64-constant-chunks magic)
        recognize (var-get #'machine/a64-logical-immediate-fields)
        probes (atom 0)]
    (is (= [0xe0 0x0b 0x41 0xb2 0x20 0x00 0xc0 0xf2]
           (#'machine/a64-constant :aarch64/x0 magic))
        "the modular-mix reciprocal is exactly one logical seed plus one MOVK")
    (is (nil? (ns-resolve 'kotoba.native.machine-ir
                          'a64-logical-seed-index))
        "the pin does not restore the cold global candidate index")
    (with-redefs [machine/a64-logical-immediate-fields
                  (fn [candidate]
                    (swap! probes inc)
                    (recognize candidate))]
      (is (some? (#'machine/a64-logical-seed-plan chunks)))
      (is (<= @probes 8)
          "four lanes times zero/full replacement is the structural ceiling"))))

(deftest standalone-expressions-still-reject-calls-but-modules-admit-them
  (is (not (machine/pilot-expression? ['x] '(callee x))))
  (try
    (machine/lower-kir-expression ['x] '(callee x))
    (is false "standalone call-shaped KIR must require module lowering")
    (catch clojure.lang.ExceptionInfo error
      (is (= :aggregate-abi (:phase (ex-data error))))
      (is (= :call-abi-not-admitted (:problem (ex-data error))))))
  (let [module {:format :kotoba.kir/v4
                :exports ['main]
                :functions [{:name 'inc-one :params ['x] :result :i64
                             :body '(+ x 1)}
                            {:name 'main :params [] :result :i64
                             :body '(let [live 40]
                                      (+ live (inc-one 1)))}]}
        gmir (machine/lower-kir-module module)]
    (is (machine/pilot-module? module))
    (is (= 3 (:gmir/version gmir)))
    (is (= ['inc-one 'main]
           (mapv :gmir/name (:gmir/functions gmir))))
    (doseq [target [:x86-64 :aarch64]]
      (let [mc (machine/compile-gmir target gmir)
            caller (second (:mc/functions mc))
            encodings (map :mc/encoding (:mc/instructions caller))]
        (is (= :call-live (:mc/frame-policy caller)) target)
        (is (zero? (:mc/frame-slots caller)) target)
        (is (not-any? #{(keyword (name target) "spill-store")
                        (keyword (name target) "spill-load")}
                      encodings)
            [target "the call-crossing value is preserved, not spilled
                     (kotoba-mir 8a2bc4d via kotoba-native 1fd9c22)"])))))

(deftest pinned-closure-carries-the-zero-frame-four-argument-entry
  (let [module {:format :kotoba.kir/v4
                :exports ['main]
                :functions
                [{:name 'sum-four :params ['a 'b 'c 'd] :result :i64
                  :body '(+ (+ a b) (+ c d))}
                 {:name 'main :params [] :result :i64
                  :body '(sum-four 1 2 4 8)}]}]
    (doseq [target [:x86-64 :aarch64]]
      (let [[callee caller]
            (:mc/functions (->> module machine/lower-kir-module
                                (machine/compile-gmir target)))
            spill-encodings #{(keyword (name target) "spill-store")
                              (keyword (name target) "spill-load")}]
        (is (= [0 0] (mapv :mc/frame-slots [callee caller])) target)
        (is (= [:allocator :call-live]
               (mapv :mc/frame-policy [callee caller])) target)
        (is (not-any? #(contains? spill-encodings (:mc/encoding %))
                      (mapcat :mc/instructions [callee caller])) target)))))

(deftest five-argument-entries-no-longer-spill-the-excess-input
  (let [module {:format :kotoba.kir/v4
                :exports ['main]
                :functions
                [{:name 'sum-five :params ['a 'b 'c 'd 'e] :result :i64
                  :body '(+ (+ (+ a b) (+ c d)) e)}
                 {:name 'main :params ['a 'b 'c 'd 'e] :result :i64
                  :body '(sum-five a b c d e)}]}]
    (doseq [target [:x86-64 :aarch64]]
      (let [[callee caller]
            (:mc/functions (->> module machine/lower-kir-module
                                (machine/compile-gmir target)))
            functions [callee caller]
            store-encoding (keyword (name target) "spill-store")
            load-encoding (keyword (name target) "spill-load")]
        ;; A fifth live argument used to exhaust the four-register allocator
        ;; and get backed directly from its ABI register: one slot, one store,
        ;; one lazy reload, in each of the two functions. The pool now reaches
        ;; past four, so five arguments all arrive in registers and neither
        ;; function touches the stack.
        (is (= [0 0] (mapv :mc/frame-slots functions)) target)
        (is (= [:allocator :call-live]
               (mapv :mc/frame-policy functions)) target)
        (doseq [function functions]
          (let [encodings (map :mc/encoding (:mc/instructions function))]
            (is (zero? (count (filter #{store-encoding} encodings)))
                [target (:mc/name function)])
            (is (zero? (count (filter #{load-encoding} encodings)))
                [target (:mc/name function)])))))))
