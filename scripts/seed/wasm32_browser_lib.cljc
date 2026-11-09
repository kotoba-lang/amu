;; Headless-browser harness shared by the browser gates (JUN-974): the DevTools protocol over
;; --remote-debugging-pipe (fd 3 in, fd 4 out, NUL-separated JSON), result-line observation and the
;; probe tables. Ported from the helpers of check-wasm32-browser.py (Pipe, find_browser, observe,
;; PROBES, PROBE_RUNS); the consent-broker qualification stays in the Python original.
(ns wasm32-browser-lib
  (:require [gate-util :as u])
  (:import base64 json operator os pathlib re select shutil subprocess tempfile time))

(def fuel 1000000)
(def browsers ["chromium" "chromium-browser" "google-chrome" "google-chrome-stable"])

(defn find-browser [explicit]
  (let [names (concat (when explicit [explicit]) [(.get os/environ "KOTOBA_BROWSER")] browsers)]
    (some (fn [n] (when n (shutil/which n))) names)))

(defn open-pipe
  "Start the browser with the DevTools pipe; returns a state map. profile is a directory."
  [browser profile]
  (let [[to-r to-w] (os/pipe)
        [from-r from-w] (os/pipe)
        child-fds (fn []
                    ;; dup first: dup2 onto the same number would keep close-on-exec
                    (let [a (os/dup to-r) b (os/dup from-w)]
                      (os/dup2 a 3)
                      (os/dup2 b 4)))
        args (python/list [browser "--headless" "--disable-gpu" "--no-first-run" "--no-default-browser-check"
                           "--disable-extensions" "--disable-background-networking" "--disable-sync"
                           "--remote-debugging-pipe" (str "--user-data-dir=" profile) "about:blank"])
        _ (when (or (zero? (os/geteuid)) (= (.get os/environ "KOTOBA_BROWSER_NO_SANDBOX") "1"))
            (.insert args 1 "--no-sandbox"))
        log (python/open (pathlib/Path profile "browser.log") "w+b")
        proc (subprocess/Popen args ** :preexec_fn child-fds :close_fds false
                               :stdout subprocess/DEVNULL :stderr log)]
    (os/close to-r)
    (os/close from-w)
    {:proc proc :to-w to-w :from-r from-r :log log :state (atom {:buf (python/bytes) :next-id 0})}))

(defn stderr-tail [pipe]
  (let [log (:log pipe)]
    (.flush log)
    (.seek log 0)
    (let [t (.decode (.read log) "utf-8" "replace")]
      (subs t (max 0 (- (count t) 3000))))))

(defn- post [pipe method params session]
  (let [id (:next-id (swap! (:state pipe) update :next-id inc))
        msg (u/pydict "id" id "method" method "params" (or params (python/dict)))]
    (when session (operator/setitem msg "sessionId" session))
    (os/write (:to-w pipe) (operator/add (.encode (json/dumps msg)) (u/bytes-of 0)))
    id))

(defn send! [pipe method & [params session]] (post pipe method params session) nil)

(defn call
  "Send a command and wait for its reply (events are dropped)."
  [pipe method & [params session timeout]]
  (let [id (post pipe method params session)
        end (+ (time/time) (or timeout 60))]
    (loop []
      (if (< (time/time) end)
        (let [buf (:buf @(:state pipe))]
          (if (operator/contains buf (u/bytes-of 0))
            (let [[raw remainder] (.split buf (u/bytes-of 0) 1)
                  reply (json/loads raw)]
              (swap! (:state pipe) assoc :buf remainder)
              (if (and (operator/contains reply "id") (= (operator/getitem reply "id") id))
                (if (operator/contains reply "error")
                  (throw (python/RuntimeError (python/tuple [method (operator/getitem reply "error")])))
                  (operator/getitem reply "result"))
                (recur)))
            (if (empty? (operator/getitem (select/select [(:from-r pipe)] [] [] (max 0.0 (- end (time/time)))) 0))
              (throw (python/TimeoutError (python/tuple [method (stderr-tail pipe)])))
              (let [chunk (os/read (:from-r pipe) 65536)]
                (when (zero? (python/len chunk))
                  (throw (python/RuntimeError (python/tuple ["browser closed the pipe" (stderr-tail pipe)]))))
                (swap! (:state pipe) update :buf operator/add chunk)
                (recur)))))
        (throw (python/TimeoutError (python/tuple [method (stderr-tail pipe)])))))))

