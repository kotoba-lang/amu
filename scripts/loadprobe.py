import subprocess, sys
r = subprocess.run(["uptime"], capture_output=True, text=True)
print("STDOUT:", r.stdout)
print("STDERR:", r.stderr)
print("RC:", r.returncode)
r2 = subprocess.run(["sysctl", "-n", "vm.loadavg"], capture_output=True, text=True)
print("loadavg:", r2.stdout, r2.stderr)
r3 = subprocess.run(["date"], capture_output=True, text=True)
print("date:", r3.stdout)
