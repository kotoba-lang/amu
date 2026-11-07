;; Observe native kernel-project memory/I/O images; guest execution is separate.
;; Ported from check-aiueos-memory-project-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-memory-project-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-memory-project-native
  (:require [aiueos-gate :as g]
            [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import operator sys))

(def value 0x123456789abcdef)
(def base "region")
;; The old fixture granted a literal physical address. The locked image now obtains memory only from an explicit
;; owner. Reuse the boot ABI's eight-byte scratch record, restoring it before returning.
(def region "(kernel-subregion (kernel-boot-info) 16544 152 8)")

(def width-rows
  (vec (for [[tier size] [["" 512] ["-4k" 4096] ["-16k" 16384] ["-64k" 65536]]
             bits [8 16 32 64]]
         {:store (str "kernel-store-u" bits tier) :load (str "kernel-load-u" bits tier) :bits bits :maximum size})))

(def memory
  (let [bindings (concat [(str base " " region) (str "saved (kernel-load-u64 " base " 8 0)")]
                         (mapcat (fn [k {:keys [store load]}]
                                   [(str "s" k " (" store " " base " 8 0 " value ")") (str "l" k " (" load " " base " 8 0)")])
                                 (range) width-rows)
                         [(str "restored (kernel-store-u64 " base " 8 0 saved)")])
        checks (concat (mapcat (fn [k {:keys [bits]}]
                                 [(str "(= s" k " " value ")") (str "(= l" k " " (bit-and value (dec (bit-shift-left 1 bits))) ")")])
                               (range) width-rows)
                       ["(= restored saved)"])]
    (str "(ns memory (:export [main]))\n(defn main [] :i64 (let [" (str/join "\n" bindings) "] (if (and " (str/join " " checks) ") 42 0)))\n")))

(def pci
  "(ns pci (:export [main]))
(defn main [] :i64
  (let [mark (kernel-out-u8 233 65)
        selected (kernel-out-u32 3320 (+ 2147483648 (* 0 mark)))
        wide (kernel-in-u32 (+ 3324 (* 0 selected)))
        byte (kernel-in-u8 3324)]
    (if (and (= (bit-and wide 65535) 32902) (= byte 134)) 42 0)))
")

(def cases
  [["memory-widths" memory] ["q35-pci-ports" pci]
   ["loaded-base" (str "(ns bad (:export [main]))\n(defn main [] :i64 (let [" base " " region " p (kernel-load-u64 " base " 8 0)] (kernel-load-u8 p 8 0)))\n")]
   ["computed-base" (str "(ns bad (:export [main]))\n(defn main [] :i64 (let [" base " " region "] (kernel-load-u8 (+ " base " 1) 8 0)))\n")]
   ["literal-base" "(ns bad (:export [main]))\n(defn main [] :i64 (kernel-load-u8 1089536 8 0))\n"]])

(defn main [build output complete]
  (let [[source producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir output ** :parents true :exist_ok false)
        verify (g/load-source-var "check-aiueos-image-native.cljc" 'check-aiueos-image-native/verify)
        routes (python/list)]
    (doseq [producer producers]
      (let [out (.joinpath output (.-stem producer))
            _ (.mkdir out)
            calls (python/list) artifacts (python/dict)
            env (python/dict {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"})]
        (doseq [[name text] cases]
          (let [src (.joinpath out (str name ".kotoba")) image (.joinpath out (str name ".elf")) lock (.joinpath out (str name ".ksl"))
                _ (.write_text src text)
                _ (.write_text lock (u/ksl-text src out))
                r (u/run-process [producer "compile" src "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image" "--output" image
                                  "--fuel" "1000000" "--source-path" out "--source-lock" lock
                                  "--source-lock-sha256" (u/geti (u/pin lock) "sha256")] env 180)]
            (.append calls (u/pydict "name" name "exit" (.-returncode r) "stdout" (.decode (.-stdout r)) "stderr" (.decode (.-stderr r))
                                     "source" (u/pin src) "lock" (u/pin lock)))
            (if (str/ends-with? name "base")
              (u/chk (and (= 1 (.-returncode r)) (u/has-bytes? (.encode "E7106") (.-stderr r)) (not (.exists image))) [name (.-returncode r) (.-stderr r)])
              (do
                (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r)))) [name (.-returncode r) (.-stderr r)])
                (verify (.read_bytes image) 1000000 true)
                (operator/setitem artifacts name (u/pin image))
                (let [efi (.joinpath out (str name ".efi"))
                      r2 (u/run-process [producer "package-aiueos-boot" image "--output" efi] env 180)]
                  (u/chk (and (zero? (.-returncode r2)) (not (u/nonempty? (.-stderr r2)))) [name (.-stderr r2)])
                  (operator/setitem artifacts (str name "-efi") (u/pin efi)))))))
        (.write_text (.joinpath out "commands.json") (u/json-dump calls))
        (.append routes (u/pydict "producer" (u/pin producer) "artifacts" artifacts))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_KERNEL_MEMORY_PROJECT_IMAGES" "source" source "routes" routes
                           "operationPairs" (u/to-py (mapv (fn [m] (into {} (map (fn [k] [(name k) (get m k)]) [:store :load :bits :maximum]))) width-rows))
                           "qemuBoot" false "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath output "native-memory-project.json") (u/json-dump report))
      (println (u/geti report "status") "all32 width/tier operations and q35 PCI port fixture; guest execution pending"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-memory-project-native.cljc") (str/ends-with? % "/check-aiueos-memory-project-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
