"""Fetch an exact main-run bounded fixture and verify before using it.

The source SHA and verifier pin must be supplied by trusted host configuration,
not by the downloaded artifact or a PR-controlled cache record. A missing
candidate is distinct from a malformed or unauthenticated one. This is not
whole-compiler cache admission.
"""
import hashlib
import json
import os
import re
import select
import stat
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

from bounded_cache_bundle import verified_extract
from sealed_image import MAX_IMAGE_BYTES, sealed_image
from verified_attestation import AttestationPolicy

REPO = "kotoba-lang/amu"
REPO_ID = 1297097065
WORKFLOW = ".github/workflows/bounded-cache-producer.yml"


class CacheUnavailable(Exception):
    """No successful producer exists for this exact source revision."""


def _run_matches(row, sha):
    return (row.get("event") == "push" and row.get("status") == "completed" and
            row.get("conclusion") == "success" and row.get("head_branch") == "main" and
            row.get("head_sha") == sha and row.get("path") == WORKFLOW and
            row.get("repository", {}).get("id") == REPO_ID and
            row.get("head_repository", {}).get("id") == REPO_ID and
            type(row.get("id")) is int and row["id"] > 0)


def _artifact_matches(row, run_id, sha):
    run = row.get("workflow_run") or {}
    return (row.get("name") == "experimental-bounded-kir-producer-" + sha and
            row.get("expired") is False and type(row.get("id")) is int and row["id"] > 0 and
            type(row.get("size_in_bytes")) is int and 0 < row["size_in_bytes"] <= MAX_IMAGE_BYTES and
            bool(re.fullmatch(r"sha256:[0-9a-f]{64}", row.get("digest") or "")) and
            run.get("id") == run_id and run.get("repository_id") == REPO_ID and
            run.get("head_repository_id") == REPO_ID and run.get("head_branch") == "main" and
            run.get("head_sha") == sha)


def _select_artifact(rows, run_id, sha):
    candidates = [a for a in rows if a.get("name") == "experimental-bounded-kir-producer-" + sha]
    if len(candidates) > 1:
        raise ValueError("ambiguous producer artifacts")
    if not candidates or candidates[0].get("expired") is True:
        return None
    if not _artifact_matches(candidates[0], run_id, sha):
        raise ValueError("producer artifact metadata mismatch")
    return candidates[0]


