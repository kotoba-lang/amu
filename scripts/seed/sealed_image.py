"""Bind a Linux process launch to immutable executable bytes.

The expected digest must come from a separately trusted source. This helper
does not authenticate the origin of that digest or qualify compiler inputs.
"""
import fcntl
import hashlib
import hmac
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path

MAX_IMAGE_BYTES = 128 * 1024 * 1024
SEALS = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL


@contextmanager
def sealed_image(path, expected_sha256):
    """Yield (fd, digest) for the verified, sealed bytes; caller must pass fd.

    Execute /proc/self/fd/<fd> with pass_fds=(fd,) while inside this context.
    A cache record or a caller-selected digest is not a trusted authority.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("invalid trusted image digest")
    with sealed_blob(path) as (fd, actual):
        if not hmac.compare_digest(actual, expected_sha256):
            raise ValueError("image digest mismatch")
        yield fd, actual


@contextmanager
def sealed_blob(path):
    """Yield immutable bytes and their digest; this does not authenticate them."""
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    source = os.open(Path(path), flags)
    fd = -1
    try:
        if not stat.S_ISREG(os.fstat(source).st_mode):
            raise ValueError("image must be a regular file")
        fd = os.memfd_create("kotoba-verified-image", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        length = 0
        while True:
            chunk = os.read(source, 1024 * 1024)
            if not chunk:
                break
            length += len(chunk)
            if length > MAX_IMAGE_BYTES:
                raise ValueError("image exceeds size limit")
            remaining = memoryview(chunk)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise OSError("short image write")
                remaining = remaining[written:]
        os.fchmod(fd, 0o500)
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, SEALS)
        if fcntl.fcntl(fd, fcntl.F_GET_SEALS) & SEALS != SEALS:
            raise OSError("image sealing failed")
        # Hash after sealing so the digest identifies the exact immutable
        # bytes that exec will see, even if the source changed during copying.
        os.lseek(fd, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        actual = digest.hexdigest()
        yield fd, actual
    finally:
        os.close(source)
        if fd >= 0:
            os.close(fd)
