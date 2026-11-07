;; Observe native FS2 kernel boundaries; no host language/compiler oracle.
;;
;; The supplied image is seed/tests/fs2-product.kotoba compiled by Amu selfhost. ptrace affects only this
;; observer's child. Creation-window tests send a real signal after kernel creation, before the guest can update
;; its journal. The EINTR case lets close consume its real fd before changing only the return. Partial I/O tests
;; reduce the real kernel transfer count and let Kotoba's existing fixture assertions decide whether the
;; reconstructed bytes are right.
;; Ported from check-fs2-observed.py (Basilisp). Linux only. Run:
;;   basilisp run scripts/seed/check-fs2-observed.cljc -- --image IMG --output OUT --case CASE
(ns check-fs2-observed
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import ctypes json operator os pathlib platform signal sys time))

(def case-names
  (vec (concat ["close-consumed-eintr" "partial-read" "partial-write"]
               (for [window ["directory" "file"] sig ["sigint" "sigterm" "sigalrm" "sigxcpu"]] (str "journal-" window "-" sig)))))

(defn- fd-path [pid fd]
  (try (os/readlink (str "/proc/" pid "/fd/" fd))
       (catch python/FileNotFoundError _ "<closed>")))

(defn main [image out case]
  (let [machine (platform/machine)
        _ (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "arm64" "x86_64"} machine)))
        arm (contains? #{"aarch64" "arm64"} machine)
        [reg-count number result args] (if arm [34 8 0 [0 1 2 3 4 5]] [27 15 10 [14 13 12 7 9 8]])
        ids (if arm {:close 57 :mkdirat 34 :openat2 437 :read 63 :write 64} {:close 3 :mkdirat 258 :openat2 437 :read 0 :write 1})
        _ (.mkdir out ** :parents true :exist_ok false)
        scope (.joinpath out "scope")
        _ (.mkdir scope)
        _ (.write_bytes (.joinpath scope "sentinel") (.encode "unowned-preserve"))
        lib (ctypes/CDLL nil ** :use_errno true)
        _ (set! (.-restype (.-ptrace lib)) ctypes/c_long)
        IOV (python/type "IOV" (python/tuple [ctypes/Structure])
                         (python/dict {"_fields_" (python/list [(python/tuple ["base" ctypes/c_void_p]) (python/tuple ["length" ctypes/c_size_t])])}))
        trace (fn [request pid & [address data]]
                (ctypes/set_errno 0)
                (let [r (.ptrace lib (ctypes/c_uint request) (ctypes/c_uint pid) (ctypes/c_void_p (or address 0)) (ctypes/c_void_p (or data 0)))]
                  (when (= r -1)
                    (let [error (ctypes/get_errno)] (throw (python/OSError error (os/strerror error)))))
                  r))
        registers (fn [pid]
                    (let [r ((operator/mul ctypes/c_uint64 reg-count))
                          io (IOV (ctypes/addressof r) (ctypes/sizeof r))]
                      (trace 0x4204 pid 1 (ctypes/addressof io)) ; GETREGSET/NT_PRSTATUS
                      (u/chk (= (.-length io) (ctypes/sizeof r)))
                      r))
        write-registers (fn [pid r]
                          (let [io (IOV (ctypes/addressof r) (ctypes/sizeof r))]
                            (trace 0x4205 pid 1 (ctypes/addressof io))))
        journal (str/starts-with? case "journal-")
        [_ window signame] (when journal (vec (.split case "-" 2)))
        selected (when journal (python/getattr signal (.upper signame)))
        [mode path] (if journal
                      ["managed-return" scope]
                      (cond (= case "partial-read") ["raw" (.joinpath scope "data")]
                            (= case "partial-write") ["managed-publish-exclusive" scope]
                            :else ["managed-return" scope]))
        pid (os/fork)]
    (when (zero? pid)
      (try
        (let [stdout (os/open (.joinpath out "guest.stdout") (bit-or os/O_CREAT os/O_WRONLY) 0600)
              stderr (os/open (.joinpath out "guest.stderr") (bit-or os/O_CREAT os/O_WRONLY) 0600)]
          (os/dup2 stdout 1)
          (os/dup2 stderr 2)
          (os/close stdout)
          (os/close stderr)
          (trace 0 0) ; TRACEME, before exec of the native fixture
          (os/execve image (python/list [(str image) mode (str path)])
                     (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str scope) "KEXE_STACK_BYTES" "8388608"})))
        (catch python/BaseException _ (os/_exit 127))))
    (let [[_ status] (vec (os/waitpid pid 0))
          _ (u/chk (and (os/WIFSTOPPED status) (= (os/WSTOPSIG status) signal/SIGTRAP)))
          _ (trace 0x4200 pid 0 0x100001) ; TRACESYSGOOD | EXITKILL
          entering (atom true) pending (atom nil) injected (atom false) deliver (atom 0)
          events (python/list) closes (python/list)
          started (time/monotonic)
          reg (fn [r i] (operator/getitem r i))
          code
          (try
            (loop []
              (u/chk (< (- (time/monotonic) started) 30) "native observer deadline")
              (trace 24 pid 0 @deliver) ; SYSCALL
              (reset! deliver 0)
              (let [[_ status] (vec (os/waitpid pid 0))]
                (cond
                  (os/WIFEXITED status) (os/WEXITSTATUS status)
                  (os/WIFSIGNALED status) (- (os/WTERMSIG status))
                  :else
                  (let [sig (os/WSTOPSIG status)]
                    (cond
                      (= sig (bit-or signal/SIGTRAP 0x80))
                      (let [r (registers pid)]
                        (if @entering
                          (do
                            (reset! pending nil)
                            (when (= (reg r number) (:close ids))
                              (let [fd (reg r (first args))
                                    name (fd-path pid fd)]
                                (.append closes (u/pydict "fd" fd "path" name))
                                (when (and (= case "close-consumed-eintr") (not @injected)
                                           (str/starts-with? name (str scope "/kotoba-output-")) (str/ends-with? name "/0.tmp"))
                                  (reset! pending ["close" fd]))))
                            (when (and journal (= (reg r number) (:mkdirat ids)) (= window "directory"))
                              (reset! pending ["directory" 0]))
                            (when (and journal (= (reg r number) (:openat2 ids)) (= window "file"))
                              (reset! pending ["file" 0]))
                            (let [io-name (if (= case "partial-read") :read :write)]
                              (when (and (contains? #{"partial-read" "partial-write"} case) (not @injected) (= (reg r number) (get ids io-name)))
                                (let [name (fd-path pid (reg r (first args)))
                                      match (if (= case "partial-read")
                                              (= name (str (.joinpath scope "data")))
                                              (and (str/starts-with? name (str scope "/kotoba-output-")) (str/ends-with? name "/0.tmp")))]
                                  (when (and match (> (reg r (nth args 2)) 1))
                                    (let [original (reg r (nth args 2))]
                                      (operator/setitem r (nth args 2) (if (= case "partial-read") 1 4))
                                      (write-registers pid r)
                                      (reset! pending ["partial" (reg r (nth args 2))])
                                      (.append events (u/pydict "kernelTransferRequested" (reg r (nth args 2)) "originalRequested" original "path" name))))))))
                          (when (and (some? @pending) (not @injected))
                            (let [[kind detail] @pending]
                              (cond
                                (= kind "close")
                                (do (u/chk (and (zero? (reg r result)) (= "<closed>" (fd-path pid detail))) "real kernel close must consume fd")
                                    (operator/setitem r result (- (bit-shift-left 1 64) 4))
                                    (write-registers pid r)
                                    (.append events (u/pydict "realCloseConsumed" true "returnedErrno" "EINTR"))
                                    (reset! injected true))
                                (and (= kind "directory") (zero? (reg r result)))
                                (let [created (vec (python/list (.glob scope "kotoba-output-*")))]
                                  (when (= 1 (count created))
                                    (os/kill pid selected)
                                    (.append events (u/pydict "kernelCreated" (str (first created)) "signal" (.upper signame)))
                                    (reset! injected true)))
                                (and (= kind "file") (< (reg r result) (bit-shift-left 1 63)))
                                (let [name (fd-path pid (reg r result))]
                                  (when (and (str/starts-with? name (str scope "/kotoba-output-")) (str/ends-with? name "/0.tmp"))
                                    (os/kill pid selected)
                                    (.append events (u/pydict "kernelCreated" name "signal" (.upper signame)))
                                    (reset! injected true)))
                                (= kind "partial")
                                (do (u/chk (= (reg r result) detail) "kernel must perform the shortened transfer")
                                    (.append events (u/pydict "kernelTransferred" detail))
                                    (reset! injected true))))
                            (reset! pending nil)))
                        (swap! entering not)
                        (recur))
                      (not= sig signal/SIGTRAP)
                      (do (reset! deliver sig) (recur))
                      :else (recur)))))) 
            (catch python/BaseException e
              (os/kill pid signal/SIGKILL)
              (os/waitpid pid 0)
              (throw e)))
          stdout (.read_bytes (.joinpath out "guest.stdout"))
          stderr (.read_bytes (.joinpath out "guest.stderr"))
          remaining (vec (sort (map #(str (.relative_to % scope)) (python/list (.rglob scope "*")))))]
      (.write_text (.joinpath out "observations.json")
                   (u/json-dump (u/pydict "case" case "exit" code "injected" @injected "events" events "closes" closes
                                          "remaining" (python/list remaining) "stdout" (.decode stdout ** :errors "replace")
                                          "stderr" (.decode stderr ** :errors "replace"))))
      (u/chk (and @injected (not (u/nonempty? stdout)) (= (.encode "unowned-preserve") (.read_bytes (.joinpath scope "sentinel")))))
      (cond
        journal
        (do (u/chk (and (= 120 code) (u/has-bytes? (.encode (str ":signal :" (.upper signame))) stderr)
                        (not (u/has-bytes? (.encode "KEXE_CLEANUP") stderr))))
            (u/chk (= ["sentinel"] remaining)))
        (= case "close-consumed-eintr")
        (do (u/chk (and (= 126 code) (u/has-bytes? (.encode ":stage 13}") stderr) (not (u/has-bytes? (.encode "KEXE_CLEANUP") stderr))))
            (u/chk (and (= ["sentinel"] remaining)
                        (= 1 (count (filter #(str/ends-with? (u/geti % "path") "/0.tmp") closes))))))
        :else
        (do (u/chk (and (zero? code) (not (u/nonempty? stderr))))
            (if (= case "partial-read")
              (u/chk (and (= ["data" "sentinel"] remaining) (= (u/bytes-of 0 255 128) (.read_bytes (.joinpath scope "data")))))
              (u/chk (and (= ["published" "ready" "sentinel"] remaining) (= (.encode "preserved") (.read_bytes (.joinpath scope "published"))))))))
      (let [report (u/pydict "status" "PASS_NATIVE_FS2_OBSERVED_BOUNDARY" "case" case "host" (python/list [(platform/system) machine])
                             "image" (u/pydict "bytes" (.-st_size (.stat image)) "sha256" (u/sha256-hex (.read_bytes image)))
                             "exit" code "kernelBoundaryObserved" true "nativeGuestUnmodified" true "events" events
                             "ownedStageRemoved" true "unownedSentinelPreserved" true "legacyRuntimeFallback" false
                             "allFaultRaceParityQualified" false)]
        (.write_text (.joinpath out "receipt.json") (u/json-dump report))
        (println (u/geti report "status") case)))))

(defn -main [& args]
  (let [case (or (u/opt args "--case") (sys/exit "--case is required"))]
    (when-not (contains? (set case-names) case) (sys/exit (str "invalid --case: " case)))
    (main (.resolve (pathlib/Path (or (u/opt args "--image") (sys/exit "--image is required"))))
          (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
          case)))

(when (some #(or (= % "check-fs2-observed.cljc") (str/ends-with? % "/check-fs2-observed.cljc")) sys/argv)
  (apply -main *command-line-args*))
