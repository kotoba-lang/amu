"""Linux process observations only; never supplies a native gate verdict.

The controller and its sealed children run with their original argv/env/limits.
No ptrace, injected code, native format writer or controller change is needed.
Phase edges are polling observations, not instruction-level instrumentation.
"""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def proc_stat(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        hz = os.sysconf("SC_CLK_TCK")
        return dict(state=fields[0], parent=int(fields[1]),
                    selfCPU=(int(fields[11]) + int(fields[12])) / hz,
                    childrenCPU=(int(fields[13]) + int(fields[14])) / hz,
                    startTicks=int(fields[19]), rssBytes=int(fields[21]) * os.sysconf("SC_PAGE_SIZE"))
    except (FileNotFoundError, ProcessLookupError):
        return None


def child_role(pid):
    try:
        argv0 = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0", 1)[0]
        return {b"amu-selfhost.elf": "amu-rebuild", b"kotoba-native.elf": "kotoba-gate"}.get(
            argv0.rsplit(b"/", 1)[-1])
    except (FileNotFoundError, ProcessLookupError):
        return None


def observe_controller(argv, *, cwd, env, timeout, output, interval=0.05):
    """Return CompletedProcess while separately recording diagnostic timing.

    wait4 retains final CPU usage including reaped descendants. /proc samples
    divide the two direct native children; cumulative child CPU is assigned
    only after the controller actually reaps them. The residual is the native
    controller's own CPU, including hashes, IO and wait supervision.
    """
    if not Path("/proc/self/stat").exists():
        raise RuntimeError("Linux /proc required for controller profiling")
    if interval <= 0 or interval > 0.1:
        raise ValueError("sampling interval must be in (0, 0.1]")
    output = Path(output)
    started = time.monotonic()
    phases = []
    children = {}
    phase = "preflight"
    phase_start = 0.0
    parent_last = dict(selfCPU=0.0, childrenCPU=0.0)
    reaped_cpu = 0.0
    departed = []
    final_usage = None
    returncode = None
    report = dict(schema="amu.native-controller-profile.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, pollIntervalSeconds=interval,
                  observerSourceSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  status="RUNNING", phases=phases, children=[],
                  hostCPUs=os.cpu_count(), loadStart=list(os.getloadavg()))

    def snapshot(elapsed, status):
        report.update(status=status, elapsedSeconds=elapsed,
                      activePhase=phase, phases=phases + [dict(name=phase, startSeconds=phase_start,
                                                              seconds=elapsed - phase_start)],
                      children=list(children.values()), parentSample=parent_last)
        atomic_json(output, report)

    # Files prevent pipe backpressure while the observer samples. They carry
    # the same stdout/stderr bytes the existing gate harness already records.
    stdout_path = output.with_suffix(".stdout")
    stderr_path = output.with_suffix(".stderr")
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(list(map(str, argv)), cwd=cwd, env=env, stdout=stdout, stderr=stderr)
        last_write = -10.0
        try:
            while True:
                elapsed = time.monotonic() - started
                parent = proc_stat(process.pid)
                active = None
                if parent:
                    parent_last = parent
                    try:
                        pids = Path(f"/proc/{process.pid}/task/{process.pid}/children").read_text().split()
                    except (FileNotFoundError, ProcessLookupError):
                        pids = []
                    seen = set()
                    for pid in pids:
                        state = proc_stat(pid)
                        role = child_role(pid)
                        if state is None or role is None:
                            continue
                        key = f"{pid}:{state['startTicks']}"
                        seen.add(key)
                        row = children.setdefault(key, dict(role=role, firstSeenSeconds=elapsed,
                                                          lastSeenSeconds=elapsed, sampledCPUSeconds=0.0,
                                                          peakRSSBytes=0, reaped=False))
                        row.update(lastSeenSeconds=elapsed, sampledCPUSeconds=state["selfCPU"] + state["childrenCPU"],
                                   peakRSSBytes=max(row["peakRSSBytes"], state["rssBytes"]))
                        active = role
                    for key, row in children.items():
                        if key not in seen and not row.get("departed"):
                            row["departed"] = True
                            row["departureObservedSeconds"] = elapsed
                            departed.append(row)
                    if parent["childrenCPU"] > reaped_cpu and departed:
                        row = departed.pop(0)
                        row.update(reaped=True, reapedCPUSeconds=parent["childrenCPU"] - reaped_cpu)
                        reaped_cpu = parent["childrenCPU"]
                if active is None:
                    roles = {row["role"] for row in children.values()}
                    active = ("receipt-finalization" if "kotoba-gate" in roles else
                              "post-rebuild-verification" if "amu-rebuild" in roles else "preflight")
                if active != phase:
                    phases.append(dict(name=phase, startSeconds=phase_start, seconds=elapsed - phase_start))
                    phase, phase_start = active, elapsed
                    snapshot(elapsed, "RUNNING")
                pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                if pid:
                    returncode = os.waitstatus_to_exitcode(status)
                    process.returncode = returncode
                    final_usage = usage
                    break
                if elapsed >= timeout:
                    process.kill()
                    _, status, usage = os.wait4(process.pid, 0)
                    process.returncode = os.waitstatus_to_exitcode(status)
                    final_usage = usage
                    snapshot(time.monotonic() - started, "TIMEOUT")
                    raise subprocess.TimeoutExpired(argv, timeout)
                if elapsed - last_write >= 5:
                    snapshot(elapsed, "RUNNING")
                    last_write = elapsed
                time.sleep(interval)
        except BaseException as error:
            if process.returncode is None:
                process.kill()
                _, status, _ = os.wait4(process.pid, 0)
                process.returncode = os.waitstatus_to_exitcode(status)
            snapshot(time.monotonic() - started, "TIMEOUT" if isinstance(error, subprocess.TimeoutExpired)
                     else "OBSERVER_INTERRUPTED")
            raise
    elapsed = time.monotonic() - started
    total_cpu = final_usage.ru_utime + final_usage.ru_stime
    remaining_cpu = total_cpu - parent_last["selfCPU"] - reaped_cpu
    unaccounted = [row for row in children.values() if not row["reaped"]]
    if len(unaccounted) == 1 and remaining_cpu >= 0:
        row = unaccounted[0]
        row.update(reaped=True, reapedCPUSeconds=remaining_cpu, finalWait4Residual=True,
                   cpuResidualIncludesControllerFinalSamplingInterval=True)
        reaped_cpu += remaining_cpu
    report.update(exit=returncode, totalCPUSeconds=total_cpu,
                  controllerCPUSeconds=total_cpu - reaped_cpu, reapedChildrenCPUSeconds=reaped_cpu,
                  maxRSSKiB=final_usage.ru_maxrss, loadEnd=list(os.getloadavg()),
                  phaseEdges="/proc polling; <= one sampling interval plus observer scheduling per edge",
                  cpuAccounting="wait4 process+reaped descendants; child boundaries from controller /proc cutime/cstime")
    report["completePhaseObservation"] = ({row["role"] for row in children.values()} ==
                                          {"amu-rebuild", "kotoba-gate"})
    snapshot(elapsed, "COMPLETED")
    return subprocess.CompletedProcess(argv, returncode, stdout_path.read_bytes(), stderr_path.read_bytes())
