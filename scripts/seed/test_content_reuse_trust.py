#!/usr/bin/env python3
"""The orchestration cache must not turn untrusted bytes into a verdict."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from content_reuse import Runs, pin


class UntrustedStoreTest(unittest.TestCase):
    def test_store_does_not_publish_process_verdict_or_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out"
            out.mkdir()
            store = root / "store"
            script = root / "producer.sh"
            script.write_text('printf fresh > "$1"\nprintf executed\n')
            output = out / "image"
            runner = Runs(out, store=store)
            runner.run_cached("compile", ["/bin/sh", script, output], {}, [output])
            entry = next(store.iterdir())
            self.assertEqual({p.name for p in entry.iterdir()}, {"image", "record.json"})
            self.assertNotIn("exit", json.loads((entry / "record.json").read_text()))
            self.assertEqual((out / "raw/compile.stdout").read_bytes(), b"executed")

    def test_forged_record_and_rewritten_hash_do_not_replace_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out"
            out.mkdir()
            store = root / "store"
            store.mkdir()
            script = root / "producer.sh"
            script.write_text('printf fresh > "$1"\nprintf executed\n')
            output = out / "image"
            argv = ["/bin/sh", script, output]
            runner = Runs(out, reuse=store)
            material = runner.key_material(argv, {}, [output])
            key = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
            entry = store / key
            entry.mkdir()
            (entry / "image").write_bytes(b"forged")
            (entry / "stdout").write_bytes(b"forged success")
            (entry / "stderr").write_bytes(b"")
            (entry / "record.json").write_text(json.dumps({
                "key": key, "material": material, "exit": 0, "from": "forged",
                "outputs": {"image": pin(entry / "image")},
            }))

            runner.run_cached("compile", argv, {}, [output])

            self.assertEqual(output.read_bytes(), b"fresh")
            self.assertEqual((out / "raw/compile.stdout").read_bytes(), b"executed")
            self.assertNotIn("reused", runner.calls[0])


if __name__ == "__main__":
    unittest.main()
