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
import jdk.jfr.consumer.RecordedMethod;
import jdk.jfr.consumer.RecordedStackTrace;
import jdk.jfr.consumer.RecordingFile;

// J-A dispatch-share estimator V2 (amu-jit tick 29, 2026-09-08).
//
// Why a v2: tick-27's cross-attribution plan (SampleVersion=2 method-vs-stack
// leaf comparison) is NOT AVAILABLE on benjamin's JDK — Homebrew OpenJDK 26.0.1
// rejects -XX:FlightRecorderOptions=SampleVersion=2 outright (measured this
// tick: "Unknown argument 'SampleVersion' ... Failure when starting JFR").
// Instead of giving up the cross-check, v2 separates the two event types into
// their OWN aggregates from ONE recording: jdk.ExecutionSample -> stack-leaf
// (exclusive) / on-stack (inclusive) shares as in v1; jdk.MethodSample ->
// per-method exclusive counts using the event's own method (+interval) fields,
// no stack needed. If MethodSample fires natively on JDK 26 we get two
// independent leaf attributions to cross-check (kills tick-27 caveat (a):
// JIT-inlined push sites piling onto the MStack.push leaf name); if its event
// count is 0 we record that honestly — cross-attribution then impossible on
// this host's JDK, next branch per tick 27: perf counters.
//
// v1 perturbation profile is unchanged: passive sampling, no per-wasm-instruction
// listener work; instance pool (SLOTS=8, REBUILD_EVERY=256) as in v1.
//
// usage: java ... JaJfrDispatchShareV2 <wasm> <kernel-n> <inner-iters> <warmup_s> <record_s>
public class JaJfrDispatchShareV2 {
    static final int SLOTS = 8;
    static final int REBUILD_EVERY = 256;
    static final String IM = "com.dylibso.chicory.runtime.InterpreterMachine";

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
        System.out.println("kernel(" + n + ")=" + fns[0].apply(n)[0]);

        long[] useCount = new long[SLOTS];
        useCount[0] = 1;

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
        Map<String, Long> methodW = new HashMap<>();   // jdk.MethodSample exclusive (weighted ns)
        Map<String, Long> methodC = new HashMap<>();   // jdk.MethodSample event counts
        Map<String, Long> perEvent = new HashMap<>();
        long[] total = {0};
        long wallSpanNs = 0;
        java.nio.file.Path f = Paths.get("/tmp/ja_jfr2_" + ProcessHandle.current().pid() + ".jfr");
        try (Recording r = new Recording()) {
            r.enable("jdk.ExecutionSample").withPeriod(java.time.Duration.ofMillis(10));
            r.enable("jdk.MethodSample").withPeriod(java.time.Duration.ofMillis(10));
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
            wallSpanNs = System.nanoTime() - t1;
            double wallNs = wallSpanNs / (double) Math.max(1, recIters);
            System.out.println("recorded_iters=" + recIters + " in " + seconds
                + "s wall_ns_per_call=" + (long) wallNs);
            System.out.println("load1_at_record_end=" + java.lang.management.ManagementFactory
                .getOperatingSystemMXBean().getSystemLoadAverage());
            for (RecordedEvent e : RecordingFile.readAllEvents(f)) {
                String evn = e.getEventType().getName();
                perEvent.merge(evn, 1L, Long::sum);
                if (evn.equals("jdk.MethodSample")) {
                    long w = 1;
                    try {
                        if (e.hasField("interval")) w = Math.max(1, e.getDuration("interval").toNanos());
                    } catch (Throwable ignored) {}
                    String k = "?";
                    try {
                        RecordedMethod m = e.getValue("method");
                        if (m != null) k = m.getType().getName() + "." + m.getName();
                    } catch (Throwable t) {
                        try { k = String.valueOf(e.getValue("method")); } catch (Throwable ignored) {}
                    }
                    methodW.merge(k, w, Long::sum);
                    methodC.merge(k, 1L, Long::sum);
                    continue;
                }
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
                    String k2 = key(fr);
                    if (seen.add(k2)) onstack.computeIfAbsent(k2, x -> new long[1])[0]++;
                }
            }
            Files.deleteIfExists(f);
        }
        long T = total[0];
        System.out.println("events=" + perEvent + " total_stack_samples=" + T);
        System.out.println("STACK EXCLUSIVE_leaf call=" + pct(leaf, IM + ".call", T)
            + " eval=" + pct(leaf, IM + ".eval", T));
        System.out.println("STACK INCLUSIVE_onstack call=" + pct(onstack, IM + ".call", T)
            + " eval=" + pct(onstack, IM + ".eval", T));
        dump("STACK top20_leaf", leaf, T);
        dump("STACK top20_onstack", onstack, T);
        long MW = methodW.values().stream().mapToLong(Long::longValue).sum();
        long MC = methodC.values().stream().mapToLong(Long::longValue).sum();
        System.out.println("METHODSAMPLE events=" + MC + " total_weight_ns=" + MW
            + " distinct_methods=" + methodW.size());
        if (MC > 0) {
            Map<String, long[]> mw = new HashMap<>();
            methodW.forEach((k, v) -> mw.put(k, new long[]{v}));
            dumpW("METHOD top20_exclusive(weight_ns)", mw, MW);
            System.out.println("METHOD weight/wall_recorded_span=" + String.format("%.3f",
                MW / (double) Math.max(1, wallSpanNs)));
        }
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

    static void dumpW(String title, Map<String, long[]> m, long W) {
        System.out.println(title + ":");
        m.entrySet().stream().sorted((a, b) -> Long.compare(b.getValue()[0], a.getValue()[0]))
            .limit(20).forEach(en -> System.out.printf("  %6.2f%% %12d %s%n",
                100.0 * en.getValue()[0] / W, en.getValue()[0], en.getKey()));
    }

    static String pct(Map<String, long[]> m, String k, long T) {
        long[] v = m.get(k);
        return v == null ? "0" : String.format("%.1f%% (%d/%d)", 100.0 * v[0] / T, v[0], T);
    }
}
