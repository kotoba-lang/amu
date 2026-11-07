;; Observe whole-project canonical SIR provenance and scalar stack calls.
;;
;; No alternate region policy, native controller or compiler in this observer.
;; Ported from check-aiueos-regions-native.py (Basilisp). Linux only.
;; Run: basilisp run scripts/seed/check-aiueos-regions-native.cljc -- (--build DIR | --complete DIR) --output OUT
(ns check-aiueos-regions-native
  (:require [aiueos-native-proof :as proof]
            [basilisp.string :as str]
            [gate-util :as u])
  (:import operator sys))

(def good-entry "(ns entry (:require [lib.bridge :as b]) (:export [main]))\n(defn main [] :i64 42)\n")
(def good-bridge "(ns lib.bridge (:require [lib.memory :as m]) (:export [through]))\n(defn through [base :i64 length :i64] :i64 (m/read base length))\n")
(def good-memory "(ns lib.memory (:export [read]))\n(defn- leaf [base :i64 length :i64] :i64 (kernel-load-u8 base length 0))\n(defn read [base :i64 length :i64] :i64 (leaf base length))\n")

(defn main [build output complete]
  (let [[source producers _] (proof/load-native-producers :build build :complete complete)
        _ (.mkdir output ** :parents true :exist_ok false)
        routes (python/list)]
    (doseq [producer producers]
      (let [out (.joinpath output (.-stem producer))
            _ (.mkdir (.joinpath out "lib") ** :parents true)
            entry (.joinpath out "entry.kotoba") bridge (.joinpath out "lib/bridge.kotoba") memory (.joinpath out "lib/memory.kotoba")
            lock (.joinpath out "source.ksl")
            calls (python/list)
            reset (fn [] (.write_text entry good-entry) (.write_text bridge good-bridge) (.write_text memory good-memory))
            compile- (fn [name expected]
                       (.write_text lock (str "KSL1\nentry " entry "\nroot " out "\n"
                                              (apply str (for [p (sort-by str [entry bridge memory])] (str "file " (u/geti (u/pin p) "sha256") " " p "\n")))))
                       (let [image (.joinpath out (str name ".elf"))
                             r (u/run-process [producer "compile" entry "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image" "--output" image
                                               "--fuel" "1000000" "--source-path" out "--source-lock" lock
                                               "--source-lock-sha256" (u/geti (u/pin lock) "sha256")]
                                              (python/dict {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"}) 240)]
                         (.append calls (u/pydict "name" name "exit" (.-returncode r) "stdout" (.decode (.-stdout r)) "stderr" (.decode (.-stderr r))
                                                  "sourceLock" (u/pin lock)))
                         (.write_text (.joinpath out "commands.json") (u/json-dump calls))
                         (u/chk (and (= expected (.-returncode r)) (not (u/has-bytes? (.encode "KEXE_TRAP") (.-stderr r)))) [name (.-returncode r) (.-stderr r)])
                         (if (not (zero? expected))
                           (u/chk (and (u/has-bytes? (.encode "E7106") (.-stderr r)) (not (.exists image))) [name (.-stderr r)])
                           (u/chk (and (not (u/nonempty? (.-stderr r))) (.is_file image)) [name (.-stderr r)]))
                         image))]
        (reset)
        ;; Uncalled helpers remain in the graph and use the same conservative adjacent base/length rule as
        ;; canonical object admission.
        (let [valid (compile- "canonical-helper-graph" 0)]
          (doseq [[name file before after]
                  [["literal-through-import" entry ":i64 42)" ":i64 (b/through 1089536 64))"]
                   ["length-lie-through-import" bridge "(m/read base length)" "(m/read base 4096)"]
                   ["second-bad-caller" bridge "\n" "\n(defn- bad [] :i64 (m/read 1089536 64))\n"]
                   ["private-length-lie" memory "(leaf base length)" "(leaf base 512)"]
                   ["private-computed-base" memory "(leaf base length)" "(leaf (+ base 8) length)"]
                   ["loaded-base" memory "(leaf base length)" "(leaf (kernel-load-u64 base length 0) length)"]
                   ["subregion-parent-length" memory "(leaf base length)" "(leaf (kernel-subregion base 4096 0 64) 64)"]
                   ["subregion-output-length" memory "(leaf base length)" "(leaf (kernel-subregion base length 0 64) 32)"]]]
            (reset)
            (.write_text file (.replace (.read_text file) before after 1))
            (compile- name 1))
          (reset)
          ;; The independent stack-ABI fixture has no privileged memory ops, so the canonical AArch64 backend can
          ;; execute this same full graph.
          (let [params (str/join " " (for [i (range 16)] (str "a" i " :i64")))]
            (.write_text memory "(ns lib.memory (:export [read]))\n(defn read [base :i64 length :i64] :i64 0)\n")
            (.write_text bridge (str "(ns lib.bridge (:require [lib.memory :as m]) (:export [sum16]))\n(defn sum16 [" params "] :i64 (+ "
                                     (str/join " " (for [i (range 16)] (str "a" i))) "))\n"))
            (.write_text entry (str "(ns entry (:require [lib.bridge :as b]) (:export [main]))\n(defn main [] :i64 (- (b/sum16 "
                                    (str/join " " (for [i (range 16)] (str (inc i)))) ") 94))\n")))
          (let [stack (compile- "stack16" 0)
                artifacts (u/pydict "helperGraph" (u/pin valid) "stack16" (u/pin stack))]
            (doseq [[label image] [["helper-graph" valid] ["stack16" stack]]]
              (let [efi (.joinpath out (str label ".efi"))
                    r (u/run-process [producer "package-aiueos-boot" image "--output" efi]
                                     (python/dict {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out)}) 180)]
                (u/chk (and (zero? (.-returncode r)) (not (u/nonempty? (.-stderr r)))) (.-stderr r))
                (operator/setitem artifacts (str label "EFI") (u/pin efi))))
            (.append routes (u/pydict "producer" (u/pin producer) "artifacts" artifacts "refusalCount" 8))))))
    (u/chk (u/deq (u/geti (u/geti routes 0) "artifacts") (u/geti (u/geti routes 1) "artifacts")))
    (let [report (u/pydict "status" "PASS_NATIVE_CANONICAL_PROJECT_PROVENANCE" "source" source "routes" routes
                           "qemuBoot" false "fullKernel" false "nativeCDCI" false)]
      (.write_text (.joinpath output "native-regions.json") (u/json-dump report))
      (println (u/geti report "status") "resolved whole-project SIR, 8 refusals and scalar16 calls"))))

(defn -main [& args]
  (let [[build out complete] (u/parse-build-complete-output args)]
    (main build out complete)))

(when (some #(or (= % "check-aiueos-regions-native.cljc") (str/ends-with? % "/check-aiueos-regions-native.cljc")) sys/argv)
  (apply -main *command-line-args*))
