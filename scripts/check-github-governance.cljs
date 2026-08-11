(ns scripts.check-github-governance
  (:require [cljs.reader :as reader]
            [scripts.lib :as lib]))

(def policy-path
  (lib/join lib/root "docs" "adr" "0249-version-github-merge-governance.edn"))

(defn- api [endpoint]
  (let [{:keys [stdout]} (lib/run "gh" ["api" "--method" "GET" endpoint])]
    (js->clj (js/JSON.parse stdout) :keywordize-keys true)))

(defn- normalize-check [{:keys [context app_id]}]
  {:context context :app-id app_id})

(defn- live-policy [{:keys [repository default-branch]}]
  (let [protection (api (str "repos/" repository "/branches/" default-branch "/protection"))
        actions (api (str "repos/" repository "/actions/permissions"))
        workflow (api (str "repos/" repository "/actions/permissions/workflow"))]
    {:schema/version 1
     :repository repository
     :default-branch default-branch
     :actions
     {:enabled (:enabled actions)
      :allowed-actions (:allowed_actions actions)
      :sha-pinning-required (:sha_pinning_required actions)
      :default-workflow-permissions (:default_workflow_permissions workflow)
      :can-approve-pull-request-reviews (:can_approve_pull_request_reviews workflow)}
     :branch-protection
     {:strict (get-in protection [:required_status_checks :strict])
      :enforce-admins (get-in protection [:enforce_admins :enabled])
      :required-conversation-resolution
      (get-in protection [:required_conversation_resolution :enabled])
      :allow-force-pushes (get-in protection [:allow_force_pushes :enabled])
      :allow-deletions (get-in protection [:allow_deletions :enabled])
      :required-checks
      (->> (get-in protection [:required_status_checks :checks])
           (map normalize-check)
           (sort-by :context)
           vec)}}))

(defn- verify! [expected actual]
  (when-not (= expected actual)
    (throw (js/Error.
            (str "GitHub governance drift detected\nexpected: " (pr-str expected)
                 "\nactual:   " (pr-str actual)))))
  actual)

(let [expected (reader/read-string (lib/read-text policy-path))]
  (verify! expected (live-policy expected))
  (println "github-governance: live GitHub policy matches" policy-path))
