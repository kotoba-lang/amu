#!/usr/bin/env python3
"""Compare descriptor source unity with bytes at a specified Git commit.

This audits tree content only. A match does not establish how a compiler image
was built, qualification, or release readiness; it never changes descriptors.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r"[0-9a-f]{40}\Z")
PATH = re.compile(r"seed/[A-Za-z0-9_.-]+\.kotoba\Z")


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def commit(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError("revision must be a full lowercase 40-character commit")
    resolved = git("rev-parse", "--verify", value + "^{commit}").decode().strip()
    if resolved != value:
        raise ValueError("revision did not resolve to itself")
    return value


def blob(revision, path):
    return git("show", revision + ":" + path)


def audit(descriptor_revision, source_override):
    descriptor_revision = commit(descriptor_revision)
    d = json.loads(blob(descriptor_revision, "native-product.json"))
    source_revision = commit(source_override if source_override is not None else d["sourceRevision"])
    if d["sourceManifest"] != "seed/FULL-MANIFEST":
        raise ValueError("unexpected manifest path")
    lines = blob(descriptor_revision, d["sourceManifest"]).decode("utf-8").splitlines()
    paths = [line for line in lines if line and not line.startswith("#")]
    if (not paths or len(paths) != d["sourceModuleCount"] or len(paths) != len(set(paths))
            or any(not PATH.fullmatch(path) for path in paths)):
        raise ValueError("manifest paths, duplicates or module count invalid")
    digest = hashlib.sha256()
    size = 0
    for path in paths:
        data = blob(source_revision, path) + b"\n"
        digest.update(data)
        size += len(data)
    actual = {"bytes": size, "sha256": digest.hexdigest()}
    expected = d["sourceUnity"]
    matched = actual == expected
    return {"status": "MATCH" if matched else "MISMATCH", "descriptorRevision": descriptor_revision,
            "descriptorSourceRevision": d["sourceRevision"], "sourceRevisionTested": source_revision,
            "modules": len(paths), "expectedUnity": expected, "actualUnity": actual,
            "compilerBuildProvenanceVerified": False, "publicReleaseQualified": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--descriptor-revision", required=True)
    p.add_argument("--source-revision", help="compare a different full Git commit")
    args = p.parse_args()
    try:
        result = audit(args.descriptor_revision, args.source_revision)
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as e:
        print(json.dumps({"status": "REFUSED", "reason": str(e)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
