#!/usr/bin/env python3
"""Stage a pinned static gh image from its pinned release archive."""
import argparse
import hashlib
import os
import tarfile
from pathlib import Path

from check_bounded_producer_attestation import GH_SHA256
from sealed_image import sealed_image

ARCHIVE_SHA256 = "4c806978ffce1cec70853302a56d70ac6da4f19bae7adca4e1a8ab00633dd91d"
MEMBER = "gh_2.103.3_linux_amd64/bin/gh"
LIMIT = 128 * 1024 * 1024


def stage(archive, output):
    archive, output = Path(archive), Path(output)
    with sealed_image(archive, ARCHIVE_SHA256) as (fd, _):
        if os.fstat(fd).st_size > 32 * 1024 * 1024:
            raise ValueError("verifier archive exceeds size limit")
        os.lseek(fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(fd), "rb") as source, tarfile.open(fileobj=source, mode="r:gz") as tar:
            members = [m for m in tar if m.name == MEMBER]
            if len(members) != 1 or not members[0].isfile() or not 0 < members[0].size <= LIMIT:
                raise ValueError("invalid verifier member")
            stream = tar.extractfile(members[0])
            if stream is None:
                raise ValueError("missing verifier bytes")
            data = stream.read(LIMIT + 1)
    if hashlib.sha256(data).hexdigest() != GH_SHA256:
        raise ValueError("verifier image digest mismatch")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o500)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fchmod(out.fileno(), 0o500)
            os.fsync(out.fileno())
    except BaseException:
        output.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stage(args.archive, args.output)
