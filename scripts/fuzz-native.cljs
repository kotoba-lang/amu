#!/usr/bin/env nbb
(ns kotoba-native-fuzz
  (:require [clojure.string :as str]
            [cljs.reader :as reader]
            [scripts.lib :as lib]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def tmp (lib/temp-dir "kotoba-native-fuzz-"))
(def corpus (lib/join tmp "corpus"))
(def source-corpus (lib/join lib/root "fuzz" "corpus" "parser"))
(def output-dir (aget js/process.env "KOTOBA_FUZZ_ARTIFACT_DIR"))
(def import-dir (aget js/process.env "KOTOBA_FUZZ_IMPORT_DIR"))
(def runs (or (aget js/process.env "KOTOBA_NATIVE_FUZZ_RUNS") "20000"))
(def seed (or (aget js/process.env "KOTOBA_NATIVE_FUZZ_SEED") "424242"))
(defn exit! [message]
  (.error js/console message)
  (.exit js/process 2))
(defn entries [directory]
  (if (and directory (.existsSync fs directory))
    (map #(lib/join directory %) (.readdirSync fs directory)) []))

(defn import-corpus! []
  (when import-dir
    (loop [remaining (entries import-dir) count 0 total 0]
      (when-let [candidate (first remaining)]
        (let [stat (.lstatSync fs candidate)
              name (.basename path candidate)
              committed (lib/join source-corpus name)]
          (when-not (and (.isFile stat) (not (.isSymbolicLink stat)))
            (exit! "native-fuzz: imported corpus contains a non-regular file"))
          (let [legacy? (not (boolean (re-matches #"[0-9a-f]{40}|[0-9a-f]{64}" name)))]
            (if legacy?
              (do
                (when-not (and (.existsSync fs committed)
                               (.equals (.readFileSync fs candidate) (.readFileSync fs committed)))
                  (exit! (str "native-fuzz: unsafe corpus name: " name)))
                (recur (next remaining) count total))
              (let [size (.-size stat)
                    next-count (inc count)
                    next-total (+ total size)]
                (when (> size 1024) (exit! "native-fuzz: corpus input exceeds 1024 bytes"))
                (when (or (> next-count 10000) (> next-total 1048576))
                  (exit! "native-fuzz: imported corpus exceeds review limits"))
                (.copyFileSync fs candidate (lib/join corpus name))
                (recur (next remaining) next-count next-total)))))))))

;; The fuzz target prints one reach line at exit, counting how many inputs
;; actually arrived inside each family it claims to test. A target that never
;; reaches the function it names answers "no defect" for the same reason a
;; check with no input does, and is indistinguishable from the outside -- which
;; is not hypothetical here: the first draft drew the result handle as a raw
;; 64-bit word, landed inside the 32-entry pair table roughly never, and a
;; deliberately broken `inspect_string_result` survived all 20,000 cases.
;;
;; The floor is presence and non-zero, not a tuned threshold: a number invented
;; without a measurement would be the same failure in a new place.
(def reach-keys
  [:inputs :ops-completed :ops-trapped :string-bytes-read :dataspace-calls
   :string-result :record-result :tagged-result :variant-result :string-handle])

(defn reach! [log]
  (let [line (last (filter #(.includes % ":kotoba.fuzz-reach/v1") (str/split-lines log)))]
    (when-not line (throw (js/Error. "native-fuzz: target emitted no reach line")))
    (let [reach (reader/read-string (str/trim line))]
      (lib/ensure! (= :kotoba.fuzz-reach/v1 (:format reach))
                   "native-fuzz: reach line is not :kotoba.fuzz-reach/v1")
      (lib/ensure! (= (set reach-keys) (disj (set (keys reach)) :format))
                   "native-fuzz: reach line does not carry every counter")
      (doseq [k reach-keys]
        (lib/ensure! (and (integer? (get reach k)) (pos? (get reach k)))
                     (str "native-fuzz: nothing reached " k
                          " -- refusing to report a pass over an unexercised target")))
      (str "{" (str/join " " (map #(str % " " (get reach %)) reach-keys)) "}"))))

;; The compiler goes in the summary because a sanitizer verdict is a property of
;; the toolchain as much as of the code. Measured 2026-08-19: an `applying zero
;; offset to null pointer` report appeared on fleet node simeon (Apple clang 17)
;; and not on the authoring workstation (Apple clang 21), because C23 made
;; `NULL + 0` well defined. The gate was green here and red there with the same
;; source, the same seed and the same 20,000 inputs. A receipt that does not say
;; which compiler judged cannot be compared with one from another node.
(defn compiler-id []
  (let [{:keys [stdout stderr]} (lib/run "clang" ["--version"] {:allow-failure? true})
        line (first (str/split-lines (str (or stdout "") (or stderr ""))))]
    (if (str/blank? line) "unknown" (str/trim line))))

(defn number-field [text pattern label]
  (let [[_ value] (re-find pattern text)]
    (when-not value (throw (js/Error. (str "native-fuzz: missing " label))))
    (js/parseInt value 10)))

(defn linux-fuzz! [binary artifact-prefix]
  (lib/run "clang" ["-std=c11" "-O1" "-g" "-Wall" "-Wextra"
                    "-fsanitize=fuzzer,address,undefined" "-fno-omit-frame-pointer"
                    (str "-I" (lib/join lib/root "tools"))
                    (lib/join lib/root "tools" "kexe_parser_fuzz.c") "-o" binary])
  (let [seconds (aget js/process.env "KOTOBA_NATIVE_FUZZ_SECONDS")
        limit (if seconds (str "-max_total_time=" seconds) (str "-runs=" runs))
        label (if seconds (str seconds "s") runs)
        result (lib/run binary [corpus limit "-max_len=1024" "-timeout=2"
                                (str "-seed=" seed) (str "-artifact_prefix=" artifact-prefix)
                                "-print_final_stats=1" "-verbosity=1"]
                        {:env {:ASAN_OPTIONS "detect_leaks=0:abort_on_error=1"
                               :UBSAN_OPTIONS "halt_on_error=1:print_stacktrace=1"}
                         :allow-failure? true :max-buffer (* 16 1024 1024)})
        log (str (:stdout result) (:stderr result))]
    (when-not (= 0 (:status result))
      ;; amu#784: print the captured exit/signal so a silent child death is
      ;; attributable (signal=SIGKILL = external kill/OOM, signal=SIGSEGV =
      ;; unhandled fault, exit=N = the child failed on its own).
      (throw (js/Error. (str "native-fuzz: target " (lib/describe-exit result)
                             "\n" log))))
    (let [done (last (filter #(.includes % "cov:") (str/split-lines log)))
          cov (number-field done #"cov: ([0-9]+)" "coverage")
          features (number-field done #"ft: ([0-9]+)" "features")
          corpus-count (number-field done #"corp: ([0-9]+)/" "corpus")
          baseline (reader/read-string
                    (lib/read-text (lib/join lib/root "fuzz" "baselines" "native-parser.edn")))
          architecture (keyword (.-arch js/process))
          profile (get-in baseline [:profiles architecture])
          _ (lib/ensure! (and (= :kotoba.fuzz-baseline/v2 (:format baseline))
                              (= #{:format :loader-source-sha256 :profiles} (set (keys baseline)))
                              (= #{:x64 :arm64} (set (keys (:profiles baseline))))
                              (= #{:min-cov :min-features :min-corpus} (set (keys profile)))
                              (every? #(and (integer? %) (pos? %)) (vals profile)))
                         "native-fuzz: architecture baseline rejected")
          {:keys [min-cov min-features min-corpus]} profile
          expected (:loader-source-sha256 baseline)
          actual (lib/sha256 (lib/join lib/root "tools" "kexe_loader.c"))]
      (lib/ensure! (= expected actual) "native-fuzz: coverage baseline does not match loader source")
      (lib/ensure! (and (>= cov min-cov) (>= features min-features)
                        (>= corpus-count min-corpus))
                   (str "native-fuzz: coverage regression: cov=" cov "/" min-cov
                        " features=" features "/" min-features
                        " corpus=" corpus-count "/" min-corpus))
      [(str "{:format :kotoba.fuzz-coverage/v1 :engine :libfuzzer :arch " architecture
            " :seed " seed
            " :cov " cov " :features " features " :corpus " corpus-count
            " :reach " (reach! log)
            " :compiler \"" (compiler-id) "\""
            " :limit \"" label "\"}") label "coverage-guided"])))

(defn macos-fuzz! [binary]
  (lib/run "clang" ["-std=c11" "-O1" "-g" "-Wall" "-Wextra" "-DKEXE_STANDALONE_FUZZ"
                    "-fsanitize=address,undefined" "-fno-omit-frame-pointer"
                    (str "-I" (lib/join lib/root "tools"))
                    (lib/join lib/root "tools" "kexe_parser_fuzz.c") "-o" binary])
  (let [result (lib/run binary (into [runs] (entries corpus))
                        {:env {:ASAN_OPTIONS "detect_leaks=0:abort_on_error=1"
                               :UBSAN_OPTIONS "halt_on_error=1:print_stacktrace=1"}
                         :max-buffer (* 16 1024 1024)})
        log (str (:stdout result) (:stderr result))]
    [(str "{:format :kotoba.fuzz-coverage/v1 :engine :deterministic-sanitized"
          " :cases " runs " :reach " (reach! log)
          " :compiler \"" (compiler-id) "\"}")
     runs "deterministic-sanitized"]))

(try
  (.mkdirSync fs corpus #js {:recursive true})
  (doseq [candidate (entries source-corpus)]
    (.copyFileSync fs candidate (lib/join corpus (.basename path candidate))))
  (import-corpus!)
  (when output-dir (.mkdirSync fs output-dir #js {:recursive true}))
  (let [binary (lib/join tmp "kexe-parser-fuzz")
        prefix (if output-dir (lib/join output-dir "crash-") (lib/join tmp "crash-"))
        [summary label mode] (if (= "linux" (.platform os))
                               (linux-fuzz! binary prefix) (macos-fuzz! binary))]
    (println summary)
    (when output-dir (lib/write-text! (lib/join output-dir "coverage.edn") (str summary "\n")))
    (println (str "native-fuzz: " label " " mode " parser fuzz passed")))
  (finally
    (when output-dir
      (.mkdirSync fs (lib/join output-dir "corpus") #js {:recursive true})
      (.cpSync fs corpus (lib/join output-dir "corpus") #js {:recursive true :force true}))
    (lib/remove-tree! tmp)))
