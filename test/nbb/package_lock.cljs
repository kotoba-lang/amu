(ns test.nbb.package-lock
  "The package lock, produced and consumed on this runtime.

  `ADR-kotoba-package-cid-lock` has carried M5 -- \"kotoba-lang/registry or
  kotoba-cli consumes the same suite\" -- as outstanding since 2026-06-30.
  Nothing read a lock, so every field in one was a claim no build checked.
  This suite is the check on the consumer.

  It asserts BOTH directions for every rule, and asserts the REASON, not just
  the refusal. That distinction is not pedantry here: measured 2026-09-06 in
  `kotoba-core-contracts`, the same forged-signature fixtures were `rejected`
  by a runtime that verified no signature at all -- an assertion of the form
  \"this was refused\" was green on a validator that refused everything."
  (:require ["node:child_process" :as child]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            [clojure.string :as str]
            [ed25519.core :as ed25519]
            [kotoba.compiler.definition-identity :as definition-identity]
            [kotoba.compiler.nbb.cli-support :as support]
            [kotoba.compiler.nbb.package-authoring :as authoring]
            [kotoba.compiler.nbb.package-lock :as package-lock]
            [kotoba.kir :as ir]
            [kotoba.sema :as sema]))

(def ^:private failures (atom 0))

(defn- check [label thunk]
  (try
    (thunk)
    (println "PASS" label)
    (catch :default error
      (swap! failures inc)
      (println "FAIL" label "--" (.-message error)))))

(defn- expect-reject
  "Run THUNK, require it to throw, and require the message to be the one this
  rule is named after. A throw for another reason is a failure, not a pass."
  [label expected thunk]
  (check label
         (fn []
           (let [outcome (try (thunk) ::no-throw
                              (catch :default e (.-message e)))]
             (cond
               (= ::no-throw outcome)
               (throw (js/Error. (str "expected a rejection containing "
                                      (pr-str expected) ", got acceptance")))

               (not (str/includes? outcome expected))
               (throw (js/Error. (str "rejected for the wrong reason: expected "
                                      (pr-str expected) ", got "
                                      (pr-str outcome)))))))))

;; ── fixture ─────────────────────────────────────────────────────────────────

(def ^:private package-source
  "(ns demo.util (:export [double-it]))\n\n(defn double-it [n] (* n 2))\n")

(def ^:private app-source
  "(ns main (:require [demo.util :as u]) (:export [run]))\n\n(defn run [n] (u/double-it n))\n")

