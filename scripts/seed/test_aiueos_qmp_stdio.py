#!/usr/bin/env python3
"""Exercise QMP pipe framing and deadlines without starting a guest."""
import importlib.util
import os
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location(
    "aiueos_entry_qemu", Path(__file__).with_name("check-aiueos-entry-qemu.py"))
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


class QmpStdioTests(unittest.TestCase):
    def setUp(self):
        read_fd, self.write_fd = os.pipe()
        self.reader = os.fdopen(read_fd, "rb", buffering=0)
        self.writer = open(os.devnull, "wb", buffering=0)
        self.stream = observer.QmpStdio(
            SimpleNamespace(stdout=self.reader, stdin=self.writer), reply_timeout=0.1)

    def tearDown(self):
        if self.write_fd is not None:
            os.close(self.write_fd)
        self.stream.close()

    def test_partial_line_times_out_with_pipe_still_open(self):
        os.write(self.write_fd, b"{")
        started = time.monotonic()
        with self.assertRaisesRegex(AssertionError, "reply timeout"):
            self.stream.readline()
        self.assertLess(time.monotonic() - started, 2)

    def test_no_reply_times_out(self):
        with self.assertRaisesRegex(AssertionError, "reply timeout"):
            self.stream.readline()

    def test_split_line_is_reassembled(self):
        os.write(self.write_fd, b'{"QMP":')
        def finish():
            time.sleep(0.01)
            os.write(self.write_fd, b' {}}\r\n')
        thread = threading.Thread(target=finish)
        thread.start()
        try:
            self.assertEqual(self.stream.readline(), b'{"QMP": {}}\r\n')
        finally:
            thread.join()

    def test_buffered_second_line_needs_no_new_pipe_bytes(self):
        os.write(self.write_fd, b'one\ntwo\n')
        self.assertEqual(self.stream.readline(), b'one\n')
        self.assertEqual(self.stream.readline(), b'two\n')

    def test_partial_eof_refuses(self):
        os.write(self.write_fd, b'{')
        os.close(self.write_fd)
        self.write_fd = None
        with self.assertRaisesRegex(AssertionError, "stdio closed"):
            self.stream.readline()


if __name__ == "__main__":
    unittest.main()
