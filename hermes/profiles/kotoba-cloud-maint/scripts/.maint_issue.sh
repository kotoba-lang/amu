#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
cat > /tmp/issue_body.md <<'EOF'
## Live measurement 2026-09-18T15:39Z (maint bot, curl)

The entire static asset tree returns 404 on every host; only worker API routes respond.

| URL | status |
|---|---|
| https://kotoba.cloud/ | 404 (empty body, `x-content-identity: unmeasured`, CSP headers from worker.cljk present) |
| https://kotoba.cloud/en/ | 404 |
| https://kotoba.cloud/ja/ , /index.html , /pricing , /about , /404-page | 404 |
| https://kotoba.cloud/llms.txt , /agent-quickstart.md | 404 |
| https://docs.kotoba.cloud/ , /graph/ | 404 |
| https://twin.kotoba.cloud/ | 404 |
| https://boot.kotoba.cloud/ | 404 |
| https://kotoba.cloud/health | 200 `{"ok":true,"service":"kotoba-cloud-control-plane"}` |
| https://api.kotoba.cloud/v1/control-plane | 200 (schema JSON OK) |

## Reading
- The 404 responses carry route-static's headers (Vary: Accept-Language/Cookie/CF-IPCountry, security CSP, `x-content-identity: unmeasured`), so the deployed **worker** is alive and routing; the **ASSETS binding is answering 404 for everything**, including `/404-page` (which `not_found_handling: "404-page"` in wrangler.jsonc requires). That points at a deploy whose `./public` directory was empty/missing or whose asset manifest didn't upload — worker deployed, assets didn't.
- Latest main: 61fde42d (Merge PR #419 nex-mini-go-live). Recent deploys of research-authority features happened ~2026-09-18 per ADRs in git log. No CI on this repo, so a broken `npm run render`/asset step would not have been caught by tests if the deploy pipeline's asset stage failed after the worker uploaded.

## Suggested first checks (owner)
1. `wrangler deployments list` — was the newest deploy made with a build whose `public/` was empty (e.g. `npm run build` render step failed but deploy continued)?
2. Redeploy from a verified build: `npm run dry-run` passes → `npm run deploy`.
3. Rollback to the previous deployment in the CF dashboard if the newest one is the culprit (human approval required — maint bot will not deploy/rollback).

Reported by the kotoba-cloud-maint bot (observed only; no deploy/rollback executed).
EOF
gh issue create -R cloud-kotoba/app-kotoba-cloud \
  --title "OUTAGE: all static hosts 404 (apex, /en/, docs, twin, boot, even /404-page) — ASSETS binding serving nothing; worker API routes OK" \
  --body-file /tmp/issue_body.md --label bug
