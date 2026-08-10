(ns kotoba.compiler.nbb.cli-support
  "Shared, backend-free support for the split nbb compiler entrypoints.

  Keeping policy decoding and the CLI error contract here is important: the
  Wasm/native split may reduce namespace load time, but must not create two
  subtly different admission boundaries."
  (:require ["node:path" :as node-path]
            ["node:perf_hooks" :refer [performance]]
            [kotoba.compiler.diagnostic :as diagnostic]
            [kotoba.compiler.kotoba-reader :as kr]
            [kotoba.compiler.nbb.io :as io]
            [kotoba.compiler.source-path :as source-path]))

;; Opt-in phase timings go to stderr behind a stable marker. Normal stdout and
;; artifact bytes remain unchanged.
(def ^:private timing-enabled?
  (= "1" (aget js/process.env "KOTOBA_COMPILER_TIMING")))
(def ^:private timing-origin-ms (volatile! (.now performance)))
(def ^:private timing-phases (volatile! []))

(defn- reset-timing! []
  (vreset! timing-origin-ms (.now performance))
  (vreset! timing-phases []))

(defn timed [phase f]
  (if-not timing-enabled?
    (f)
    (let [started (.now performance)]
      (try
        (f)
        (finally
          (vswap! timing-phases conj
                  {:phase phase :milliseconds (- (.now performance) started)}))))))

(defn- timing-report []
  (when timing-enabled?
    {:format "kotoba.compiler-timing/v1"
     :totalMilliseconds (- (.now performance) @timing-origin-ms)
     :phases @timing-phases}))

(defn- emit-timing! [report]
  (when report
    (.error js/console
            (str "KOTOBA_TIMING " (.stringify js/JSON (clj->js report))))))

