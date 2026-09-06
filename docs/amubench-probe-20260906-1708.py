import subprocess, io, datetime

lines = []

# timestamp
lines.append("ts: " + datetime.datetime.now().astimezone().isoformat(timespec="seconds"))

# load via sysctl
try:
    r = subprocess.run(["sysctl", "-n", "vm.loadavg"], capture_output=True, text=True, timeout=15)
    lines.append("load: " + (r.stdout.strip() or "EMPTY stdout; rc=" + str(r.returncode)))
except Exception as e:
    lines.append("load: ERR " + repr(e))

# guard glob that remote-bench.cljs guards (exit 2 on non-empty)
try:
    r = subprocess.run(
        ["git", "status", "--porcelain", "--", "src", "bench", "scripts", "deps.edn"],
        capture_output=True, text=True, timeout=30, cwd="/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu")
    out = r.stdout.splitlines()
    lines.append("guard-glob-lines: " + str(len(out)))
    for l in out[:10]:
        lines.append("  " + l)
except Exception as e:
    lines.append("guard: ERR " + repr(e))

# scripts present?
try:
    r = subprocess.run(["ls", "scripts/quiet-host.cljs", "scripts/remote-bench.cljs"],
                       capture_output=True, text=True, timeout=15,
                       cwd="/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu")
    lines.append("scripts-ls rc: " + str(r.returncode) + " " + r.stderr.strip())
except Exception as e:
    lines.append("ls: ERR " + repr(e))

# HEAD
try:
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True, timeout=15,
                       cwd="/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu")
    lines.append("HEAD: " + (r.stdout.strip() or "EMPTY"))
except Exception as e:
    lines.append("HEAD: ERR " + repr(e))

with io.open("/private/tmp/amubench_tick161_probe.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("probe ok")