"""Small macOS FD diagnostic; mutates only its own temporary directory.

This exercises libc fstatat64 and Python FD operations, not the native helper.
"""
import ctypes
import os
import stat
import tempfile


def main():
    lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    fstatat = lib.fstatat64
    fstatat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int]
    fstatat.restype = ctypes.c_int
    flags = 0x20 | 0x800 | 0x2000
    with tempfile.TemporaryDirectory(prefix='awai149-flint-fstatat-') as root:
        os.chmod(root, 0o700)
        os.mkdir(root + '/.kapitsa', 0o700)
        open_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(root, open_flags)
        child_fd = -1
        try:
            child_fd = os.open('.kapitsa', open_flags, dir_fd=parent_fd)
            def sample(name):
                buf = ctypes.create_string_buffer(256)
                ctypes.set_errno(0)
                result = fstatat(parent_fd, name.encode(), buf, flags)
                raw = buf.raw
                return (result, ctypes.get_errno(), int.from_bytes(raw[0:4], 'little'),
                        int.from_bytes(raw[4:6], 'little'), int.from_bytes(raw[8:16], 'little'))

            expected = os.fstat(child_fd)
            initial = sample('.kapitsa')
            os.rename(root + '/.kapitsa', root + '/old')
            os.mkdir(root + '/.kapitsa', 0o700)
            replaced = sample('.kapitsa')
            os.symlink('old', root + '/link')
            link = sample('link')
            good = (initial[0] == 0 and stat.S_ISDIR(initial[3]) and
                    (initial[2], initial[4]) == (expected.st_dev, expected.st_ino))
            changed = (replaced[0] == 0 and
                       (replaced[2], replaced[4]) != (expected.st_dev, expected.st_ino))
            link_seen = link[0] == 0 and stat.S_ISLNK(link[3]) and not stat.S_ISDIR(link[3])
            print('initial_match', good, 'replacement_detected', changed,
                  'symlink_metadata', link_seen, 'symlink_rc', link[0], flush=True)
            if not (good and changed and link_seen):
                raise SystemExit(1)
        finally:
            if child_fd >= 0:
                os.close(child_fd)
            os.close(parent_fd)
    print('PROBE_END', flush=True)


if __name__ == '__main__':
    main()