(defn option [args flag] (second (drop-while #(not= flag %) args)))

(defn usage-error! [message]
  (throw (ex-info message {:phase :usage})))

(defn source! [path] (source-path/admit! path))

;; These bounds mirror `kotoba.compiler.bounded-edn`. Policy files are the one
;; untrusted-ish EDN side channel on this fast path; source has its own reader
;; and admission contract.
(def ^:private max-policy-depth 128)
(def ^:private max-policy-token-chars 4096)
(def ^:private max-policy-nodes 200000)
(def ^:private max-policy-string-chars (* 1024 1024))

(defn- validate-edn-shape! [value]
  (let [nodes (volatile! 0)]
    (letfn [(walk [x]
              (when (> (vswap! nodes inc) max-policy-nodes)
                (throw (ex-info "EDN value contains too many nodes"
                                {:phase :decode :limit max-policy-nodes})))
              (when (and (string? x) (> (count x) max-policy-string-chars))
                (throw (ex-info "EDN string exceeds limit"
                                {:phase :decode :limit max-policy-string-chars})))
              (cond
                (map? x) (doseq [[k v] x] (walk k) (walk v))
                (coll? x) (doseq [item x] (walk item))))]
      (walk value)
      value)))

(defn- read-edn-form! [text]
  (let [forms (kr/read-forms text {:max-depth max-policy-depth
                                   :max-token-chars max-policy-token-chars})]
    (when (empty? forms)
      (throw (ex-info "EDN input is empty" {:phase :decode})))
    (when (> (count forms) 1)
      (throw (ex-info "EDN input contains trailing forms" {:phase :decode})))
    (validate-edn-shape! (first forms))))

(defn read-policy-material [args]
  (if-let [path (option args "--policy")]
    {:present? true :text (io/read-text-file path)}
    {:present? false :text ""}))

(defn parse-policy-material [material]
  (if (:present? material)
    (read-edn-form! (:text material))
    {}))

(defn read-policy [args]
  (parse-policy-material (read-policy-material args)))

(defn- exit-code [phase]
  (case phase
    :usage 64
    (:decode :read :subset :admission :verify) 65
    :output 74
    70))

(defn- error-report [error source-name]
  (let [data (ex-data error)
        phase (or (:phase data) :internal)]
    {:format :kotoba.cli-error/v1
     :ok false
     :error phase
     :diagnostic (diagnostic/from-error error source-name)
     :message (if (= phase :internal) "internal compiler error" (.-message error))}))

(defn- invoke* [run! args reset?]
  (when reset? (reset-timing!))
  (try
    (let [value (timed "command" #(run! (vec args)))]
      {:status 0
       :stdout (str (pr-str value) "\n")
       :stderr ""
       :timing (timing-report)})
    (catch :default error
      (let [source (second args)
            source-name (when (source-path/source-kind source)
                          (.basename node-path source))
            report (error-report error source-name)]
        {:status (exit-code (:error report))
         :stdout ""
         :stderr (str (pr-str report) "\n")
         :timing (timing-report)}))))

(defn invoke
  "Runs one already-loaded compiler command without terminating the process."
  [run! args]
  (invoke* run! args true))

(defn execute! [run!]
  (let [{:keys [status stdout stderr timing]}
        (invoke* run! (vec *command-line-args*) false)]
    (emit-timing! timing)
    (when (seq stdout) (.write js/process.stdout stdout))
    (when (seq stderr) (.write js/process.stderr stderr))
    (when-not (zero? status) (.exit js/process status))))

(def ^:private max-worker-line-bytes (* 64 1024))
(def ^:private max-worker-args 64)
(def ^:private max-worker-arg-chars 4096)

(defn- configured-max-requests []
  (let [text (or (aget js/process.env "KOTOBA_WORKER_MAX_REQUESTS") "1000")
        value (js/Number text)]
    (if (and (js/Number.isSafeInteger value) (<= 1 value 100000))
      value
      1000)))

(defn- write-worker-response! [response]
  (.write js/process.stdout
          (str (.stringify js/JSON (clj->js response)) "\n")))

(defn- request! [line]
  (when (> (.byteLength js/Buffer line "utf8") max-worker-line-bytes)
    (usage-error! "worker request exceeds byte limit"))
  (let [request (js->clj (.parse js/JSON line) :keywordize-keys true)
        args (:args request)]
    (when-not (map? request)
      (usage-error! "worker request must be a JSON object"))
    (when-not (or (nil? (:id request))
                  (string? (:id request))
                  (number? (:id request)))
      (usage-error! "worker request id must be a string, number, or null"))
    (when-not (and (vector? args)
                   (<= (count args) max-worker-args)
                   (every? #(and (string? %) (<= (count %) max-worker-arg-chars)) args))
      (usage-error! "worker args must be a bounded array of strings"))
    request))

(defn serve!
  "Serves bounded, sequential NDJSON requests until shutdown or the request
  ceiling. Each response contains the ordinary CLI stdout/stderr contract, so
  callers do not need a second error decoder."
  [run! target]
  (let [requests (volatile! 0)
        maximum (configured-max-requests)
        pending (volatile! (.alloc js/Buffer 0))
        closed? (volatile! false)
        close! (fn []
                 (when-not @closed?
                   (vreset! closed? true)
                   (.pause js/process.stdin)
                   (js/setImmediate #(.exit js/process 0))))
        handle-line!
        (fn [line]
          (let [count (vswap! requests inc)]
            (if (> count maximum)
              (do
                (write-worker-response! {:format "kotoba.compiler-worker/v1"
                                         :type "result" :id nil :status 64
                                         :stdout ""
                                         :stderr "worker request limit exceeded\n"})
                (close!))
              (try
                (let [request (request! line)
                      id (:id request)]
                  (if (= "shutdown" (:op request))
                    (do
                      (write-worker-response! {:format "kotoba.compiler-worker/v1"
                                               :type "shutdown" :id id :status 0})
                      (close!))
                    (let [result (invoke run! (:args request))]
                      (write-worker-response!
                       (assoc result :format "kotoba.compiler-worker/v1"
                                     :type "result" :id id))
                      ;; Recover from bounded caller errors, but fail-stop after
                      ;; an internal compiler failure that may have tainted state.
                      (when (= 70 (:status result)) (close!)))))
                (catch :default error
                  (write-worker-response! {:format "kotoba.compiler-worker/v1"
                                           :type "result" :id nil :status 64
                                           :stdout ""
                                           :stderr (str (.-message error) "\n")}))))))]
    (write-worker-response! {:format "kotoba.compiler-worker/v1"
                             :type "ready" :target (name target)
                             :maxRequests maximum})
    (.on js/process.stdin "data"
         (fn [chunk]
           (when-not @closed?
             (vreset! pending (.concat js/Buffer #js [@pending chunk]))
             (loop []
               (let [newline (.indexOf @pending 10)]
                 (if (neg? newline)
                   (when (> (.-length @pending) max-worker-line-bytes)
                     (write-worker-response! {:format "kotoba.compiler-worker/v1"
                                              :type "result" :id nil :status 64
                                              :stdout ""
                                              :stderr "worker request exceeds byte limit\n"})
                     (close!))
                   (let [line-buffer (.subarray @pending 0 newline)
                         line-buffer (if (and (pos? (.-length line-buffer))
                                              (= 13 (aget line-buffer
                                                          (dec (.-length line-buffer)))))
                                       (.subarray line-buffer 0 (dec (.-length line-buffer)))
                                       line-buffer)]
                     (vreset! pending (.subarray @pending (inc newline)))
                     (if (> (.-length line-buffer) max-worker-line-bytes)
                       (do
                         (write-worker-response! {:format "kotoba.compiler-worker/v1"
                                                  :type "result" :id nil :status 64
                                                  :stdout ""
                                                  :stderr "worker request exceeds byte limit\n"})
                         (close!))
                       (do
                         (handle-line! (.toString line-buffer "utf8"))
                         (when-not @closed? (recur)))))))))))
    (.on js/process.stdin "end"
         (fn []
           (when-not @closed?
             (when (pos? (.-length @pending))
               (write-worker-response! {:format "kotoba.compiler-worker/v1"
                                        :type "result" :id nil :status 64
                                        :stdout ""
                                        :stderr "unterminated worker request\n"}))
             (close!))))))
