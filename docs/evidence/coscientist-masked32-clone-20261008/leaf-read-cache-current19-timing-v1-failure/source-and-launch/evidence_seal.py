"""Measurement evidence identity guard; no production cache or reuse authorization.

Full byte checks establish a local snapshot. Metadata checks detect ordinary
filesystem writes between full checks. Kernel metadata and absence of privileged
metadata forgery are assumptions; this is not protection against a privileged host.
"""
import hashlib
import os
from pathlib import Path
import re
import stat


class SealError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise SealError(message)


def fingerprint(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns,
            s.st_mode, s.st_uid, s.st_gid, s.st_nlink)


class Seal:
    def __init__(self, refs, maximum_files=8192, maximum_bytes=448 * 1024**2):
        require(type(maximum_files) is int and maximum_files > 0 and
                type(maximum_bytes) is int and maximum_bytes > 0, 'finite budgets')
        self.refs = tuple(dict(r) for r in refs)
        require(len(self.refs) <= maximum_files, 'logical file budget')
        self.paths = {}
        total = 0
        for r in self.refs:
            require(set(r) == {'path', 'bytes', 'sha256'}, 'exact reference schema')
            p, n, h = r['path'], r['bytes'], r['sha256']
            require(type(p) is str and Path(p).is_absolute() and str(Path(p)) == p
                    and '..' not in Path(p).parts, 'canonical absolute input path')
            require(type(n) is int and 0 <= n <= maximum_bytes, 'input byte bound')
            require(type(h) is str and re.fullmatch('[0-9a-f]{64}', h), 'exact SHA256')
            total += n
            require(total <= maximum_bytes, 'logical byte budget')
            require(p not in self.paths or self.paths[p] == r, 'conflicting duplicate path')
            self.paths[p] = dict(r)
        # Duplicate references retain their logical cost; hash each physical path once.
        self.logical_bytes = total
        self._identities = None

    def _stat(self, path):
        s = os.lstat(path)
        require(stat.S_ISREG(s.st_mode), 'regular non-symlink input: ' + path)
        require(s.st_size == self.paths[path]['bytes'], 'exact input size: ' + path)
        return fingerprint(s)

    def _digest(self, path, expected_identity):
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
        fd = os.open(path, flags)
        try:
            require(fingerprint(os.fstat(fd)) == expected_identity, 'open identity changed')
            digest = hashlib.sha256()
            remaining = self.paths[path]['bytes']
            while remaining:
                b = os.read(fd, min(1024 * 1024, remaining))
                require(bool(b), 'short input read')
                digest.update(b)
                remaining -= len(b)
            require(os.read(fd, 1) == b'', 'input grew')
            require(fingerprint(os.fstat(fd)) == expected_identity, 'read identity changed')
            require(self._stat(path) == expected_identity, 'path identity changed')
            require(digest.hexdigest() == self.paths[path]['sha256'], 'input SHA256 changed')
        finally:
            os.close(fd)

    def full(self):
        observed = {p: self._stat(p) for p in self.paths}
        if self._identities is not None:
            require(observed == self._identities, 'sealed identity changed before full check')
        for p, identity in observed.items():
            self._digest(p, identity)
        require({p: self._stat(p) for p in self.paths} == observed,
                'cross-file snapshot changed during full check')
        # Publish only after every hash and both identity checks succeed.
        self._identities = observed
        return self.receipt()

    def check(self):
        require(self._identities is not None, 'no complete initial seal')
        require({p: self._stat(p) for p in self.paths} == self._identities,
                'sealed metadata changed')

    def receipt(self):
        require(self._identities is not None, 'no complete seal receipt')
        return {'logicalFiles': len(self.refs), 'logicalBytes': self.logical_bytes,
                'uniquePhysicalPaths': len(self.paths),
                'fingerprintFields': ['dev', 'ino', 'size', 'mtime_ns', 'ctime_ns',
                                      'mode', 'uid', 'gid', 'nlink'],
                'files': [{'reference': self.paths[p], 'fingerprint': list(identity)}
                          for p, identity in self._identities.items()]}
