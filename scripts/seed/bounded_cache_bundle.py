"""Transport a bounded native object fixture; never transport gate verdicts."""
import fcntl
import hashlib
import os
import re
import shutil
import stat
import tarfile
from pathlib import Path

from sealed_image import MAX_IMAGE_BYTES, SEALS
from verified_attestation import verified_artifact

OBJECT = re.compile(r"objects/[0-9a-f]{64}\.kdo")
MAX_OBJECTS = 512
MAX_OBJECT_BYTES = 4 * 1024 * 1024


def _private(path, directory):
    info = os.lstat(path)
    if (info.st_uid != os.geteuid() or
        not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)) or
        stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o400)):
        raise ValueError("object store must be private and compiler-owned")


def pack(producer, cache, destination):
    """Pack only a producer image and private .kdo files; never a receipt."""
    producer, cache, destination = Path(producer), Path(cache), Path(destination)
    _private(cache, True)
    objects = sorted(cache.iterdir())
    if not objects or len(objects) > MAX_OBJECTS:
        raise ValueError("invalid object count")
    entries = [(producer, "producer.elf", MAX_IMAGE_BYTES, 0o500)]
    for path in objects:
        if not OBJECT.fullmatch("objects/" + path.name):
            raise ValueError("unexpected cache entry")
        _private(path, False)
        entries.append((path, "objects/" + path.name, MAX_OBJECT_BYTES, 0o400))
    created = False
    try:
        with destination.open("xb") as out:
            created = True
            os.fchmod(out.fileno(), 0o600)
            total = 0
            with tarfile.open(fileobj=out, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                for path, name, limit, mode in entries:
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
                    with os.fdopen(fd, "rb") as source:
                        info = os.fstat(fd)
                        if not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size > limit:
                            raise ValueError("invalid artifact file")
                        total += info.st_size
                        if total > MAX_IMAGE_BYTES:
                            raise ValueError("bundle contents exceed size limit")
                        if mode == 0o400 and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o400):
                            raise ValueError("object changed while opening")
                        row = tarfile.TarInfo(name)
                        row.size, row.mode, row.mtime, row.uid, row.gid = info.st_size, mode, 0, 0, 0
                        tar.addfile(row, source)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    if destination.stat().st_size > MAX_IMAGE_BYTES:
        destination.unlink()
        raise ValueError("bundle exceeds size limit")


def _extract_sealed(fd, destination):
    """Extract an already authenticated, sealed fd into a new private path."""
    if fcntl.fcntl(fd, fcntl.F_GET_SEALS) & SEALS != SEALS:
        raise ValueError("bundle is not sealed")
    destination = Path(destination)
    destination.mkdir(mode=0o700)
    os.chmod(destination, 0o700)
    try:
        objects = destination / "objects"
        objects.mkdir(mode=0o700)
        os.chmod(objects, 0o700)
        seen = set()
        total = 0
        image_digest = None
        os.lseek(fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(fd), "rb") as source, tarfile.open(fileobj=source, mode="r|") as tar:
            for row in tar:
                name = row.name
                is_image = name == "producer.elf"
                if (not row.isfile() or (not is_image and not OBJECT.fullmatch(name)) or name in seen or
                    row.size <= 0 or row.size > (MAX_IMAGE_BYTES if is_image else MAX_OBJECT_BYTES)):
                    raise ValueError("invalid bundle entry")
                seen.add(name)
                if len(seen) > MAX_OBJECTS + 1:
                    raise ValueError("too many bundle entries")
                total += row.size
                if total > MAX_IMAGE_BYTES:
                    raise ValueError("bundle contents exceed size limit")
                target = destination / name
                handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(handle, "wb") as out:
                    data = tar.extractfile(row)
                    if data is None:
                        raise ValueError("missing bundle bytes")
                    hasher = hashlib.sha256()
                    while True:
                        chunk = data.read(1024 * 1024)
                        if not chunk:
                            break
                        hasher.update(chunk)
                        out.write(chunk)
                    if is_image:
                        image_digest = hasher.hexdigest()
                os.chmod(target, 0o500 if is_image else 0o400)
        if "producer.elf" not in seen or len(seen) < 2:
            raise ValueError("bundle must contain a producer and objects")
    except BaseException:
        shutil.rmtree(destination)
        raise
    return destination / "producer.elf", objects, image_digest


def verified_extract(bundle, gh, gh_sha256, policy, destination):
    """Authenticate the sealed archive before touching its member paths."""
    with verified_artifact(bundle, gh, gh_sha256, policy) as (fd, digest):
        image, objects, image_digest = _extract_sealed(fd, destination)
        return image, objects, image_digest, digest


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pack(args.producer, args.cache, args.output)
