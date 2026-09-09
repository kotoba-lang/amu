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

// J-A dispatch-share estimator V2FIX (amu-jit tick 29, 2026-09-08).
//
// V2 -> V2FIX: on benjamin's Homebrew OpenJDK 26.0.1 the V2 smoke run died
// with "Not a valid Flight Recorder file. File length is only 0 bytes" —
// readAllEvents ran INSIDE the try-with-resources, i.e. before Recording.close()
// flushes the file on JDK 26 (Temurin 21 on the workstation did not behave
// this way). Fix: r.stop(), then close the Recording, THEN read the file.
//
// Estimator content unchanged from V2: one recording, two event types kept in
// SEPARATE aggregates. jdk.ExecutionSample -> stack-leaf (exclusive) and
// on-stack (inclusive) shares (v1 semantics). jdk.MethodSample -> per-method
// exclusive counts from the event's own method/interval fields (no stack).
// This is the tick-27 cross-attribution route WITHOUT SampleVersion=2, which
// benjamin's JDK rejects outright (measured this tick:
// "Unknown argument 'SampleVersion' ... Failure when starting JFR").
// If MethodSample event count is 0 on JDK 26 as well, the cross-check is
// impossible on this host and the next branch is perf counters (recorded,
// not fabricated).
//
// v1 perturbation profile unchanged: passive sampling, no per-instruction
// listener; pool SLOTS=8 / REBUILD_EVERY=256 (fuel 512 per Instance).
//
// usage: java ... JaJfrDispatchShareV2FIX <wasm> <kernel-n> <inner-iters> <warmup_s> <record_s>
public class JaJfrDispatchShareV2FIX {
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

        java.nio.file.Path f = Paths.get("/tmp/ja_jfr2fix_" + ProcessHandle.current().pid() + ".jfr");
        long recIters;
        long wallSpanNs;
        {
            Recording r = new Recording();
            r.enable("jdk.ExecutionSample").withPeriod(java.time.Duration.ofMillis(10));
            r.enable("jdk.MethodSample").withPeriod(java.time.Duration.ofMillis(10));
            r.setToDisk(true);
            r.setDestination(f);
            r.setMaxAge(java.time.Duration.ofMinutes(10));
            r.setMaxSize(256L * 1024 * 1024);
            r.start();
            long t1 = System.nanoTime();
            long deadline = t1 + seconds * 1_000_000_000L;
            recIters = 0;
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
            r.stop();
            r.close();   // JDK 26: file is only complete AFTER close (measured tick 29)
        }
        System.out.println("recorded_iters=" + recIters + " in " + seconds
            + "s wall_ns_per_call=" + (wallSpanNs / (double) Math.max(1, recIters)));
        System.out.println("load1_at_record_end=" + java.lang.management.ManagementFactory
            .getOperatingSystemMXBean().getSystemLoadAverage());

        Map<String, long[]> leaf = new HashMap<>();
        Map<String, long[]> onstack = new HashMap<>();
        Map<String, Long> methodW = new HashMap<>();
        Map<String, Long> methodC = new HashMap<>();
        Map<String, Long> perEvent = new HashMap<>();
        long T = 0;
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
            T++;
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
            dumpW("METHOD top20_exclusive(count)", new HashMap<String, long[]>() {{
                methodC.forEach((k, v) -> put(k, new long[]{v})); }}, MC);
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
