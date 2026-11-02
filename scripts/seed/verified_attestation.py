"""Verify GitHub provenance before using a sealed artifact.

The policy and gh image pin must be selected by a trusted host, never by the
artifact or a PR-controlled manifest. This is a transport/identity check; it
does not validate compiler input closure or confer native admission.
"""
import json
import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass

from sealed_image import sealed_blob, sealed_image


@dataclass(frozen=True)
class AttestationPolicy:
    repository: str
    repository_id: str
    workflow: str
    ref: str
    source_sha: str
    signer_sha: str
    trigger: str


def _validate(policy):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", policy.repository):
        raise ValueError("invalid repository")
    if not re.fullmatch(r"[1-9][0-9]*", policy.repository_id):
        raise ValueError("invalid repository ID")
    if not re.fullmatch(r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml", policy.workflow):
        raise ValueError("invalid workflow")
    if not re.fullmatch(r"refs/heads/[A-Za-z0-9_.-]+", policy.ref):
        raise ValueError("invalid source ref")
    for value in (policy.source_sha, policy.signer_sha):
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise ValueError("invalid source or signer SHA")
    if policy.trigger not in ("push", "schedule", "workflow_dispatch"):
        raise ValueError("invalid trigger")


def _certificate_matches(certificate, policy):
    identity = f"https://github.com/{policy.repository}/{policy.workflow}@{policy.ref}"
    expected = {
        "issuer": "https://token.actions.githubusercontent.com",
        "subjectAlternativeName": identity,
        "buildSignerURI": identity,
        "buildSignerDigest": policy.signer_sha,
        "sourceRepositoryURI": f"https://github.com/{policy.repository}",
        "sourceRepositoryIdentifier": policy.repository_id,
        "sourceRepositoryDigest": policy.source_sha,
        "sourceRepositoryRef": policy.ref,
        "runnerEnvironment": "github-hosted",
        "buildTrigger": policy.trigger,
    }
    return all(certificate.get(key) == value for key, value in expected.items())


@contextmanager
def verified_artifact(path, gh, gh_sha256, policy):
    """Yield (fd, sha256); only the sealed fd is verified and may be used.

    Attestations are fetched online from GitHub for the current repository ID.
    No caller-provided bundle, cache record, or predicate is an authority.
    """
    with _verified_artifact(path, gh, gh_sha256, policy, ()) as result:
        yield result


@contextmanager
def _verified_artifact(path, gh, gh_sha256, policy, verifier_test_args):
    # verifier_test_args is private for offline cryptographic test fixtures;
    # the public entry always supplies an empty tuple and fetches from GitHub.
    _validate(policy)
    with sealed_blob(path) as (artifact_fd, artifact_digest):
        with sealed_image(gh, gh_sha256) as (gh_fd, _):
            identity = f"https://github.com/{policy.repository}/{policy.workflow}@{policy.ref}"
            args = [f"/proc/self/fd/{gh_fd}", "attestation", "verify", f"/proc/self/fd/{artifact_fd}",
                    "--repo", policy.repository, "--cert-identity", identity,
                    "--source-ref", policy.ref, "--source-digest", policy.source_sha,
                    "--signer-digest", policy.signer_sha, "--deny-self-hosted-runners", "--format", "json",
                    *verifier_test_args]
            with tempfile.TemporaryDirectory(prefix="kotoba-gh-") as config:
                env = {"PATH": "/usr/bin:/bin", "GH_HOST": "github.com", "GH_PROMPT_DISABLED": "1",
                       "HOME": config, "GH_CONFIG_DIR": config}
                if "GH_TOKEN" in os.environ:
                    env["GH_TOKEN"] = os.environ["GH_TOKEN"]
                result = subprocess.run(args, env=env, capture_output=True, timeout=120,
                                        pass_fds=(gh_fd, artifact_fd))
            if result.returncode != 0:
                raise ValueError("attestation verification failed")
            try:
                rows = json.loads(result.stdout)
                valid = any(_certificate_matches(row["verificationResult"]["signature"]["certificate"], policy)
                            and any(s.get("digest", {}).get("sha256") == artifact_digest
                                    for s in row["verificationResult"]["statement"]["subject"])
                            for row in rows)
            except (TypeError, KeyError, ValueError):
                valid = False
            if not valid:
                raise ValueError("attestation certificate or subject mismatch")
            os.lseek(artifact_fd, 0, os.SEEK_SET)
            yield artifact_fd, artifact_digest
