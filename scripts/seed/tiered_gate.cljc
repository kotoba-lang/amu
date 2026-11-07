;; Shared preamble of the tiered native bootstrap observers (check-tiered-*): validate the selfhost-bootstrap
;; receipt and its source graphs, stage the kx64 runner source, and provide run / compile-payload / execute.
;; Basilisp port of the identical preamble the three Python originals each carried. Linux arm64 only.
(ns tiered-gate
  (:require [gate-util :as u])
  (:import operator pathlib platform re))

(defn fail [message] (throw (python/ValueError (str message))))
(defn pin-of [p] (u/pydict "bytes" (python/len (.read_bytes p)) "sha256" (u/sha256-hex (.read_bytes p))))

(defn- check-graph! [repo graph what]
  (doseq [[name expected] (.items graph)]
    (let [path (pathlib/Path name)]
      (when (or (.is_absolute path) (contains? (set (.-parts path)) "..") (not (u/deq (pin-of (.joinpath repo path)) expected)))
        (fail (str what name))))))

(defn setup
  "Returns a map: :repo :boot :out :receipt-path :receipt :producer :c0 :source :tracked :before (atom of
  path-string -> pin) :rows (python list) :run :runner :compile-payload :execute. `this` is the observer file."
  [repo boot out this]
  (when-not (and (= "Linux" (platform/system)) (contains? #{"aarch64" "arm64"} (platform/machine)))
    (fail "requires a Linux arm64 execution host"))
  (let [repo (.resolve repo ** :strict true) boot (.resolve boot ** :strict true) out (.resolve out)
        receipt-path (.joinpath boot "selfhost-bootstrap.json")
        receipt (u/read-json receipt-path)
        _ (when (or (not= "PASS_LOADERLESS_SELFHOST_BOOTSTRAP" (.get receipt "status")) (not (contains? #{"pr" "main" "full"} (.get receipt "tier"))))
            (fail "invalid bootstrap status"))
        generation (u/geti (u/geti receipt "generations") -1)
        producer (.joinpath boot (str (u/geti generation "name") ".elf"))
        _ (when-not (u/deq (pin-of producer) (u/geti generation "image")) (fail "bootstrap F image mismatch"))
        _ (check-graph! repo (u/geti (u/geti receipt "sourceGraph") "full") "bootstrap source drift: ")
        _ (check-graph! repo (u/geti (u/geti receipt "adopted") "sourceGraph") "bootstrap source drift: ")
        c0 (when (= "full" (u/geti receipt "tier"))
             (let [c0 (.joinpath boot "C0.elf")
                   core (u/geti (u/geti receipt "provenance") "coreStatic")]
               (when-not (u/deq (pin-of c0) (u/geti core "C0")) (fail "bootstrap C0 image mismatch"))
               (check-graph! repo (u/geti core "sourceGraph") "bootstrap C0 source drift: ")
               c0))
        _ (.mkdir out ** :parents true :exist_ok false)
        source (.joinpath repo "seed/x86_64-kx64-runner.kotoba")
        tracked (cond-> [receipt-path producer source (.joinpath repo "seed/float-cases.json") (.joinpath repo "seed/static-cases.json") this]
                  c0 (conj c0))
        before (atom (into {} (for [p tracked] [(str p) (pin-of p)])))
        _ (.write_bytes (.joinpath out "runner.kotoba") (.read_bytes source))
        env {"PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str out) "KEXE_STACK_BYTES" "8388608"}
        rows (python/list)
        run (fn [name args & {:keys [overrides expected] :or {expected 0}}]
              (let [p (u/run-process args (python/dict (merge env overrides)) 900 :cwd out)]
                (.write_bytes (.joinpath out (str name ".stdout")) (.-stdout p))
                (.write_bytes (.joinpath out (str name ".stderr")) (.-stderr p))
                (when (and (some? expected) (or (not= expected (.-returncode p)) (u/nonempty? (.-stderr p))))
                  (throw (python/RuntimeError (str [name (.-returncode p) (u/bslice (.-stderr p) -500 nil)]))))
                (.append rows (u/pydict "name" name "exit" (.-returncode p) "stdout" (pin-of (.joinpath out (str name ".stdout")))
                                        "stderr" (pin-of (.joinpath out (str name ".stderr")))))
                p))
        runner (.joinpath out "runner.elf")
        _ (run "runner-compile" [producer "compile" (.joinpath out "runner.kotoba") "--target" "aarch64-linux" "--output" runner "--format" "runner"])
        _ (.chmod runner 0700)
        _ (when-not (u/deq (pin-of runner) (u/geti (u/geti receipt "built") "aarch64Runner")) (fail "fresh runner differs from bootstrap runner pin"))
        compile-payload (fn [name body & [compiler]]
                          (let [compiler (or compiler producer)
                                source-file (.joinpath out (str name ".kotoba"))]
                            (.write_text source-file body)
                            (let [container (.joinpath out (str name ".kseed")) raw (.joinpath out (str name ".bin"))]
                              (run (str name "-compile") [compiler "compile" source-file "--target" "aarch64-macos" "--output" container])
                              (run (str name "-extract") [compiler "extract-native" container "--symbol" "main" "--output" raw])
                              raw)))
        execute (fn [name payload fuel]
                  (run name [runner payload "0" "0" "aarch64" "35,37,38,39" "--"]
                       :overrides {"KEXE_COMMAND" "1" "KEXE_STRUCTURED_REPORT" "1" "KEXE_FUEL" (str fuel) "KEXE_ALLOW" "-"} :expected nil))]
    {:repo repo :boot boot :out out :receipt-path receipt-path :receipt receipt :producer producer :c0 c0 :source source
     :tracked tracked :before before :rows rows :run run :runner runner :compile-payload compile-payload :execute execute}))

(defn producers
  "[[\"F\" producer]] plus [\"C0\" c0] in the full tier."
  [{:keys [producer c0]}]
  (cond-> [["F" producer]] c0 (conj ["C0" c0])))

(defn unchanged-inputs? [{:keys [tracked before]}]
  (every? #(u/deq (pin-of %) (get @before (str %))) tracked))
