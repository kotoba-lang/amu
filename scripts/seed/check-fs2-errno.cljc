;; Inject real kernel errno in one native FS2 child, after observer setup.
;;
;; Basilisp stages input and checks process/FS observations. Only the Amu-produced image implements FS operations.
;; The BPF filter affects no container init, observer, service or unrelated process. No compiler or host language
;; oracle.
;; Ported from check-fs2-errno.py (Basilisp). Linux only. Run:
;;   basilisp run scripts/seed/check-fs2-errno.cljc -- --image IMG --output OUT --case CASE
(ns check-fs2-errno
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import ctypes hashlib json operator os pathlib platform signal sys time))

(def cases
  {"write-eio" [64 1 5 126 13]
   "fsync-eio" [82 74 5 126 13]
   "chmod-eperm" [52 91 1 126 13]
   "unlink-eacces" [35 263 13 1 nil]
   "fstat-eio" [80 5 5 126 11]
   "entropy-enosys" [278 318 38 126 10]
   "rename-enosys" [276 316 38 126 3]
   "open-enosys" [437 437 38 126 3]})

(defn- struct-type [name fields]
  (python/type name (python/tuple [ctypes/Structure]) (python/dict {"_fields_" (python/list (map python/tuple fields))})))

(defn main [image out case]
  (let [machine (platform/machine)
        _ (u/chk (and (= "Linux" (platform/system)) (contains? #{"aarch64" "arm64" "x86_64"} machine)))
        arm (contains? #{"aarch64" "arm64"} machine)
        [arm-nr x86-nr error expected stage] (get cases case)
        number (if arm arm-nr x86-nr)
        _ (.mkdir out ** :parents true :exist_ok false)
        scope (.joinpath out "scope")
        _ (.mkdir scope)
        _ (.write_bytes (.joinpath scope "sentinel") (.encode "unowned-preserve"))
        libc (ctypes/CDLL nil ** :use_errno true)
        _ (set! (.-restype (.-prctl libc)) ctypes/c_long)
        _ (set! (.-restype (.-syscall libc)) ctypes/c_long)
        Instruction (struct-type "Instruction" [["code" ctypes/c_uint16] ["jt" ctypes/c_uint8] ["jf" ctypes/c_uint8] ["k" ctypes/c_uint32]])
        Program (struct-type "Program" [["length" ctypes/c_uint16] ["instructions" ctypes/c_void_p]])
        ;; Check the native audit architecture, load syscall number, then deny exactly this syscall. write only
        ;; targets fd >=3; diagnostics remain.
        instructions (vec (concat [[0x20 0 0 4] [0x15 1 0 (if arm 0xC00000B7 0xC000003E)] [0x06 0 0 0x80000000]
                                   [0x20 0 0 0] [0x15 0 (if (= case "write-eio") 3 1) number]]
                                  (when (= case "write-eio") [[0x20 0 0 16] [0x35 0 1 3]])
                                  [[0x06 0 0 (bit-or 0x00050000 error)] [0x06 0 0 0x7FFF0000]]))
        data ((operator/mul Instruction (count instructions)))
        _ (doseq [[i ins] (map-indexed vector instructions)] (operator/setitem data i (apply Instruction ins)))
        program (Program (count instructions) (ctypes/addressof data))
        _ (.write_text (.joinpath out "filter.json")
                       (u/json-dump (u/pydict "architecture" machine "syscall" number "errno" error
                                              "instructions" (python/list (map python/list instructions)))))
        pid (os/fork)]
    (when (zero? pid)
      ;; child: install the filter, then exec the native guest; never fall back into the observer's flow
      (try
        (let [stdout (os/open (.joinpath out "guest.stdout") (bit-or os/O_CREAT os/O_WRONLY) 0600)
              stderr (os/open (.joinpath out "guest.stderr") (bit-or os/O_CREAT os/O_WRONLY) 0600)]
          (os/dup2 stdout 1)
          (os/dup2 stderr 2)
          (os/close stdout)
          (os/close stderr)
          (u/chk (zero? (.prctl libc (ctypes/c_long 38) (ctypes/c_long 1) (ctypes/c_long 0) (ctypes/c_long 0) (ctypes/c_long 0))))
          (u/chk (zero? (.syscall libc (ctypes/c_long (if arm 277 317)) (ctypes/c_long 1) (ctypes/c_long 0) (ctypes/byref program))))
          (let [mode (if (= case "rename-enosys") "managed-publish-exclusive" "managed-return")]
            (os/execve image (python/list [(str image) mode (str scope)])
                       (python/dict {"PATH" "/nonexistent" "KEXE_ALLOW" "35,37,38,39" "KEXE_CAP_RESOURCES_35" (str scope) "KEXE_STACK_BYTES" "8388608"}))))
        (catch python/BaseException _ (os/_exit 127))))
    (let [deadline (+ (time/monotonic) 30)
          status (loop []
                   (let [[done status] (vec (os/waitpid pid os/WNOHANG))]
                     (cond
                       (not (zero? done)) status
                       (>= (time/monotonic) deadline)
                       (do (os/kill pid signal/SIGKILL) (os/waitpid pid 0) (throw (python/AssertionError "native errno guest deadline")))
                       :else (do (time/sleep 0.005) (recur)))))
          code (os/waitstatus_to_exitcode status)
          stdout (.read_bytes (.joinpath out "guest.stdout"))
          stderr (.read_bytes (.joinpath out "guest.stderr"))
          remaining (vec (sort (map #(str (.relative_to % scope)) (python/list (.rglob scope "*")))))]
      (.write_text (.joinpath out "observations.json")
                   (u/json-dump (u/pydict "exit" code "remaining" (python/list remaining) "stdout" (.decode stdout ** :errors "replace")
                                          "stderr" (.decode stderr ** :errors "replace"))))
      (u/chk (and (= expected code) (not (u/nonempty? stdout)) (= (.encode "unowned-preserve") (.read_bytes (.joinpath scope "sentinel")))))
      (when stage (u/chk (u/has-bytes? (.encode (str ":stage " stage "}")) stderr)))
      (let [incomplete (contains? #{"unlink-eacces" "fstat-eio"} case)]
        (u/chk (= (u/has-bytes? (.encode "KEXE_CLEANUP {:incomplete}") stderr) incomplete))
        (cond
          (= case "unlink-eacces")
          (let [directory (pathlib/Path (.read_text (.joinpath scope "ready")))]
            (u/chk (and (= scope (.-parent directory)) (str/starts-with? (.-name directory) "kotoba-output-")))
            (u/chk (= (.encode "preserved") (.read_bytes (.joinpath directory "0.tmp"))))
            (u/chk (= remaining (vec (sort [(.-name directory) (str (.-name directory) "/0.tmp") "ready" "sentinel"])))))
          (= case "fstat-eio")
          (let [dirs (vec (python/list (.glob scope "kotoba-output-*")))]
            (u/chk (and (= 1 (count dirs)) (.is_dir (first dirs)) (empty? (python/list (.iterdir (first dirs))))))
            (u/chk (= remaining (vec (sort [(.-name (first dirs)) "sentinel"])))))
          :else
          (u/chk (= remaining (if (= case "rename-enosys") ["ready" "sentinel"] ["sentinel"]))))
        (u/chk (not (.exists (.joinpath scope "published"))))
        (let [report (u/pydict "status" "PASS_NATIVE_FS2_KERNEL_ERRNO" "case" case "host" (python/list [(platform/system) machine])
                               "image" (u/pydict "bytes" (.-st_size (.stat image)) "sha256" (u/sha256-hex (.read_bytes image)))
                               "syscall" number "kernelErrno" error "exit" code "incompleteCleanupExpected" incomplete
                               "unownedSentinelPreserved" true "noPublishedTarget" true "nativeGuestUnmodified" true
                               "legacyRuntimeFallback" false "allFaultRaceParityQualified" false)]
          (.write_text (.joinpath out "receipt.json") (u/json-dump report))
          (println (u/geti report "status") case))))))

(defn -main [& args]
  (let [case (or (u/opt args "--case") (sys/exit "--case is required"))]
    (when-not (contains? cases case) (sys/exit (str "invalid --case: " case)))
    (main (.resolve (pathlib/Path (or (u/opt args "--image") (sys/exit "--image is required"))))
          (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
          case)))

(when (some #(or (= % "check-fs2-errno.cljc") (str/ends-with? % "/check-fs2-errno.cljc")) sys/argv)
  (apply -main *command-line-args*))
