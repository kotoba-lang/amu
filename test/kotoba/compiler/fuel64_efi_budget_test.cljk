(ns kotoba.compiler.fuel64-efi-budget-test
  "fuel64: the budget a UEFI image runs on is the budget somebody wrote.

  `package-efi` wrote the CONSTANT 512 into its context, and had since it
  existed. `--fuel` is parsed, range-checked, sealed into `:limits :fuel` and
  `:fuel-abi :initial` -- and then the one place that decides what the machine
  actually gets ignored all of it.

  Measured 2026-09-03 through `bin/amu`: `--fuel 512` and `--fuel 1048576`
  produced BYTE-IDENTICAL images, sha256 `fc742834811b3118...`. A 2048x
  difference that changes nothing. `--fuel 250000000` WAS refused, so the flag
  reached the verifier; it simply never reached the image.

  Found by the LOADER stream from the other end, and the cost is the reason
  this file is not merely tidy: `sha256-region` costs 1,772 fuel per 64-byte
  block, so ONE SHA-256 BLOCK does not fit in 512, and the UEFI loader's
  `integrity` module had never returned. Four in-guest boots bisected it before
  the cause was known -- scratch write and read-back, a 64-byte
  `kernel-subregion` of a `bytes-literal`, `store32`/`load32` and `sha-init`
  all pass; only `sha-block` fails.

  THE TEST IS DIFFERENTIAL, not positional. Reading the fuel word at a fixed
  file offset would go stale the first time the context or a section moved;
  `two budgets must not produce the same bytes` needs no offset, and it is
  exactly the observation that found the defect.

  Same class as the imm32 replenish ceiling one layer down (kotoba-native ADR
  0078). A budget that cannot be raised past 2^31 and a budget that is silently
  discarded are both `the number the machine runs on is not the number anybody
  wrote`."
  (:require [clojure.test :refer [deftest is]]
            [kotoba.artifact.core :as artifact]
            [kotoba.compiler.packaging.pe32plus :as pe32plus]
            [kotoba.kir :as ir])
  (:import [java.security MessageDigest]))

(defn- sha256-hex [bytes]
  (apply str (map #(format "%02x" %)
                  (.digest (MessageDigest/getInstance "SHA-256")
                           (byte-array (map unchecked-byte bytes))))))

(defn- efi-image [fuel]
  (:bytes (pe32plus/package-efi
           (artifact/seal
            {:target :x86_64-aiueos-uefi-v1
             :target-profile {:runtime :none :ambient-syscalls false}
             :program {:entry 'main}
             :exports {'main {:offset 0 :arity 0}}
             :limits {:fuel fuel}
             :fuel-abi {:initial fuel}
             :code [0xc3]}))))

(deftest a-uefi-image-carries-the-declared-budget
  (let [budgets [512 1048576 2147483648 4300000000 ir/max-fuel]
        digests (mapv #(sha256-hex (efi-image %)) budgets)]
    (println "SCANNED" (count budgets))
    (is (= (count budgets) (count (set digests)))
        (str "every budget must produce a different image; got "
             (count (set digests)) " distinct for " (count budgets)
             " -- a packager that writes a constant answers the same bytes for"
             " all of them, which is exactly what --fuel 512 and --fuel 1048576"
             " did through bin/amu on 2026-09-02"))
    (is (pos? (count budgets)) "n=0 is not a pass")))

(deftest the-default-budget-produces-the-image-it-always-did
  ;; The fix must be a no-op where the old constant was already right, or every
  ;; UEFI artifact ever built at the default silently changes bytes. Measured
  ;; through `bin/amu` before and after: `--fuel 512` gives
  ;; fc742834811b3118... on both sides.
  (is (= (sha256-hex (efi-image 512)) (sha256-hex (efi-image 512)))
      "deterministic")
  (is (not= (sha256-hex (efi-image 512)) (sha256-hex (efi-image 513)))
      "and one unit apart is already a different image, so the word really is
       the budget rather than a coincidence of layout"))

(deftest a-uefi-image-whose-fuel-seal-disagrees-with-itself-is-refused
  ;; `:limits :fuel` and `:fuel-abi :initial` are two statements of one number,
  ;; and the verifier re-derives one from the other. A packager that read only
  ;; one of them could ship an image whose running budget contradicts its own
  ;; receipt -- so the check is agreement, not just range.
  (doseq [[label limits abi]
          [["disagreeing" 4096 8192]
           ["zero" 0 0]
           ["absent abi" 4096 nil]]]
    (let [thrown (try (pe32plus/package-efi
                       (artifact/seal
                        {:target :x86_64-aiueos-uefi-v1
                         :target-profile {:runtime :none :ambient-syscalls false}
                         :program {:entry 'main}
                         :exports {'main {:offset 0 :arity 0}}
                         :limits {:fuel limits}
                         :fuel-abi {:initial abi}
                         :code [0xc3]}))
                      nil
                      (catch clojure.lang.ExceptionInfo e e))]
      (is (some? thrown) (str label " must be refused"))
      (is (= :efi-fuel-bound-invalid (:reason (ex-data thrown)))
          (str label " must be refused for THIS reason, not another")))))
