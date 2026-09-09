// Fleet quiet gate probe (ADR 0282/0341 busy-CPU fraction), 1s samples.
// NOTE(amu-jit tick 31): first version used c.times.system; node's field is
// .sys -> busy_fraction came out NaN(null). Fixed here; the tick-31 post-run
// bracket below uses THIS version.
const os = require("os");
function snap() { return os.cpus().map(c => c.times); }
async function main() {
  const n = parseInt(process.argv[2] || "5", 10);
  const s1 = snap();
  for (let k = 0; k < n; k++) {
    await new Promise(r => setTimeout(r, 1000));
    const s2 = snap();
    let busy = 0, tot = 0, worst = 0;
    for (let i = 0; i < s1.length; i++) {
      const d = (s2[i].user - s1[i].user) + (s2[i].sys - s1[i].sys) +
                (s2[i].idle - s1[i].idle) + (s2[i].nice - s1[i].nice);
      const b = d - (s2[i].idle - s1[i].idle);
      busy += b; tot += d;
      worst = Math.max(worst, d > 0 ? b / d : 0);
      s1[i] = s2[i];
    }
    console.log(JSON.stringify({
      t: new Date().toISOString(),
      busy_fraction: +(busy / tot).toFixed(4),
      worst_cpu_busy: +worst.toFixed(3),
      load1: +os.loadavg()[0].toFixed(2),
      cores: s1.length
    }));
  }
}
main();
