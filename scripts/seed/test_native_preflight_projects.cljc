;; Preflight process ordering/failure controls; no native qualification.
;; Ported from test_native_preflight_projects.py. Run: basilisp test scripts/seed
(ns test-native-preflight-projects
  (:require [basilisp.test :refer [deftest is testing]]
            [native-preflight-projects :as P])
  (:import json pathlib subprocess tempfile))

(def root-file P/root-file)

(deftest original-project-then-fs-argv-are-preserved
  (let [compiler (root-file "bin/amu-linux-x86_64")
        calls (atom [])]
    (with-open [d (tempfile/TemporaryDirectory)]
      (let [temporary (pathlib/Path d)
            image (-> (P/path (root-file "native-product.json")) .read-text json/loads (get "image") (get "sha256"))]
        (with-redefs [P/run-process (fn [argv] (swap! calls conj (vec argv)) nil)]
          (P/main compiler temporary))
        (is (= [["basilisp" "run" "-p" (root-file "scripts/seed") (root-file "scripts/seed/check-x86-project-native.cljc") "--"
                 "--compiler" compiler "--output" (str (.joinpath temporary "local-native-project"))]
                ["python3" (root-file "scripts/seed/check-x86-project-fs-native.py")
                 "--compiler" compiler "--compiler-sha256" image
                 "--runner" (str (.joinpath temporary "local-native-project/runner.elf"))
                 "--output" (str (.joinpath temporary "project-fs-candidate")) "--derive"]]
               @calls))))))

(deftest project-refusal-stops-its-dependent-fs-candidate
  (let [n (atom 0)]
    (with-redefs [P/run-process (fn [_] (swap! n inc) (throw (subprocess/CalledProcessError 7 ["project"])))]
      (is (thrown? subprocess/CalledProcessError (P/main (root-file "bin/amu-linux-x86_64") "/unused")))
      (is (= 1 @n)))))

(deftest fs-refusal-is-not-a-successful-preflight
  (let [n (atom 0)]
    (with-redefs [P/run-process (fn [_] (when (= 2 (swap! n inc))
                                          (throw (subprocess/CalledProcessError 9 ["fs"]))))]
      (is (thrown? subprocess/CalledProcessError (P/main (root-file "bin/amu-linux-x86_64") "/unused")))
      (is (= 2 @n)))))

(deftest preflight-plan-keeps-all-independent-controls
  (let [plan (-> (P/path (root-file "seed/native-preflight-plan.json")) .read-text json/loads)
        gates (get-in plan ["phases" "preflight"])]
    (is (= "amu.native-gate-plan.v1" (get plan "schema")))
    (is (= ["local-project-fs" "early-kotoba" "b2-preflight"] (mapv #(get % "name") gates)))
    (is (= ["python3" "scripts/seed/check-native-kotoba-early.py"
            "--compiler" "bin/amu-linux-x86_64" "--output" "@TEMP@/early-kotoba"]
           (vec (get (nth gates 1) "argv"))))
    (is (= ["python3" "scripts/seed/check-b2-libc.py"
            "--compiler" "bin/amu-linux-x86_64" "--output" "@TEMP@/b2-libc-preflight"]
           (vec (get (nth gates 2) "argv"))))))
