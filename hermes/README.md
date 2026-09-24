# hermes/ — the resident bots that act for this repository

This directory is the **source of truth** for the Hermes profiles listed below
(ADR-2609241200). The host's `~/.hermes/profiles/<profile>` is materialized
from `hermes/profiles/<profile>/` and checked against it:

```
kbb --backend sci scripts/hermes-profile-repo.cljk materialize <profile>   # repo -> host
kbb --backend sci scripts/hermes-profile-repo.cljk check <profile>         # 0 agree / 1 drift / 2 could not compare
kbb --backend sci scripts/hermes-profile-repo.cljk export <profile>        # host -> repo, then commit
```

(run from the com-junkawasaki/root superproject; registry
`manifest/hermes-profile-repos.edn`.)

Each profile directory holds SOUL.md, profile.yaml, config.yaml (host-local
blocks removed), cron/jobs.json (definitions only), scripts/ and the skills the
profile owns. **Never here:** `.env` or any secret value, workspace/ledgers,
sessions, memories, logs, caches, run state.

## Profiles

| profile | description |
|---|---|
| `aiueos-maint` | kotoba-lang/aiueos OSS maintainer bot: issue triage + main red test |
| `amu` | Amu co-scientist: kotoba-lang/amu を世界最速 runtime & build-time OS にする検証ループ |
| `amu-bench` | amu co-scientist cowork: perfgate/bench 実行と quiet gate 監視専門, 15min cron |
| `amu-falsify` | amu co-scientist cowork: 反証実験専門 (hand-patch 測定で仮説を殺す), 15min cron |
| `amu-jit-cosientist` | amu JIT/tiering 軸の co-scientist: JIT仮説ループ (perfgate 判定, 30min) |
| `amu-maint` | kotoba-lang/amu OSS maintainer bot: issue/PR triage + CI 赤検知 + pin 安定化, |
| `amu-rank` | amu co-scientist cowork: 仮説 rank/進化と tournament state 更新専門, 15min cron |
| `amu-test-jvmfree` | amu test 経路の JVM-free 化ドライバー: test_profile.cljk の JVM 依存 (clojure.java.shell / java.util.Base64) を nbb/Node 経路へ移植し、bin/amu が `test --jvm-free` を受理するまで進める。 |
| `jvm-dep-migrator` | kotoba-lang org JVM 依存 repo の Q9 whole-component 移行: 棚卸し→計画→段階的 PR, |
| `jvm-retire` |  |
| `kotoba-cloud-maint` | kotoba.cloud メンテ (network-awai/app-kotoba-cloud Worker), 60min cron |
| `kotoba-lang-cosientist` | kotoba 言語機能×速度 co-scientist: blocked 機能の実装と速度検証, 30min |
| `kotoba-maint` | kotoba-lang/kotoba OSS maintainer bot: issue/PR triage + CI 赤検知, 30min |
| `kotobalang-maint` | kotoba-lang org 横断 maintainer bot: CI 赤検知 + repo 健全性, 30min cron |
| `kotobalang-org-maint` | kotoba-lang.org site メンテ (orgs/kotoba-lang/kotoba-lang site/, Cloudflare), |
