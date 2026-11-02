#!/usr/bin/env python3
"""Verify the experimental producer built by the main push workflow.

This verifies artifact origin only. Source identity, resource proof and
production/shared-cache admission remain separate native qualifications.
"""
import argparse
import os
from pathlib import Path

from verified_attestation import AttestationPolicy, verified_artifact

GH_SHA256 = "b768184570b12536be4ac1528893f6340d1c6a7b40b56ad45bca9cd0e87ad34d"
REPO_ID = "1297097065"
WORKFLOW = ".github/workflows/bounded-cache-producer.yml"


def main(artifact, gh):
    if (os.environ.get("GITHUB_REPOSITORY") != "kotoba-lang/amu" or
        os.environ.get("GITHUB_REPOSITORY_ID") != REPO_ID or
        os.environ.get("GITHUB_REF") != "refs/heads/main" or
        os.environ.get("GITHUB_EVENT_NAME") != "push"):
        raise ValueError("producer verification requires the trusted main push context")
    source_sha = os.environ.get("GITHUB_SHA", "")
    policy = AttestationPolicy("kotoba-lang/amu", REPO_ID, WORKFLOW, "refs/heads/main",
                               source_sha, source_sha, "push")
    with verified_artifact(artifact, gh, GH_SHA256, policy) as (fd, digest):
        if os.read(fd, 4) != b"\x7fELF":
            raise ValueError("attested candidate is not an ELF image")
        print("PASS_ATTESTED_BOUNDED_PRODUCER", digest, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--gh", type=Path, required=True)
    args = parser.parse_args()
    main(args.artifact, args.gh)
