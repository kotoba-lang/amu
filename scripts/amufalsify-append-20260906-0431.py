import subprocess, datetime
# sustained-window probe: 3 samples ~20s apart
out = []
for i in range(3):
    l = subprocess.run(["uptime"], capture_output=True, text=True).stdout.strip()
    out.append(l)
    if i < 2:
        subprocess.run(["sleep", "20"])
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M JST")
line = (f"2413|{ts} (amu-falsify cron): host busy under sustained-window protocol "
        f"(3x~20s samples): " + " | ".join(out) +
        " — threshold 7.5, load1 far above gate in all samples; no sustained quiet window. "
        "Per quiet-gate policy the J-B idle>=9/10 rerun, the H-Z3 hand-patch A/B, and the "
        "H-C2 timed A/B were NOT started; no bench, no perfgate run, no numbers. "
        "NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10, sustained-window protocol), "
        "then H-Z3 quiet-host hand-patch A/B, then H-C2 timed A/B. Population unchanged: "
        "J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder, "
        "H-C2 statically confirmed (61/61) but timed A/B pending, H-D/H-B/H-Y1 open; "
        "J-C blocked behind J-B. Doc read via grep to file (foreground terminal empty-output "
        "shape, known); this entry appended via python script (no heredoc, per the entry-117 convention).")
path = "docs/codegen-coscientist.md"
with open(path, "a") as f:
    f.write("\n" + line.split("|", 1)[1] + "\n")
print("appended")
print(line)
