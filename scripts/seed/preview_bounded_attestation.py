#!/usr/bin/env python3
"""Temporary branch-only GitHub attestation qualification, not production."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from bounded_cache_bundle import _extract_sealed
from check_bounded_producer_attestation import GH_SHA256, exercise
from sealed_image import sealed_blob, sealed_image
from verified_attestation import AttestationPolicy, _certificate_matches

REPO = "kotoba-lang/amu"
REF = "refs/heads/codex/jun-358-attested-producer-20261102"
WORKFLOW = ".github/workflows/bounded-cache-preview.yml"


def main():
    if (os.environ.get("GITHUB_REPOSITORY") != REPO or os.environ.get("GITHUB_REPOSITORY_ID") != "1297097065" or
        os.environ.get("GITHUB_REF") != REF or os.environ.get("GITHUB_EVENT_NAME") != "push"):
        raise ValueError("preview requires the task branch push context")
    sha = os.environ["GITHUB_SHA"]
    root = Path(os.environ["RUNNER_TEMP"])
    policy = AttestationPolicy(REPO, "1297097065", WORKFLOW, REF, sha, sha, "push")
    identity = f"https://github.com/{REPO}/{WORKFLOW}@{REF}"
    with sealed_blob(root / "bounded-cache.tar") as (fd, digest), sealed_image(root / "pinned-gh", GH_SHA256) as (ghfd, _):
        args = [f"/proc/self/fd/{ghfd}", "attestation", "verify", f"/proc/self/fd/{fd}", "--repo", REPO,
                "--cert-identity", identity, "--source-ref", REF, "--source-digest", sha, "--signer-digest", sha,
                "--deny-self-hosted-runners", "--format", "json"]
        with tempfile.TemporaryDirectory(prefix="preview-gh-", dir=root) as config:
            env = dict(PATH="/usr/bin:/bin", GH_HOST="github.com", GH_PROMPT_DISABLED="1", HOME=config,
                       GH_CONFIG_DIR=config, GH_TOKEN=os.environ["GH_TOKEN"])
            result = subprocess.run(args, env=env, pass_fds=(fd, ghfd), capture_output=True, timeout=120, check=True)
        rows = json.loads(result.stdout)
        if not any(_certificate_matches(r["verificationResult"]["signature"]["certificate"], policy) and
                   any(s.get("digest", {}).get("sha256") == digest for s in r["verificationResult"]["statement"]["subject"])
                   for r in rows):
            raise ValueError("preview attestation does not match the sealed bundle")
        image, objects, image_digest = _extract_sealed(fd, root / "preview-bundle")
    exercise(image, objects, image_digest, root)
    print("PASS_BRANCH_ONLY_ATTESTED_NATIVE_BUNDLE", sha, digest, flush=True)


if __name__ == "__main__":
    main()
