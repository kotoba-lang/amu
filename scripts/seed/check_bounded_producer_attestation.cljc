;; Verify the experimental producer built by the main push workflow.
;;
;; This verifies artifact origin only. Source identity, resource proof and
;; production/shared-cache admission remain separate native qualifications.
;; Ported from check_bounded_producer_attestation.py (Basilisp).
;; Run: basilisp run scripts/seed/check_bounded_producer_attestation.cljc -- --artifact A --gh G
(ns check-bounded-producer-attestation
  (:require [basilisp.string :as str]
            [bounded-cache-bundle :as bundle]
            [sealed-image :as sealed]
            [verified-attestation :as attest])
  (:import os pathlib subprocess sys tempfile))

(def gh-sha256 "b768184570b12536be4ac1528893f6340d1c6a7b40b56ad45bca9cd0e87ad34d")
(def repo-id "1297097065")
(def workflow ".github/workflows/bounded-cache-producer.yml")
(def probe (str "{:format :kotoba.kir/v4 :entry main :exports [main] :effects #{} :functions ["
                "{:name helper :params [x] :param-types [:i64] :result :i64 :effects #{} "
                ":body (if (< x 0) 0 (+ x 2))} "
                "{:name main :params [] :param-types [] :result :i64 :effects #{} :body (helper 40)}]}\n"))

(defn exercise
  "Perform fresh admission/link and execute a bounded reused-object probe."
  [image objects image-digest root]
  (let [root (pathlib/Path root)
        source (.joinpath root "probe.kir") reference (.joinpath root "reference.elf") candidate (.joinpath root "candidate.elf")
        _ (.write_text source probe)
        env (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str root)
                          "KEXE_STACK_BYTES" "8388608" "KEXE_FUEL" "10000000000"})]
    (sealed/with-sealed-image image image-digest
      (fn [fd digest]
        (os/lseek fd 0 os/SEEK_SET)
        (when (not= (python/bytes [0x7f 0x45 0x4c 0x46]) (os/read fd 4))
          (throw (python/ValueError "attested candidate is not an ELF image")))
        (doseq [[mode output] [["reference" reference] ["cached" candidate]]]
          (let [proc (subprocess/run (python/list [(str "/proc/self/fd/" fd) mode (str source) (str objects) digest (str output) "1000000"])
                                     ** :env env :cwd root :pass_fds (python/tuple [fd]) :capture_output true :timeout 120 :check true)]
            (when (or (seq (.-stderr proc))
                      (and (= mode "cached")
                           (not= [(.encode "DCB1 reused=2 rebuilt=0")] (vec (take-last 1 (.splitlines (.-stdout proc)))))))
              (throw (python/ValueError "fresh candidate admission or expected object reuse failed")))))))
    (when (not= (.read_bytes reference) (.read_bytes candidate))
      (throw (python/ValueError "reused object differs from fresh output")))
    (.chmod candidate 0500)
    (let [proc (subprocess/run (python/list [(str candidate)]) ** :env (python/dict {"PATH" "/nonexistent"}) :cwd root
                               :capture_output true :timeout 30 :check true)]
      (when (or (seq (.-stderr proc)) (not= (.to_bytes 42 8 "little" ** :signed true) (.-stdout proc)))
        (throw (python/ValueError "fresh execution did not match the native oracle"))))))

(defn main [artifact gh]
  (let [env os/environ]
    (when (or (not= (.get env "GITHUB_REPOSITORY") "kotoba-lang/amu")
              (not= (.get env "GITHUB_REPOSITORY_ID") repo-id)
              (not= (.get env "GITHUB_REF") "refs/heads/main")
              (not= (.get env "GITHUB_EVENT_NAME") "push"))
      (throw (python/ValueError "producer verification requires the trusted main push context")))
    (let [source-sha (.get env "GITHUB_SHA" "")
          policy (attest/attestation-policy "kotoba-lang/amu" repo-id workflow "refs/heads/main" source-sha source-sha "push")]
      (with-open [temp (tempfile/TemporaryDirectory ** :prefix "bounded-cache-" :dir (.get env "RUNNER_TEMP"))]
        (let [root (pathlib/Path temp)
              [image objects image-digest bundle-digest] (bundle/verified-extract artifact gh gh-sha256 policy (.joinpath root "bundle"))]
          (exercise image objects image-digest root)
          (println "PASS_ATTESTED_BOUNDED_PRODUCER_AND_FRESH_PROBE" bundle-digest)
          (.flush sys/stdout))))))

(defn- opt [args k] (second (drop-while #(not= % k) args)))

(defn -main [& args]
  (main (or (opt args "--artifact") (sys/exit "--artifact is required"))
        (or (opt args "--gh") (sys/exit "--gh is required"))))

(when (some #(or (= % "check_bounded_producer_attestation.cljc") (str/ends-with? % "/check_bounded_producer_attestation.cljc")) sys/argv)
  (apply -main *command-line-args*))
