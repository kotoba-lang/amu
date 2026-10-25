"""Bound native build admission across cooperating processes/worktrees.

This is process scheduling, not compilation or native qualification. A held
flock is inherited by the launched harness, and kernel cleanup releases it.
Existing unmanaged builds are reported separately; they are never stopped.
"""
import argparse
import concurrent.futures
import contextlib
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from native_process_profile import atomic_json


def default_slot_dir():
    if os.environ.get("KOTOBA_NATIVE_SLOT_DIR"):
        return Path(os.environ["KOTOBA_NATIVE_SLOT_DIR"])
    if os.environ.get("RUNNER_TEMP"):
        return Path(os.environ["RUNNER_TEMP"]) / "native-build-slots"
    return Path.home() / "github/workspaces/codex/native-build-slots-v1"


@contextlib.contextmanager
def build_slot(directory, capacity=2):
    if capacity < 1 or capacity > 64:
        raise ValueError("slot capacity must be 1..64")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "capacity.lock").open("a+") as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        config = directory / "capacity.json"
        if config.exists():
            if json.loads(config.read_text())["slots"] != capacity:
                raise ValueError("shared slot capacity mismatch; use the existing capacity")
        else:
            atomic_json(config, dict(slots=capacity))
    started = time.monotonic()
    while True:
        for index in range(capacity):
            handle = (directory / f"slot-{index}.lock").open("a+")
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                continue
            try:
                # The command inherits the descriptor. If the outer wrapper is
                # killed, its still-running harness keeps its admission slot.
                yield handle, dict(slot=index, capacity=capacity,
                                   queuedSeconds=time.monotonic() - started)
            finally:
                # Do not explicitly LOCK_UN: the child may still hold this
                # same open-file description after an interrupted wrapper.
                handle.close()
            return
        time.sleep(0.1)


def execute(argv, *, directory, capacity=2, stdout=None, stderr=None, cwd=None, env=None):
    started = time.monotonic()
    with build_slot(directory, capacity) as (handle, admission):
        admitted = time.monotonic()
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                                 pass_fds=(handle.fileno(),), start_new_session=True)
        try:
            code = child.wait()
        except BaseException:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            raise
    return dict(**admission, exit=code, runSeconds=time.monotonic() - admitted,
                totalSeconds=time.monotonic() - started)


def plan_jobs(manifest, phase, environment):
    data = json.loads(Path(manifest).read_text())
    if data["schema"] != "amu.native-gate-plan.v1":
        raise ValueError("unknown native gate plan")
    rows = data["phases"][phase]
    names = [row["name"] for row in rows]
    if len(names) != len(set(names)):
        raise ValueError("duplicate gate names")
    # Only substitute complete argv tokens, never splice data into shell code.
    values = {"@TEMP@": environment["RUNNER_TEMP"]}
    result = []
    for row in rows:
        argv = []
        for token in row["argv"]:
            for key, value in values.items():
                token = token.replace(key, value)
            argv.append(token)
        result.append(dict(name=row["name"], argv=argv))
    return result


def run_plan(manifest, phase, output, *, jobs=2, capacity=2, directory=None):
    if jobs < 1 or jobs > capacity:
        raise ValueError("jobs must be 1..shared capacity")
    gates = plan_jobs(manifest, phase, os.environ)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema="amu.native-gate-scheduling.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, jobs=jobs, capacity=capacity,
                  phase=phase, status="RUNNING", gates=[])
    started = time.monotonic()
    atomic_json(output / "schedule.json", report)

    def run(row):
        name = row["name"]
        if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name):
            raise ValueError("invalid gate name")
        with (output / (name + ".log")).open("wb") as log:
            timing = execute(row["argv"], directory=directory or default_slot_dir(),
                             capacity=capacity, stdout=log, stderr=subprocess.STDOUT)
        (output / (name + ".rc")).write_text(str(timing["exit"]) + "\n")
        return dict(name=name, argv=row["argv"], **timing)

    # Every submitted gate is awaited even if another fails. No lost pipeline
    # exit, cancelled assertion, swallowed exception or shared JSON writer.
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(run, row): row for row in gates}
        for future in concurrent.futures.as_completed(futures):
            row = futures[future]
            try:
                result = future.result()
            except Exception as error:
                result = dict(name=row["name"], exit=1, error=type(error).__name__ + ": " + str(error))
            report["gates"].append(result)
            atomic_json(output / "schedule.json", report)
            print(f"{row['name']}: exit={result['exit']}", flush=True)
            log = output / (row["name"] + ".log")
            if log.exists():
                sys.stdout.buffer.write(log.read_bytes())
                sys.stdout.flush()
    report.update(status="COMPLETED", seconds=time.monotonic() - started,
                  exit=0 if all(row["exit"] == 0 for row in report["gates"]) else 1)
    atomic_json(output / "schedule.json", report)
    return report["exit"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slot-dir", type=Path, default=default_slot_dir())
    parser.add_argument("--capacity", type=int, default=2)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--phase")
    parser.add_argument("--output", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.manifest:
        if not args.phase or not args.output or args.command:
            parser.error("plan requires --phase and --output, with no command")
        return run_plan(args.manifest, args.phase, args.output, jobs=args.jobs,
                        capacity=args.capacity, directory=args.slot_dir)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("provide a command after --, or a --manifest plan")
    timing = execute(command, directory=args.slot_dir, capacity=args.capacity)
    if args.output:
        atomic_json(args.output, dict(schema="amu.native-build-admission.v1", **timing))
    print(json.dumps(timing), file=sys.stderr)
    return timing["exit"] if timing["exit"] >= 0 else 128 - timing["exit"]


if __name__ == "__main__":
    raise SystemExit(main())
