"""Content-addressed reuse for the selfhost orchestration scripts.

A stored result may stand in for a call only when its key matches exactly: the
sha256 of every existing file the call's argv names (the producing image
first, then its inputs), the argv and the full environment (the output
directory written as $OUT), the host and the declared outputs. A hit restores
the outputs and verifies them against the recorded pins; anything different
reruns the call. Python only orchestrates processes and hashes.
"""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
RUN_PATH = "/usr/bin:/bin"
# Bump when the meaning of a reuse record changes.
REUSE_VERSION = 1
SCRIPTS = ("scripts/seed/content_reuse.py", "scripts/seed/selfhost-bootstrap.py", "scripts/seed/check-x86_64-native.py")
ROOT_IMAGE = "seed/bootstrap/aarch64-linux-static-root.elf"
MANIFESTS = ("seed/X86_64-LINUX-SELFHOST-MANIFEST", "seed/CORE-STATIC-MANIFEST", "seed/MANIFEST")


def pin(p):
    data = Path(p).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class Runs:
    def __init__(self, out, reuse=None, store=None):
        self.out, self.calls, self.reuse, self.store = out, [], reuse, store
        (out / "raw").mkdir(exist_ok=True)

    def _record(self, call):
        self.calls.append(call)
        (self.out / "calls.json").write_text(json.dumps(self.calls, indent=1) + "\n")

    def run(self, name, argv, env, success=True, timeout=3600):
        argv = list(map(str, argv))
        t = time.monotonic()
        r = subprocess.run(argv, cwd=self.out, env={"PATH": RUN_PATH, **env}, capture_output=True, timeout=timeout)
        (self.out / "raw" / (name + ".stdout")).write_bytes(r.stdout)
        (self.out / "raw" / (name + ".stderr")).write_bytes(r.stderr)
        self._record(dict(name=name, argv=argv, env=env, exit=r.returncode, seconds=round(time.monotonic() - t, 1)))
        if success:
            assert r.returncode == 0 and not r.stderr, (name, r.returncode, r.stderr.decode(errors="replace"))
        return r

    def key_material(self, argv, env, outputs):
        """Every input byte of a call: the sha256 of each existing file its argv
        names (the producing image first), the argv and the full environment
        with the output directory written as $OUT, and the declared outputs."""
        norm = lambda v: str(v).replace(str(self.out), "$OUT")
        files = {norm(a): pin(a) for a in map(Path, map(str, argv)) if a.is_absolute() and a.is_file()}
        assert norm(argv[0]) in files, "the producing image must be a file"
        return dict(version=REUSE_VERSION, host=[platform.system(), platform.machine()], argv=[norm(a) for a in argv],
                    env={k: norm(v) for k, v in sorted({"PATH": RUN_PATH, **env}.items())},
                    inputs=files, outputs=sorted(norm(o) for o in outputs))

    def run_cached(self, name, argv, env, outputs, timeout=3600):
        """run(), or the content-addressed result of the identical call. The key
        covers every input byte (key_material); a hit restores the recorded
        outputs and verifies their pins. Anything different reruns the call."""
        material = self.key_material(argv, env, outputs)
        key = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
        entry = self.reuse / key if self.reuse else None
        if entry and (entry / "record.json").is_file():
            record = json.loads((entry / "record.json").read_text())
            assert record["key"] == key and record["material"] == material, (name, "reuse record does not match its key")
            for o in outputs:
                stored = entry / Path(o).name
                assert pin(stored) == record["outputs"][Path(o).name], (name, "reused output drift", o)
                shutil.copyfile(stored, o)
            for stream in ("stdout", "stderr"):
                (self.out / "raw" / f"{name}.{stream}").write_bytes((entry / stream).read_bytes())
            assert record["exit"] == 0 and not (entry / "stderr").read_bytes(), name
            reused = dict(key=key, **{"from": record["from"]})
            self._record(dict(name=name, argv=list(map(str, argv)), env=env, exit=0, seconds=0, reused=reused))
            return reused
        r = self.run(name, argv, env, timeout=timeout)
        self.calls[-1]["key"] = key
        if self.store:
            entry = self.store / key
            entry.mkdir(parents=True, exist_ok=True)
            for o in outputs:
                shutil.copyfile(o, entry / Path(o).name)
            (entry / "stdout").write_bytes(r.stdout)
            (entry / "stderr").write_bytes(r.stderr)
            origin = {k: os.environ[k] for k in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_EVENT_NAME")
                      if k in os.environ} or "local"
            (entry / "record.json").write_text(json.dumps(dict(key=key, material=material, exit=r.returncode, **{"from": origin},
                                                               outputs={Path(o).name: pin(o) for o in outputs}), indent=1) + "\n")
        return None


def lookup_key(root):
    """A CI cache lookup hint, not the reuse key: the orchestration scripts and
    every source and image the reusable calls derive from (the pinned root, the
    selfhost closure that builds S3 and S-x86_64, the core-static and adopted
    unities). The exact per-call key is still checked by Runs.run_cached."""
    h = hashlib.sha256()
    for p in [*(root / s for s in SCRIPTS), root / ROOT_IMAGE]:
        h.update(hashlib.sha256(p.read_bytes()).digest())
    for manifest in MANIFESTS:
        for p in [manifest, *(l for l in (root / manifest).read_text().splitlines() if l and not l.startswith("#"))]:
            h.update(p.encode() + b"\0" + hashlib.sha256((root / p).read_bytes()).digest())
    return h.hexdigest()




if __name__ == "__main__":
    assert sys.argv[1:] == ["--lookup-key"], "usage: content_reuse.py --lookup-key"
    print(lookup_key(Path(__file__).resolve().parents[2]))