(defn- mkdirs! [p] (.mkdirSync fs p #js {:recursive true}))

(defn- git! [dir args]
  (let [r (.spawnSync child "git" (clj->js (into ["-C" dir] args))
                      #js {:encoding "utf8"})]
    (when-not (zero? (or (.-status r) 1))
      (throw (js/Error. (str "git " (str/join " " args) " failed: "
                             (.-stderr r)))))
    (str/trim (or (.-stdout r) ""))))

(defn- describe-cids
  "Definition CIDs of one module file -- the same computation
  `kotoba.compiler.nbb.wasm-cli` hands the lock producer."
  [p]
  ;; `sema/analyze` returns the HIR map itself. (`wasm-cli` reaches it through
  ;; `compile-cache/resolve-stage!`, whose answer is wrapped in `:value` --
  ;; taking `:value` of the raw analyze result yields nil, and `describe` then
  ;; answers `:unavailable` rather than throwing.)
  (let [hir (sema/analyze (.readFileSync fs p "utf8")
                          (support/analyze-options nil))
        report (definition-identity/describe
                {:hir hir :kir (try (ir/lower hir) (catch :default _ nil))})]
    ;; `describe` answers `:unavailable` rather than throwing when it cannot
    ;; identify definitions, and `vals` of that is not a sequence. Refuse
    ;; loudly: a producer that swallowed this would write a lock pinning
    ;; nothing, which every consumer would then accept as "no definitions to
    ;; check".
    (when-not (map? (:entries report))
      (throw (js/Error. (str "no definition identity for " p ": "
                             (pr-str (:entries report))))))
    (keep :cid (vals (:entries report)))))

(defn- seed [] (js/Uint8Array.from (clj->js (vec (repeat 32 42)))))

(defn- write! [p text]
  (mkdirs! (.dirname path p))
  (.writeFileSync fs p text))

(defn- build-fixture!
  "A signed package, materialised under `<packages>/<name>/<commit>`, plus a
  consumer that requires it. Returns the paths the tests work over."
  []
  (let [root (.mkdtempSync fs (.join path (.tmpdir os) "amu-package-lock-"))
        pkg (.join path root "pkgsrc")
        app (.join path root "app")
        packages (.join path root "packages")]
    (write! (.join path pkg "src/demo/util.kotoba") package-source)
    (write! (.join path app "main.kotoba") app-source)
    (git! root ["init" "-q" pkg])
    (git! pkg ["add" "-A"])
    (git! pkg ["-c" "user.email=t@t" "-c" "user.name=t" "commit" "-q" "-m" "v0.1.0"])
    (let [commit (git! pkg ["rev-parse" "HEAD"])
          dest (.join path packages (package-lock/package-dir-name
                                     "kotoba-lang/demo-util")
                      commit)]
      (mkdirs! (.dirname path dest))
      (.cpSync fs pkg dest #js {:recursive true})
      (let [manifest (authoring/build-manifest
                      {:root dest
                       :name "kotoba-lang/demo-util"
                       :version "0.1.0"
                       :url "https://github.com/kotoba-lang/demo-util.git"
                       :capabilities []
                       :commit commit
                       :seed (seed)})]
        (authoring/write-edn!
         (.join path dest package-lock/manifest-file-name) manifest)
        {:root root :app app :packages packages :commit commit
         :package-root dest
         :manifest-path (.join path dest package-lock/manifest-file-name)
         :entry (.join path app "main.kotoba")
         :module (.join path dest "src/demo/util.kotoba")}))))

(defn- make-lock!
  [{:keys [packages commit root]}]
  (let [deps (.join path root "kotoba.deps.edn")
        out (.join path root "kotoba.lock.edn")]
    (authoring/write-edn!
     deps {:packages {"kotoba-lang/demo-util"
                      {:git/url "https://github.com/kotoba-lang/demo-util.git"
                       :git/sha commit
                       :version "0.1.0"
                       :entries ["src/demo/util.kotoba"]}}})
    (authoring/package-lock! describe-cids
                             ["package-lock" "--deps" deps
                              "--packages" packages "--output" out])
    out))

(defn- resolve! [lock packages] (package-lock/resolve-lock lock packages nil))

(defn- edit-lock!
  "A copy of the lock with one textual substitution, so a test can express
  exactly one deviation."
  [lock root name from to]
  (let [text (.readFileSync fs lock "utf8")
        _ (when-not (str/includes? text from)
            (throw (js/Error. (str "fixture drift: " (pr-str from)
                                   " is not in the lock, so this test would "
                                   "be asserting against an unmodified file"))))
        out (.join path root (str name ".edn"))]
    (.writeFileSync fs out (str/replace text from to))
    out))

;; ── the suite ───────────────────────────────────────────────────────────────

(let [f (build-fixture!)
      lock (make-lock! f)
      {:keys [packages package-root manifest-path module root]} f
      pristine-manifest (.readFileSync fs manifest-path "utf8")
      pristine-module (.readFileSync fs module "utf8")
      restore! (fn []
                 (.writeFileSync fs manifest-path pristine-manifest)
                 (.writeFileSync fs module pristine-module))]

  (check "a signed, materialised package resolves"
         (fn []
           (let [r (resolve! lock packages)
                 dep (first (:dependencies r))
                 outcomes (into {} (map (juxt :check :outcome)) (:checks dep))]
             (when-not (= 1 (count (:dependencies r)))
               (throw (js/Error. "expected exactly one dependency")))
             ;; Every check must have RUN. `:unverified` is a legal outcome for
             ;; a tree with no git metadata, and this fixture has some, so an
             ;; unverified commit here means the check silently stopped.
             (doseq [c [:git-commit :tree-cid :manifest-signature
                        :manifest-integrity]]
               (when-not (= :verified (get outcomes c))
                 (throw (js/Error. (str c " is " (pr-str (get outcomes c))
                                        ", expected :verified")))))
             (when-not (seq (:source-paths r))
               (throw (js/Error. "resolved no source paths"))))))

  (check "the pinned definitions are the ones the compiler computes"
         (fn []
           (let [r (resolve! lock packages)
                 pinned (:definition-cids (first (:dependencies r)))
                 computed (set (describe-cids module))]
             (when-not (= pinned computed)
               (throw (js/Error. (str "pinned " (pr-str pinned)
                                      " computed " (pr-str computed))))))))

  (check "verify-definitions accepts a superset"
         (fn []
           (let [r (resolve! lock packages)]
             (package-lock/verify-definitions
              (:dependencies r)
              (concat (describe-cids module)
                      ["bafyreigpx34zxsmr526da3dxjd66b7fftx3jpyialfcuhtiart5ylrcehe"])))))

  (expect-reject "verify-definitions refuses a graph missing a pinned definition"
                 "definitions the package lock pins are not in the built graph"
                 (fn []
                   (package-lock/verify-definitions
                    (:dependencies (resolve! lock packages)) [])))

  (expect-reject "a changed source byte fails the tree cid"
                 "tree cid does not match tree content"
                 (fn []
                   (.writeFileSync fs module
                                   (str/replace pristine-module "(* n 2)" "(* n 3)"))
                   (try (resolve! lock packages) (finally (restore!)))))

  (expect-reject "an extra file in the tree fails the tree cid"
                 "tree cid does not match tree content"
                 (fn []
                   (let [extra (.join path package-root "extra.txt")]
                     (.writeFileSync fs extra "x")
                     (try (resolve! lock packages)
                          (finally (.rmSync fs extra #js {:force true}))))))

  (expect-reject "a manifest field changed after signing fails integrity"
                 "manifest cid does not match manifest content"
                 (fn []
                   (.writeFileSync fs manifest-path
                                   (str/replace pristine-manifest
                                                ":kotoba.package/capabilities []"
                                                ":kotoba.package/capabilities [:graph-read]"))
                   (try (resolve! lock packages) (finally (restore!)))))

  (expect-reject "a forged signature fails verification"
                 "signature verification failed"
                 (fn []
                   (let [sig (second (re-find #":sig \"([^\"]+)\"" pristine-manifest))
                         bad (str (if (= "A" (subs sig 0 1)) "B" "A") (subs sig 1))]
                     (.writeFileSync fs manifest-path
                                     (str/replace pristine-manifest sig bad))
                     (try (resolve! lock packages) (finally (restore!))))))

  (expect-reject "a tree with no manifest is refused"
                 "dependency tree carries no package manifest"
                 (fn []
                   (.rmSync fs manifest-path #js {:force true})
                   (try (resolve! lock packages) (finally (restore!)))))

  (expect-reject "a lock that pins no definitions is refused"
                 "does not pin its definitions"
                 (fn []
                   (resolve! (edit-lock! lock root "no-defs"
                                         ":dep/definition-cids" ":dep/other-cids")
                             packages)))

  (expect-reject "a grant wider than the package declares is refused"
                 "capability grant exceeds package declaration"
                 (fn []
                   (resolve! (edit-lock! lock root "wide-grant"
                                         ":dep/capabilities []"
                                         ":dep/capabilities [:graph-read]")
                             packages)))

  (expect-reject "a local-path dependency is refused"
                 "local-path dependency not allowed"
                 (fn []
                   (resolve! (edit-lock! lock root "local-path"
                                         ":dep/kind :library"
                                         ":dep/kind :library, :dep/local-root \"/tmp/x\"")
                             packages)))

  ;; An EMPTY packages directory, not a missing one. Pointing at a missing
  ;; path trips the earlier `--packages must name an existing directory` guard
  ;; instead, which is a different rule -- caught by this suite asserting the
  ;; reason rather than the refusal.
  (expect-reject "a package directory without this dependency is refused"
                 "dependency tree is not materialised"
                 (fn []
                   (let [empty-dir (.join path root "empty-packages")]
                     (mkdirs! empty-dir)
                     (resolve! lock empty-dir))))

  (expect-reject "a packages directory that does not exist is refused"
                 "--packages must name an existing directory"
                 (fn [] (resolve! lock (.join path root "no-such-packages-dir"))))

  ;; ── package-fetch ────────────────────────────────────────────────────────
  ;;
  ;; `--packages` had to be populated by hand until 2026-09-06; the refusals
  ;; named a command that did not exist. These run against a bare local
  ;; repository, so they exercise the real clone/checkout path without needing
  ;; the network.

  (let [remote (.join path root "remote.git")
        fetched (.join path root "fetched-packages")
        deps (.join path root "fetch.deps.edn")
        source (.join path root "pkgsrc")
        ;; The publisher commits the manifest into the package repository --
        ;; that is what makes a fetched tree self-describing. `build-fixture!`
        ;; wrote one into the materialised copy; the source repository needs
        ;; its own, and the commit it lands in is what the lock will pin.
        published (do (.cpSync fs (:manifest-path f)
                               (.join path source package-lock/manifest-file-name))
                      (git! source ["add" "-A"])
                      (git! source ["-c" "user.email=t@t" "-c" "user.name=t"
                                    "commit" "-q" "-m" "publish manifest"])
                      (git! source ["rev-parse" "HEAD"]))]
    (git! root ["clone" "--quiet" "--bare" source remote])
    (authoring/write-edn!
     deps {:packages {"kotoba-lang/demo-util"
                      {:git/url remote :git/sha published
                       :version "0.1.0"
                       :entries ["src/demo/util.kotoba"]}}})

    (check "package-fetch materialises a package at its pinned commit"
           (fn []
             (let [r (authoring/package-fetch!
                      ["package-fetch" "--deps" deps "--packages" fetched])
                   entry (first (:fetched r))
                   dest (package-lock/dependency-root
                         fetched {:dep/name "kotoba-lang/demo-util"
                                  :dep/commit published})]
               (when-not (= :fetched (:outcome entry))
                 (throw (js/Error. (str "outcome " (pr-str (:outcome entry))))))
               (when-not (.existsSync fs (.join path dest "src/demo/util.kotoba"))
                 (throw (js/Error. "the package source is not where it was put")))
               ;; ADR-2607211600 retired shallow clones: a graft boundary makes
               ;; ancestry answers wrong while looking authoritative, and this
               ;; directory is the subject of a commit check.
               (when-not (= "false" (git! dest ["rev-parse" "--is-shallow-repository"]))
                 (throw (js/Error. "the fetched checkout is shallow"))))))

    (check "a second fetch verifies rather than refetching"
           (fn []
             (let [r (authoring/package-fetch!
                      ["package-fetch" "--deps" deps "--packages" fetched])]
               ;; `:already-present` and `:fetched` must not print the same, or
               ;; a run that did nothing reads like a run that brought
               ;; everything down.
               (when-not (= :already-present (:outcome (first (:fetched r))))
                 (throw (js/Error. (str "outcome "
                                        (pr-str (:outcome (first (:fetched r)))))))))))

    (expect-reject "a directory named after one commit but holding another is refused"
                   "a different commit is already materialised at this path"
                   (fn []
                     (let [fake "0123456789abcdef0123456789abcdef01234567"
                           held (package-lock/dependency-root
                                 fetched {:dep/name "kotoba-lang/demo-util"
                                          :dep/commit published})
                           impostor (package-lock/dependency-root
                                     fetched {:dep/name "kotoba-lang/demo-util"
                                              :dep/commit fake})
                           deps2 (.join path root "fetch-impostor.deps.edn")]
                       ;; A directory NAMED after a commit is not evidence that
                       ;; it holds one -- the whole reason this check exists.
                       (.cpSync fs held impostor #js {:recursive true})
                       (authoring/write-edn!
                        deps2 {:packages {"kotoba-lang/demo-util"
                                          {:git/url remote :git/sha fake
                                           :version "0.1.0"
                                           :entries ["src/demo/util.kotoba"]}}})
                       (authoring/package-fetch!
                        ["package-fetch" "--deps" deps2 "--packages" fetched]))))

    (expect-reject "a commit the repository does not have is refused"
                   "the pinned commit is not in the fetched repository"
                   (fn []
                     (let [deps3 (.join path root "fetch-missing.deps.edn")]
                       (authoring/write-edn!
                        deps3 {:packages
                               {"kotoba-lang/absent"
                                {:git/url remote
                                 :git/sha "0123456789abcdef0123456789abcdef01234567"
                                 :version "0.1.0"
                                 :entries ["src/demo/util.kotoba"]}}})
                       (authoring/package-fetch!
                        ["package-fetch" "--deps" deps3 "--packages" fetched]))))

    (check "a lock built over a FETCHED tree resolves"
           (fn []
             (let [out (.join path root "fetched.lock.edn")]
               (authoring/package-lock! describe-cids
                                        ["package-lock" "--deps" deps
                                         "--packages" fetched "--output" out])
               (let [r (package-lock/resolve-lock out fetched nil)]
                 (when-not (= 1 (count (:dependencies r)))
                   (throw (js/Error. "the fetched tree did not resolve")))))))) 

  (check "the fixture is intact after every negative case"
         (fn []
           (let [r (resolve! lock packages)]
             (when-not (= 1 (count (:dependencies r)))
               (throw (js/Error. "the suite left the fixture broken"))))))

  (println (str "SCANNED\tpackage-lock suite, failures=" @failures))
  (when (pos? @failures) (.exit js/process 1)))
