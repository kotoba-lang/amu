#!/usr/bin/env python3
"""Verify the experimental producer built by the main push workflow.

This verifies artifact origin only. Source identity, resource proof and
production/shared-cache admission remain separate native qualifications.
"""
import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from bounded_cache_bundle import verified_extract
from sealed_image import sealed_image
from verified_attestation import AttestationPolicy

GH_SHA256 = "b768184570b12536be4ac1528893f6340d1c6a7b40b56ad45bca9cd0e87ad34d"
REPO_ID = "1297097065"
WORKFLOW = ".github/workflows/bounded-cache-producer.yml"
PROBE = ("{:format :kotoba.kir/v4 :entry main :exports [main] :effects #{} :functions ["
         "{:name helper :params [x] :param-types [:i64] :result :i64 :effects #{} "
         ":body (if (< x 0) 0 (+ x 2))} "
         "{:name main :params [] :param-types [] :result :i64 :effects #{} :body (helper 40)}]}\n")


def exercise(image, objects, image_digest, root):
    """Perform fresh admission/link and execute a bounded reused-object probe."""
    root = Path(root)
    source, reference, candidate = root / "probe.kir", root / "reference.elf", root / "candidate.elf"
    source.write_text(PROBE)
    env = dict(PATH="/nonexistent", KEXE_ALLOW="35,37,38,39", KEXE_CAP_RESOURCES_35=str(root),
               KEXE_STACK_BYTES="8388608", KEXE_FUEL="10000000000")
    with sealed_image(image, image_digest) as (fd, digest):
        os.lseek(fd, 0, os.SEEK_SET)
        if os.read(fd, 4) != b"\x7fELF":
            raise ValueError("attested candidate is not an ELF image")
        for mode, output in (("reference", reference), ("cached", candidate)):
            proc = subprocess.run([f"/proc/self/fd/{fd}", mode, str(source), str(objects), digest,
                                   str(output), "1000000"], env=env, cwd=root, pass_fds=(fd,),
                                  capture_output=True, timeout=120, check=True)
            if proc.stderr or (mode == "cached" and proc.stdout.splitlines()[-1:] != [b"DCB1 reused=2 rebuilt=0"]):
                raise ValueError("fresh candidate admission or expected object reuse failed")
    if reference.read_bytes() != candidate.read_bytes():
        raise ValueError("reused object differs from fresh output")
    candidate.chmod(0o500)
    proc = subprocess.run([str(candidate)], env={"PATH": "/nonexistent"}, cwd=root,
                          capture_output=True, timeout=30, check=True)
    if proc.stderr or proc.stdout != (42).to_bytes(8, "little", signed=True):
        raise ValueError("fresh execution did not match the native oracle")


def main(artifact, gh):
    if (os.environ.get("GITHUB_REPOSITORY") != "kotoba-lang/amu" or
        os.environ.get("GITHUB_REPOSITORY_ID") != REPO_ID or
        os.environ.get("GITHUB_REF") != "refs/heads/main" or
        os.environ.get("GITHUB_EVENT_NAME") != "push"):
        raise ValueError("producer verification requires the trusted main push context")
    source_sha = os.environ.get("GITHUB_SHA", "")
    policy = AttestationPolicy("kotoba-lang/amu", REPO_ID, WORKFLOW, "refs/heads/main",
                               source_sha, source_sha, "push")
    with tempfile.TemporaryDirectory(prefix="bounded-cache-", dir=os.environ.get("RUNNER_TEMP")) as temp:
        root = Path(temp)
        image, objects, image_digest, bundle_digest = verified_extract(artifact, gh, GH_SHA256, policy, root / "bundle")
        exercise(image, objects, image_digest, root)
        print("PASS_ATTESTED_BOUNDED_PRODUCER_AND_FRESH_PROBE", bundle_digest, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--gh", type=Path, required=True)
    args = parser.parse_args()
    main(args.artifact, args.gh)