(defn close-pipe [pipe]
  (try (call pipe "Browser.close" nil nil 10) (catch python/Exception _ nil))
  (try (.wait (:proc pipe) ** :timeout 10)
       (catch subprocess/TimeoutExpired _ (.kill (:proc pipe)) (.wait (:proc pipe))))
  (os/close (:to-w pipe))
  (os/close (:from-r pipe)))

(defn run-page
  "Open page-dir/page-name in the browser and wait for title kotoba-done; returns [version results-text]."
  [browser page-dir page-name prefix timeout]
  (let [profile-dir (tempfile/TemporaryDirectory ** :prefix prefix)
        profile (.__enter__ profile-dir)]
    (try
      (let [pipe (open-pipe browser profile)]
        (try
          (let [version (call pipe "Browser.getVersion")
                target (operator/getitem (call pipe "Target.createTarget"
                                               (u/pydict "url" (.as_uri (pathlib/Path page-dir page-name)))) "targetId")
                session (operator/getitem (call pipe "Target.attachToTarget" (u/pydict "targetId" target "flatten" true)) "sessionId")
                end (+ (time/time) timeout)
                expr "document.title === 'kotoba-done' ? document.getElementById('results').textContent : null"]
            (loop []
              (let [r (call pipe "Runtime.evaluate" (u/pydict "expression" expr "returnByValue" true) session)
                    text (.get (.get r "result" (python/dict)) "value")]
                (cond (some? text) [version text]
                      (>= (time/time) end) (throw (python/TimeoutError "the page did not finish"))
                      :else (do (time/sleep 0.2) (recur))))))
          (finally (close-pipe pipe))))
      (finally (.__exit__ profile-dir nil nil nil)))))

(defn result-lines
  "{name -> parsed result line} from the page's results text."
  [text]
  (let [d (python/dict)]
    (doseq [l (.splitlines text)]
      (when (seq (.strip l))
        (let [m (json/loads l)] (operator/setitem d (operator/getitem m "name") m))))
    d))

(defn version-info [version]
  (u/pydict "product" (.get version "product") "protocol" (.get version "protocolVersion")))

(defn observe
  "The native report's fields from a result line (exit, status, result, remaining fuel)."
  [line]
  (let [stdout (or (.get line "stdout") "")
        f (re/search ":remaining ([0-9]+)" stdout)
        s (re/search ":status :([a-z]+)" stdout)
        r (re/search ":result (-?[0-9]+)" stdout)]
    (u/pydict "exit" (.get line "exit")
              "status" (when s (.group s 1))
              "result" (when r (python/int (.group r 1)))
              "remainingFuel" (when f (python/int (.group f 1))))))

(def entry-text "kotoba 言葉 entry\n")
(def probes
  "Ordered like the Python PROBES table."
  [["spin" {"exit" 120 "status" "trap" "remainingFuel" 0}]
   ["deep" {"exit" 120 "status" nil "remainingFuel" nil}]
   ["document" {"exit" 0 "status" "ok" "result" 2}]
   ["entry" {"exit" 0 "status" "ok" "result" (python/len (.encode entry-text "utf-8"))}]
   ["entry-denied" {"exit" 120 "status" "trap"}]])
(def probe-runs
  "Python-ordered extra inputs per probe."
  {"entry" [["entry" (u/pydict "allow" (python/list [35 37 38 39]) "args" (python/list ["/data/../data/in.txt"])
                               "files" (u/pydict "/data/in.txt" entry-text))]
            ["entry-denied" (u/pydict "args" (python/list ["/data/in.txt"]) "files" (u/pydict "/data/in.txt" entry-text))]]})

(defn sha256 [path] (u/sha256-hex (.read_bytes (pathlib/Path path))))
