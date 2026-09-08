import com.dylibso.chicory.wasm.Parser;
import com.dylibso.chicory.wasm.WasmModule;
import com.dylibso.chicory.runtime.ExportFunction;
import com.dylibso.chicory.runtime.Instance;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import jdk.jfr.Recording;
import jdk.jfr.consumer.RecordedEvent;
import jdk.jfr.consumer.RecordedFrame;
import jdk.jfr.consumer.RecordedStackTrace;
import jdk.jfr.consumer.RecordingFile;

// J-A dispatch-share estimator via JFR sampling (tick-25's named next
// candidate; built 2026-09-08 tick 26; fuel bug fixed tick 27; event-type
// fixed tick 27). Unlike the wall-diff estimator (FALSIFIED tick 25: its
// sign followed arm order), this adds NO per-wasm-instruction work: it
// passively samples the running JVM (jdk.ExecutionSample, 10 ms period) and
// reports leaf (exclusive) and on-stack (inclusive) sample share of
// com.dylibso.chicory.runtime.InterpreterMachine.execute / .call, plus a
// top-k per-method profile of everything running during the wasm loop.
//
// FIX 1 (2026-09-08 tick 27 smoke run): the first version cached 8
// ExportFunctions once and trapped ("unreachable") in the warmup loop —
// chicory fuel caps an Instance at 512 kernel calls (measured this tick:
// calls_until_trap=512, matching the sealed V8 fixture's calibration).
// A fresh Instance.builder(mod).build() gets its own 512 (verified 200/200
// rebuild+call iterations). Instances are now rebuilt every REBUILD_EVERY
// uses per slot; the ~16-55 us rebuild amortises to ~62-214 ns/call over
// 256 calls (~0.2-0.8% of the ~28 us interpreter call) and shows up in the
// JFR profile as its own leaf share (Instance.<init>/builder) if it ever
// matters — the reader subtracts it, no silent perturbation.
//
// FIX 2 (tick 27 smoke run 2): with only jdk.MethodSample enabled the run
// completed (6,396,400 iters, checksum OK) but total_samples=0 — per-method
// CPU sampling is off on Temurin 21.0.1 aarch64 unless
// -XX:FlightRecorderOptions=SampleVersion=2 is set. jdk.ExecutionSample
// (thread stack sampling) fires without extra flags; both events are now
// enabled and counted (the aggregate below mixes them; the per-event split
// is printed so a reader can separate them).
//
// Caveat recorded up front (no fabricated precision): JFR samples fire at
// safepoint polls; density inside a hot loop is policy-dependent, so share
// numbers are estimates whose bias is only known after a quiet-gate run +
// cross-check against the exact instruction counts (JaOpHistogram: kernel(N)
// = 120 instrs/call) and the recorded wall totals. Diagnostics only until
// perfgate + human-approved warmup/steady-state policy (docs/jit-cosientist.md).
//
// usage: java ... JaJfrDispatchShare <wasm> <kernel-n> <iters> <warmup_s> <record_s>
public class JaJfrDispatchShare {
    static final int SLOTS = 8;
    static final int REBUILD_EVERY = 256; // per-slot uses between rebuilds (fuel 512)

    static ExportFunction[] freshPool(WasmModule mod) {
        ExportFunction[] pool = new ExportFunction[SLOTS];
        for (int i = 0; i < SLOTS; i++) pool[i] = Instance.builder(mod).build().export("kernel");
        return pool;
    }

