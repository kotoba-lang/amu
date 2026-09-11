(ns kotoba.compiler.kernel-subregion-test
  "`kernel-subregion` is the only admitted way to narrow a kernel region.

  The kernel load/store bounds check constrains an index within a DECLARED
  length, and the caller supplies both the base and that length. Narrowing by
  hand -- `(fnv (+ base object-offset) object-length)`, which six aiueos
  objects did -- therefore produced a window nothing had checked. The
  frontend previously admitted that shape and merely reported it, because no
  checked form existed; now one does, and the hand-written form is refused.

  Runtime behaviour of the emitted checks is pinned in kotoba-native's
  isa-parity-test by disassembly-derived encoding assertions. Kernel targets
  are linkable ELF objects rather than runnable processes, so there is no
  execute-and-observe path here the way there is for userland artifacts --
  the same bar every other kernel op in this repository is held to."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.sema :as sema]))

(defn- provenance-rejection
  "The rejection message when SOURCE is refused for region provenance, or nil
  when admitted. Rethrows any OTHER rejection so a test cannot pass because
  the source was malformed for an unrelated reason."
  [source]
  (try (sema/analyze source) nil
       (catch Exception e
         (if (= :kotoba.error/kernel-region-provenance
                (:kotoba.error/code (ex-data e)))
           (.getMessage e)
           (throw e)))))

(deftest a-checked-narrowing-is-admitted-as-a-base
  (testing "directly in a base position"
    (is (nil? (provenance-rejection
               "(defn f [base length]
                  (kernel-load-u8 (kernel-subregion base length 48 16) 16 0))
                (defn main [] 0)"))))
  (testing "passed into a callee's base parameter, the aiueos shape"
    (is (nil? (provenance-rejection
               "(defn fnv [base length] (kernel-load-u8 base length 0))
                (defn f [base length] (fnv (kernel-subregion base length 48 16) 16))
                (defn main [] 0)"))))
  (testing "with a computed offset, which is exactly what the runtime check
            is for -- superblock-valid.kotoba range-checks object-offset out
            of the header it just read"
    (is (nil? (provenance-rejection
               "(defn fnv [base length] (kernel-load-u8 base length 0))
                (defn f [base length off len]
                  (fnv (kernel-subregion base length off len) len))
                (defn main [] 0)")))))

(deftest hand-written-arithmetic-is-no-longer-accepted-as-a-base
  (testing "the shape the six aiueos objects used before migrating"
    (is (some? (provenance-rejection
                "(defn fnv [base length] (kernel-load-u8 base length 0))
                 (defn f [base length] (fnv (+ base 48) 16))
                 (defn main [] 0)"))))
  (testing "and directly in a base position"
    (is (some? (provenance-rejection
                "(defn f [base length] (kernel-load-u8 (+ base 48) 16 0))
                 (defn main [] 0)")))))

(deftest the-parent-of-a-narrowing-is-itself-checked
  (testing "a narrowing does not launder an untraceable base: its own parent
            sits in argument position 0 and is checked like any other"
    (is (some? (provenance-rejection
                "(defn f [buf length]
                   (kernel-load-u8
                     (kernel-subregion (kernel-load-u8 buf length 0) 16 0 16) 16 0))
                 (defn main [] 0)")))))

(deftest narrowings-are-reported-with-their-offsets
  (let [hir (sema/analyze
             "(defn fnv [base length] (kernel-load-u8 base length 0))
              (defn static [base length] (fnv (kernel-subregion base length 48 16) 16))
              (defn dynamic [base length off] (fnv (kernel-subregion base length off 16) 16))
              (defn main [] 0)")
        derived (:derived-bases (sema/kernel-region-report (:functions hir)))
        by-fn (into {} (map (juxt :function :offset-static?)) derived)]
    (is (= 2 (count derived)))
    (is (true? (get by-fn 'static)))
    (is (false? (get by-fn 'dynamic))
        "a value offset is still worth surfacing even though the emitted
         check now bounds it")))

(deftest arity-is-enforced
  (is (thrown? Exception
               (sema/analyze "(defn f [b l] (kernel-subregion b l 0)) (defn main [] 0)"))))
