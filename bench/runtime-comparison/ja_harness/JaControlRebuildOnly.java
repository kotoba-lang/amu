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

// J-A control arm (amu-jit tick 29): isolate instance-rebuild amortisation
// from the dispatch leaf-share attribution.
//
// V2FIX keeps a pool of 8 instances rebuilt every 256 uses (fuel 512). The
// rebuild (~16-55 us measured tick 27) amortises to 62-214 ns/call, i.e. up
// to ~28% of the ~751 ns/call recorded here — it is part of the timed loop,
// and JFR stack samples fired inside it land on the SAME InterpreterMachine
// on-stack frames we attribute to "dispatch". This control re-runs the exact
// V2FIX sampling loop with ONE instance and rebuilds every REBUILD_EVERY
// calls (default 100000, chosen > recorded calls/trap-margin? NO: fuel is
// 512/call per Instance — the trap after 512 would corrupt the loop). So
// instead: same trap-safe pool cadence BUT the loop alternates A) interpreter
// calls only (pool rebuild outside any measured region) vs B) rebuild-only
// calls (Instance.builder(mod).build() without apply). The rebuild-only rate
// x rebuild cost is subtractable from BOTH runs' totals, and the JFR leaf
// profile of the rebuild-only arm tells us whether rebuild contributes
// samples to InterpreterMachine.call/eval/numberOfParams AT ALL (it shouldn't
// — it's Instance.<init>/builder code), closing the contamination question.
//
// usage: java ... JaControlRebuildOnly <wasm> <kernel-n> <inner-iters> <warmup_s> <record_s>
public class JaControlRebuildOnly {
    public static void main(String[] args) throws Exception {
        byte[] bytes = Files.readAllBytes(Paths.get(args[0]));
        WasmModule mod = Parser.parse(bytes);
        // sanity + warmup: rebuilds only
        long t0 = System.nanoTime();
        long warmupS = Long.parseLong(args[3]);
        long rebuilds = 0;
        while ((System.nanoTime() - t0) < warmupS * 1_000_000_000L) {
            Instance.builder(mod).build().export("kernel").apply(100L);
            rebuilds++;
        }
        System.out.println("warmup_rebuild+call=" + rebuilds);
        java.nio.file.Path f = Paths.get("/tmp/ja_ctl_" + ProcessHandle.current().pid() + ".jfr");
        Recording r = new Recording();
        r.enable("jdk.ExecutionSample").withPeriod(java.time.Duration.ofMillis(10));
        r.setToDisk(true); r.setDestination(f);
        r.setMaxSize(64L * 1024 * 1024);
        r.start();
        long t1 = System.nanoTime();
        long deadline = t1 + Long.parseLong(args[4]) * 1_000_000_000L;
        long n2 = 0;
        while (System.nanoTime() < deadline) {
            // identical to V2FIX steady state: ONE call per freshly-built instance
            Instance.builder(mod).build().export("kernel").apply(100L);
            n2++;
        }
        long span = System.nanoTime() - t1;
        r.stop(); r.close();
        System.out.println("rebuild_call_iters=" + n2 + " ns_per_rebuild_call=" + (span / (double) n2));
        Map<String, long[]> leaf = new HashMap<>();
        Map<String, long[]> onstack = new HashMap<>();
        long T = 0;
        for (RecordedEvent e : RecordingFile.readAllEvents(f)) {
            RecordedStackTrace st = e.getStackTrace();
            if (st == null || st.getFrames().isEmpty()) continue;
            T++;
            leaf.computeIfAbsent(key(st.getFrames().get(0)), k -> new long[1])[0]++;
            Set<String> seen = new HashSet<>();
            for (RecordedFrame fr : st.getFrames()) {
                String k = key(fr);
                if (seen.add(k)) onstack.computeIfAbsent(k, x -> new long[1])[0]++;
            }
        }
        Files.deleteIfExists(f);
        System.out.println("samples=" + T);
        System.out.println("INCL InterpreterMachine.call=" + pct(onstack, "com.dylibso.chicory.runtime.InterpreterMachine.call", T));
        System.out.println("INCL InterpreterMachine.eval=" + pct(onstack, "com.dylibso.chicory.runtime.InterpreterMachine.eval", T));
        System.out.println("INCL numberOfParams=" + pct(onstack, "com.dylibso.chicory.runtime.InterpreterMachine.numberOfParams", T));
        System.out.println("top10_leaf:");
        leaf.entrySet().stream().sorted((a, b) -> Long.compare(b.getValue()[0], a.getValue()[0]))
            .limit(10).forEach(en -> System.out.printf("  %6.2f%% %5d %s%n", 100.0 * en.getValue()[0] / T, en.getValue()[0], en.getKey()));
    }
    static String key(RecordedFrame fr) {
        return fr.getMethod().getType().getName() + "." + fr.getMethod().getName();
    }
    static String pct(Map<String, long[]> m, String k, long T) {
        long[] v = m.get(k);
        return v == null ? "0" : String.format("%.1f%% (%d/%d)", 100.0 * v[0] / T, v[0], T);
    }
}