    public static void main(String[] args) throws Exception {
        byte[] bytes = Files.readAllBytes(Paths.get(args[0]));
        long n = Long.parseLong(args[1]);
        int iters = Integer.parseInt(args[2]);
        long warmupS = Long.parseLong(args[3]);
        long seconds = Long.parseLong(args[4]);

        WasmModule mod = Parser.parse(bytes);
        ExportFunction[] fns = freshPool(mod);
        // checksum sanity (sealed fixture: kernel(100) -> 110550153 on both hosts)
        System.out.println("kernel(" + n + ")=" + fns[0].apply(n)[0]);

        // useCount[slot] tracks calls since that slot's instance was built
        long[] useCount = new long[SLOTS];
        useCount[0] = 1; // the sanity call above consumed one of slot 0's fuel

        long t0 = System.nanoTime();
        long itersDone = 0;
        while ((System.nanoTime() - t0) < warmupS * 1_000_000_000L) {
            for (int i = 0; i < iters; i++) {
                int slot = (int) (itersDone % SLOTS);
                if (useCount[slot] >= REBUILD_EVERY) {
                    fns[slot] = Instance.builder(mod).build().export("kernel");
                    useCount[slot] = 0;
                }
                fns[slot].apply(n);
                useCount[slot]++;
                itersDone++;
            }
        }
        System.out.println("warmup_iters=" + itersDone);
        System.out.println("load1_at_warmup_end=" + java.lang.management.ManagementFactory
            .getOperatingSystemMXBean().getSystemLoadAverage());

        Map<String, long[]> leaf = new HashMap<>();
        Map<String, long[]> onstack = new HashMap<>();
        Map<String, Long> perEvent = new HashMap<>();
        long[] total = {0};
        java.nio.file.Path f = Paths.get("/tmp/ja_jfr_" + ProcessHandle.current().pid() + ".jfr");
        try (Recording r = new Recording()) {
            r.enable("jdk.ExecutionSample").withPeriod(java.time.Duration.ofMillis(10));
            r.enable("jdk.MethodSample").with("period", "10 ms");
            r.setToDisk(true);
            r.setDestination(f);
            r.setMaxAge(java.time.Duration.ofMinutes(10));
            r.setMaxSize(256L * 1024 * 1024);
            r.start();
            long t1 = System.nanoTime();
            long deadline = t1 + seconds * 1_000_000_000L;
            long recIters = 0;
            while (System.nanoTime() < deadline) {
                for (int i = 0; i < iters; i++) {
                    int slot = (int) (recIters % SLOTS);
                    if (useCount[slot] >= REBUILD_EVERY) {
                        fns[slot] = Instance.builder(mod).build().export("kernel");
                        useCount[slot] = 0;
                    }
                    fns[slot].apply(n);
                    useCount[slot]++;
                    recIters++;
                }
            }
            r.stop();
            double wallNs = (System.nanoTime() - t1) / (double) Math.max(1, recIters);
            System.out.println("recorded_iters=" + recIters + " in " + seconds
                + "s wall_ns_per_call=" + (long) wallNs);
            System.out.println("load1_at_record_end=" + java.lang.management.ManagementFactory
                .getOperatingSystemMXBean().getSystemLoadAverage());
            for (RecordedEvent e : RecordingFile.readAllEvents(f)) {
                perEvent.merge(e.getEventType().getName(), 1L, Long::sum);
                RecordedStackTrace st = e.getStackTrace();
                if (st == null) continue;
                java.util.List<RecordedFrame> frames = st.getFrames();
                if (frames.isEmpty()) continue;
                total[0]++;
                RecordedFrame lf = frames.get(0);
                String lk = key(lf);
                leaf.computeIfAbsent(lk, k -> new long[1])[0]++;
                Set<String> seen = new HashSet<>();
                for (RecordedFrame fr : frames) {
                    String k = key(fr);
                    if (seen.add(k)) onstack.computeIfAbsent(k, x -> new long[1])[0]++;
                }
            }
            Files.deleteIfExists(f);
        }
        long T = total[0];
        System.out.println("events=" + perEvent + " total_samples=" + T);
        String exe = "com.dylibso.chicory.runtime.InterpreterMachine.execute";
        String call = "com.dylibso.chicory.runtime.InterpreterMachine.call";
        System.out.println("EXCLUSIVE_leaf_share execute=" + pct(leaf, exe, T)
            + " call=" + pct(leaf, call, T));
        System.out.println("INCLUSIVE_onstack_share execute=" + pct(onstack, exe, T)
            + " call=" + pct(onstack, call, T));
        dump("top20_leaf", leaf, T);
        dump("top20_onstack", onstack, T);
    }

    static String key(RecordedFrame fr) {
        return fr.getMethod().getType().getName() + "." + fr.getMethod().getName();
    }

    static void dump(String title, Map<String, long[]> m, long T) {
        System.out.println(title + ":");
        m.entrySet().stream().sorted((a, b) -> Long.compare(b.getValue()[0], a.getValue()[0]))
            .limit(20).forEach(en -> System.out.printf("  %6.2f%% %7d %s%n",
                100.0 * en.getValue()[0] / T, en.getValue()[0], en.getKey()));
    }

    static String pct(Map<String, long[]> m, String k, long T) {
        long[] v = m.get(k);
        return v == null ? "0" : String.format("%.1f%% (%d/%d)", 100.0 * v[0] / T, v[0], T);
    }
}
