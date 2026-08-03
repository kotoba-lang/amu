(ns test.nbb.classpath
  "Tests for the JVM-free dependency-closure resolver.

  Runs on nbb with `--classpath src` and nothing else -- no `clojure -Spath`,
  which is the property under test. Every case that must fail does so with a
  `:phase`, because the failure this replaces returned an empty classpath and
  surfaced later as a missing namespace from an unrelated file."
  (:require ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as node-path]
            [kotoba.compiler.nbb.classpath :as classpath]))

(def repo-root (.resolve node-path (.cwd js/process)))

(def failures (atom 0))

(defn- check [label ok?]
  (if ok?
    (println "PASS" label)
    (do (println "FAIL" label) (swap! failures inc))))

(defn- phase-of
  "Run BODY and return the `:phase` of the error it throws, or `:no-error`."
  [body]
  (try (body) :no-error
       (catch :default error (:phase (ex-data error) :no-phase))))

(defn- temp-dir [prefix]
  (.mkdtempSync fs (.join node-path (.tmpdir os) prefix)))

(defn- git! [dir args]
  (.spawnSync child "git" (clj->js args)
              #js {:cwd dir :encoding "utf8"}))

(defn- init-repo!
  "A real git repository with one commit, returning its sha. Cheap, offline,
  and enough to exercise both the fetch and the verification paths."
  [dir]
  (.mkdirSync fs dir #js {:recursive true})
  (git! dir ["init" "--quiet" "-b" "main"])
  (git! dir ["config" "user.email" "test@example.invalid"])
  (git! dir ["config" "user.name" "test"])
  (.mkdirSync fs (.join node-path dir "src") #js {:recursive true})
  (.writeFileSync fs (.join node-path dir "src" "marker.txt") "marker\n")
  (git! dir ["add" "-A"])
  (git! dir ["commit" "--quiet" "-m" "one"])
  (.trim (.-stdout (git! dir ["rev-parse" "HEAD"]))))

(defn- write-fixture!
  "A root with a `deps.edn` and a lock over it, with ENTRIES."
  [entries & {:keys [digest-override version]}]
  (let [root (temp-dir "kotoba-classpath-test-")
        deps "{:paths [\"src\"]}\n"]
    (.writeFileSync fs (.join node-path root "deps.edn") deps)
    (.writeFileSync fs (.join node-path root "deps-lock.edn")
                    (pr-str {:lock/version (or version classpath/lock-version)
                             :lock/deps-digest (or digest-override
                                                   (classpath/deps-digest root))
                             :lock/entries entries}))
    root))

;; --- the checked-in lock resolves, and its pins are what they claim --------
;;
;; This is the only group that needs the real dependency closure, which means
;; either a warm `~/.gitlibs` or reachable git remotes. `--hermetic-only`
;; excludes it for runners that have neither -- the murakumo fleet nodes are on
;; a tailnet with no route to github.com, which is why they cannot fetch and
;; why the flag exists.
;;
;; The flag names what it drops, out loud. A runner that silently skipped this
;; group would report the same "PASS jvm-free-classpath" as one that ran it.

(def hermetic-only? (boolean (some #{"--hermetic-only"} (vec *command-line-args*))))

(if hermetic-only?
  (do (println "SKIP the-checked-in-lock-resolves"
               "(--hermetic-only: needs the real dependency closure)")
      ;; The one thing still checkable without the closure: the lock must agree
      ;; with the deps.edn beside it. That is the failure this pair exists to
      ;; catch -- a pin moved and the lock was not regenerated.
      (check "the checked-in lock agrees with deps.edn"
             (= (classpath/deps-digest repo-root)
                (:lock/deps-digest (classpath/read-lock repo-root)))))
  (let [dirs (classpath/resolve-directories repo-root)]
    (check "checked-in lock resolves" (seq dirs))
    (check "every resolved directory exists"
           (every? #(.existsSync fs %) dirs))
    (check "every dependency checkout is at its pinned commit"
           (every? (fn [{:keys [coordinate git-sha]}]
                     (= git-sha (classpath/head-sha (classpath/checkout-dir coordinate git-sha))))
                   (:lock/entries (classpath/read-lock repo-root))))))

;; --- fetch and verification -----------------------------------------------

(let [gitlibs (temp-dir "kotoba-gitlibs-")
      origin (.join node-path (temp-dir "kotoba-origin-") "dep")
      sha (init-repo! origin)
      previous (.-GITLIBS js/process.env)]
  (set! (.-GITLIBS js/process.env) gitlibs)
  (let [entry {:coordinate "io.example/dep"
               :git-url (str "file://" origin)
               :git-sha sha
               :paths ["src"]}
        root (write-fixture! [entry])
        dirs (classpath/resolve-directories root)]
    (check "a dependency absent from the cache is fetched at its pin"
           (and (= 1 (count dirs)) (.existsSync fs (first dirs))))
    (check "the fetched checkout is at the pinned commit"
           (= sha (classpath/head-sha (classpath/checkout-dir "io.example/dep" sha)))))

  ;; A directory named after a commit is not evidence that it holds that
  ;; commit. Claim a different sha over the checkout that is really there.
  (let [wrong-sha (apply str (repeat 40 "a"))
        wrong-dir (classpath/checkout-dir "io.example/dep" wrong-sha)]
    (.mkdirSync fs (.join node-path wrong-dir "src") #js {:recursive true})
    (.cpSync fs (.join node-path origin ".git") (.join node-path wrong-dir ".git")
             #js {:recursive true})
    (let [root (write-fixture! [{:coordinate "io.example/dep"
                                 :git-url (str "file://" origin)
                                 :git-sha wrong-sha
                                 :paths ["src"]}])]
      (check "a checkout at the wrong commit is refused"
             (= :verify (phase-of #(classpath/resolve-directories root))))))

  (let [root (write-fixture! [{:coordinate "io.example/dep"
                               :git-url (str "file://" origin)
                               :git-sha sha
                               :paths ["src" "not-there"]}])]
    (check "a locked path that does not exist is refused"
           (= :verify (phase-of #(classpath/resolve-directories root)))))

  (if previous
    (set! (.-GITLIBS js/process.env) previous)
    (js-delete js/process.env "GITLIBS")))

;; --- the lock must agree with deps.edn ------------------------------------

(let [root (write-fixture! [] :digest-override (apply str (repeat 64 "0")))]
  (check "a lock generated for a different deps.edn is refused"
         (= :lock (phase-of #(classpath/resolve-directories root)))))

(let [root (write-fixture! [{:coordinate "io.example/dep" :git-url "file:///x"
                             :git-sha (apply str (repeat 40 "b")) :paths ["src"]}]
                           :version 99)]
  (check "an unsupported lock version is refused"
         (= :lock (phase-of #(classpath/resolve-directories root)))))

(let [root (write-fixture! [])]
  (check "an empty lock is refused, not treated as an empty classpath"
         (= :lock (phase-of #(classpath/resolve-directories root)))))

(let [root (temp-dir "kotoba-classpath-test-")]
  (.writeFileSync fs (.join node-path root "deps.edn") "{}\n")
  (check "a missing lock is refused"
         (= :lock (phase-of #(classpath/resolve-directories root)))))

(println (str (if (zero? @failures) "PASS" "FAIL") " jvm-free-classpath"
              (when hermetic-only? " (hermetic-only)")))
(when (pos? @failures) (.exit js/process 1))
