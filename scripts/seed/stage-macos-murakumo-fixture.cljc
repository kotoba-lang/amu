;; Stage the same native packager and CLI with a synthetic registration.
;; The bearer is present only in the invoking test process and its FD4 pipe.
(ns stage-macos-murakumo-fixture
  (:require [gate-util :as u] [macos-native-lib :as mac] [macos-cli-build :as build])
  (:import pathlib shutil sys))

(defn- stage [out port]
  (u/chk (mac/available?) "Darwin arm64 required")
  (u/chk (<= 1 port 65535) "expected a synthetic fixture port")
  (.mkdir out ** :mode 0700 :exist_ok false)
  (let [descriptor (u/read-json (.joinpath u/root "seed/bootstrap/aarch64-macos/cli.json"))
        copied (fn [key name]
                 (let [source (.joinpath u/root (u/geti (u/geti descriptor key) "path"))
                       dest (.joinpath out name)]
                   (shutil/copy2 source dest)
                   (u/chk (u/deq (mac/verify-macho dest) (build/pin-of descriptor key)))
                   dest))
        compiler (copied "compiler" "amu-full-root.macho")
        packager (copied "packager" "kotoba-packager-root.macho")
        unregistered (copied "image" "unregistered.macho")
        pins (build/cli-pins (u/geti (mac/pin compiler) "sha256") (u/geti (mac/pin packager) "sha256"))
        unity (build/cli-unity-bytes u/root (build/cli-core-names) pins)
        port-anchor (.encode "(defn- mm-port [] :i64 0)")
        auth-anchor (.encode "(defn- mm-credential [] :string \"\")")
        auth-body (.encode (str "(defn- mm-credential [] :string\n"
                     "  (let [observed (hc-err \"amu: synthetic QA credential lookup\\n\") r (hc-call 16 [])]\n"
                     "    (if (and (hc-ok? r) (= (vector-count r) 65)) (hc-text (hc-slice r 1 64)) \"\")))"))]
    (u/chk (and (= 1 (.count unity port-anchor)) (= 1 (.count unity auth-anchor))) "fixture lost its registration anchors")
    (build/native-image compiler packager out "amu-cli" "amu-cli-host"
      (.replace (.replace unity port-anchor (.encode (str "(defn- mm-port [] :i64 " port ")"))) auth-anchor auth-body))))

(when (some #(.endswith % "stage-macos-murakumo-fixture.cljc") sys/argv)
  (let [[out port] *command-line-args*]
    (stage (.resolve (pathlib/Path out)) (python/int port))))