def _unzip_exact(path, destination):
    """Extract one regular bounded tar, never paths supplied by a zip."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) != 1:
            raise ValueError("unexpected artifact archive entries")
        info = entries[0]
        mode = info.external_attr >> 16
        if (info.filename != "bounded-cache.tar" or info.is_dir() or
            (mode and not stat.S_ISREG(mode)) or info.flag_bits & 1 or
            info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) or
            not 0 < info.file_size <= MAX_IMAGE_BYTES):
            raise ValueError("invalid artifact archive entry")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = os.open(destination, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as out, archive.open(info) as source:
                total = 0
                while True:
                    data = source.read(1024 * 1024)
                    if not data:
                        break
                    total += len(data)
                    if total > info.file_size or total > MAX_IMAGE_BYTES:
                        raise ValueError("artifact entry exceeds its limit")
                    out.write(data)
                if total != info.file_size:
                    raise ValueError("truncated artifact entry")
        except BaseException:
            Path(destination).unlink(missing_ok=True)
            raise


def _call(gh_fd, env, endpoint):
    result = subprocess.run([f"/proc/self/fd/{gh_fd}", "api", endpoint], env=env, pass_fds=(gh_fd,),
                            capture_output=True, timeout=120, check=True)
    if len(result.stdout) > 4 * 1024 * 1024:
        raise ValueError("GitHub metadata exceeds size limit")
    return json.loads(result.stdout)


def _download(gh_fd, env, artifact, output):
    endpoint = f"repos/{REPO}/actions/artifacts/{artifact['id']}/zip"
    digest = hashlib.sha256()
    with tempfile.TemporaryFile() as errors, Path(output).open("xb") as dest:
        proc = subprocess.Popen([f"/proc/self/fd/{gh_fd}", "api", endpoint], env=env,
                                pass_fds=(gh_fd,), stdout=subprocess.PIPE, stderr=errors)
        try:
            total = 0
            deadline = time.monotonic() + 120
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([proc.stdout], [], [], remaining)[0]:
                    raise TimeoutError("artifact download timed out")
                data = os.read(proc.stdout.fileno(), 1024 * 1024)
                if not data:
                    break
                total += len(data)
                if total > MAX_IMAGE_BYTES or total > artifact["size_in_bytes"]:
                    raise ValueError("download exceeds declared size")
                digest.update(data)
                dest.write(data)
            if proc.wait(timeout=max(0.1, deadline - time.monotonic())) != 0 or total != artifact["size_in_bytes"]:
                raise ValueError("artifact download failed or was truncated")
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        if "sha256:" + digest.hexdigest() != artifact["digest"]:
            raise ValueError("downloaded archive digest mismatch")


def fetch_verified(source_sha, gh, gh_sha256, destination):
    """Fetch an exact successful main artifact and verify its attested bundle."""
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("source revision must be an immutable SHA")
    policy = AttestationPolicy(REPO, str(REPO_ID), WORKFLOW, "refs/heads/main", source_sha, source_sha, "push")
    with tempfile.TemporaryDirectory(prefix="bounded-fetch-") as temp:
        env = {"PATH": "/usr/bin:/bin", "GH_HOST": "github.com", "GH_PROMPT_DISABLED": "1",
               "HOME": temp, "GH_CONFIG_DIR": temp}
        if "GH_TOKEN" in os.environ:
            env["GH_TOKEN"] = os.environ["GH_TOKEN"]
        with sealed_image(gh, gh_sha256) as (fd, _):
            endpoint = (f"repos/{REPO}/actions/workflows/bounded-cache-producer.yml/runs"
                        f"?event=push&branch=main&status=success&head_sha={source_sha}&per_page=100")
            listing = _call(fd, env, endpoint)
            rows = listing.get("workflow_runs", [])
            if any(not _run_matches(r, source_sha) for r in rows):
                raise ValueError("producer run metadata mismatch")
            runs = sorted(rows, key=lambda r: r["id"], reverse=True)
            selected = None
            for run in runs:
                listing = _call(fd, env, f"repos/{REPO}/actions/runs/{run['id']}/artifacts?per_page=100")
                if listing.get("total_count", 0) > 100:
                    raise ValueError("too many artifacts for an unambiguous producer")
                selected = _select_artifact(listing.get("artifacts", []), run["id"], source_sha)
                if selected:
                    break
            if selected is None:
                raise CacheUnavailable("no successful unexpired producer for this exact revision")
            zip_path, tar_path = Path(temp) / "artifact.zip", Path(temp) / "bounded-cache.tar"
            _download(fd, env, selected, zip_path)
        _unzip_exact(zip_path, tar_path)
        image, objects, image_digest, bundle_digest = verified_extract(tar_path, gh, gh_sha256, policy, destination)
        return image, objects, image_digest, bundle_digest


if __name__ == "__main__":
    import argparse
    from check_bounded_producer_attestation import GH_SHA256, exercise

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True, help="immutable revision from trusted host configuration")
    parser.add_argument("--gh", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700)
    os.chmod(args.output, 0o700)
    output = args.output.resolve()
    try:
        image, objects, image_digest, bundle_digest = fetch_verified(args.source_sha, args.gh, GH_SHA256,
                                                                      output / "bundle")
    except CacheUnavailable as error:
        parser.exit(75, f"CACHE_UNAVAILABLE: {error}\n")
    exercise(image, objects, image_digest, output)
    print("PASS_FETCHED_BOUNDED_CACHE", args.source_sha, bundle_digest, flush=True)
