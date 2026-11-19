;; Build Amu to a Mac native fixed point, then check user-v2 Goal ELFs.
;;
;; This stages and observes; the signed Amu images compile every Kotoba source and emit every ELF. This gate does not
;; claim an AIUEOS guest or Itonami turn. Ported from check-aiueos-user-v2-macos-native.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-user-v2-macos-native.cljc -- --output DIR
;;      --compiler-image F --compiler-sha256 H --packager-image F --packager-sha256 H
(ns check-aiueos-user-v2-macos-native
  (:require [basilisp.string :as str]
            [aiueos-user-v2 :as v2]
            [gate-util :as u]
            [macos-native-lib :as mac]
            [macos-user-target :as target])
  (:import operator pathlib struct sys))

(def v2-path (.joinpath u/root "scripts/seed/check-aiueos-user-v2-native.cljc"))
(def observer-path (.joinpath u/root "scripts/seed/check-aiueos-user-v2-macos-native.cljc"))
(def slot-sha256 "b88caa63c3b782a550f4aefdb84e8ad47be0c6f578cb58352a50573bc05e9b23")
(defn- stderr-has? [result code] (u/has-bytes? (.encode code) (.-stderr result)))

(defn main [args]
  (let [v2-pin (mac/require-regular v2-path)
        _ (target/main args)
        output (.resolve (pathlib/Path (:output args)))
        v1-receipt (.joinpath output "mac-aiueos-user-target.json")
        v1 (u/read-json v1-receipt)
        _ (when (not= (u/geti v1 "status") "PASS_MAC_NATIVE_USER_TARGET_SELFHOST")
            (mac/fail "v1 Mac native fixed point was not verified"))
        compiler (.joinpath output (str "F" (u/geti v1 "fixedPointGeneration") "-signed.macho"))
        signed-pin (fn [] (u/geti (last (u/geti v1 "generations")) "signed"))
        _ (when-not (u/deq (mac/pin compiler) (signed-pin)) (mac/fail "fixed-point compiler digest mismatch"))
        p (fn [n] (.joinpath output n))
        positives (u/pydict)]
    (doseq [[name src] [["goal" v2/source] ["constant" v2/constant]]]
      (let [sp (p (str "v2-" name ".kotoba")) elf (p (str "v2-" name ".elf"))]
        (.write_text sp src)
        (mac/native-run compiler output ["compile" (.-name sp) "--target" v2/target "--output" (.-name elf)])
        (v2/verify (.read_bytes elf))
        (.__setitem__ positives name (u/pydict "source" (mac/pin sp) "elf" (mac/pin elf)))))
    (let [slot-names ["v2-goal-slot.bin" "v2-goal-slot.reproduced.bin"]]
      (doseq [name slot-names]
        (mac/native-run compiler output ["package-aiueos-user-payload" "v2-goal.elf" "--output" name "--version" "v2"]))
      (let [slot (.read_bytes (p (first slot-names)))
            goal-elf (.read_bytes (p "v2-goal.elf"))
            n (python/len goal-elf)]
        (when (or (not= (python/len slot) 524288)
                  (not= (vec (struct/unpack_from "<QQQ" slot 0)) [0x0031444c50554941 2 n])
                  (not (u/deq (u/bslice slot 64 (+ 64 n)) goal-elf))
                  (python/any (u/bslice slot (+ 64 n) (python/len slot)))
                  (not (u/deq slot (.read_bytes (p (second slot-names)))))
                  (not= (u/geti (mac/pin (p (first slot-names))) "sha256") slot-sha256))
          (mac/fail "native v2 slot disagrees with the pinned guest fixture"))
        (let [slot-refusals (u/pydict)
              malformed (python/bytearray goal-elf)]
          (operator/setitem malformed 24 (bit-xor (operator/getitem malformed 24) 1))
          (.write_bytes (p "v2-wrong-entry.elf") malformed)
          (doseq [[name src version code] [["wrong-entry" "v2-wrong-entry.elf" "v2" "E7111"]
                                           ["wrong-version" "v2-goal.elf" "v3" "E7110"]]]
            (let [destination (str "v2-" name "-slot.bin")
                  refused (mac/native-run compiler output ["package-aiueos-user-payload" src "--output" destination "--version" version]
                                          :expected (if (= name "wrong-entry") 1 2))]
              (when (or (not (stderr-has? refused code)) (.exists (p destination)))
                (mac/fail (str "v2 slot " name " did not refuse before output")))
              (.__setitem__ slot-refusals name (u/pydict "error" code "artifactAbsent" true))))
          (let [existing (mac/native-run compiler output ["package-aiueos-user-payload" "v2-goal.elf" "--output" (first slot-names) "--version" "v2"] :expected 2)]
            (when-not (stderr-has? existing "E7110") (mac/fail "v2 slot packager overwrote an existing output"))
            (.__setitem__ slot-refusals "existing-output" (u/pydict "error" "E7110" "artifactAbsent" false)))
          ;; The verifier must reject a different memory contract and an embedded nonzero context, rather than merely
          ;; recognizing its positive image.
          (let [mutation (python/bytearray (.read_bytes (p "v2-goal.elf")))]
            (struct/pack_into "<Q" mutation (+ 120 40) 321)
            (when (try (v2/verify mutation) true (catch python/ValueError _ false))
              (mac/fail "wrong v2 request region size was accepted")))
          (let [mutation (python/bytearray (.read_bytes (p "v2-goal.elf")))]
            (operator/setitem mutation (+ 8192 24) 1)
            (when (try (v2/verify mutation) true (catch python/ValueError _ false))
              (mac/fail "nonzero embedded context was accepted")))
          (let [refusals (u/pydict)]
            (doseq [[name src code] v2/refusals]
              (let [sp (p (str "v2-" name ".kotoba")) elf (p (str "v2-" name ".elf"))]
                (.write_text sp src)
                (let [refused (mac/native-run compiler output ["compile" (.-name sp) "--target" v2/target "--output" (.-name elf)] :expected 1)]
                  (when (or (not (stderr-has? refused code)) (.exists elf))
                    (mac/fail (str "v2 " name " did not refuse with " code " and no artifact")))
                  (.__setitem__ refusals name (u/pydict "source" (mac/pin sp) "error" code "artifactAbsent" true)))))
            (when (or (not (u/deq (mac/pin v2-path) v2-pin)) (not (u/deq (mac/pin compiler) (signed-pin))))
              (mac/fail "v2 gate input changed during qualification"))
            (let [report (u/pydict "schema" "amu.mac-aiueos-user-v2-goal.v1" "status" "PASS_MAC_NATIVE_USER_V2_GOAL_ELF"
                                   "v1FixedPointReceipt" (mac/pin v1-receipt) "fixedPointGeneration" (u/geti v1 "fixedPointGeneration")
                                   "compiler" (mac/pin compiler) "source" (u/geti v1 "source")
                                   "checker" v2-pin "observer" (mac/pin observer-path)
                                   "target" v2/target "positives" positives "refusals" refusals
                                   "userSlot" (mac/pin (p (first slot-names))) "userSlotReproduced" (mac/pin (p (second slot-names)))
                                   "userSlotRefusals" slot-refusals
                                   "regionMutationRejected" true "contextMutationRejected" true
                                   "guestExecution" false "ItonamiTurn" false "releaseAdmission" false
                                   "linuxProcessInThisGate" false)]
              (.write_text (p "mac-aiueos-user-v2-goal.json") (u/json-dump report))
              (println (u/geti report "status") (u/geti (u/geti (u/geti positives "goal") "elf") "sha256"))
              (.flush sys/stdout))))))))

(defn -main [& args]
  (main {:compiler-image (u/opt args "--compiler-image") :compiler-sha256 (u/opt args "--compiler-sha256")
         :packager-image (u/opt args "--packager-image") :packager-sha256 (u/opt args "--packager-sha256")
         :output (or (u/opt args "--output") (sys/exit "--output is required"))}))

(when (some #(or (= % "check-aiueos-user-v2-macos-native.cljc") (str/ends-with? % "/check-aiueos-user-v2-macos-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
