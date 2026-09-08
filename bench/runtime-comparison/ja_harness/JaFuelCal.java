import com.dylibso.chicory.wasm.Parser;
import com.dylibso.chicory.wasm.WasmModule;
import com.dylibso.chicory.runtime.ExportFunction;
import com.dylibso.chicory.runtime.Instance;

// Tick-27 scratch calibration (diagnostic, not sealed): how many kernel()
// calls fit in one sealed-fuel instance, and what does a fresh Instance
// rebuild cost relative to a call? The tick-26 JFR harness cached
// ExportFunctions from 8 instances and trapped after ~13 calls — proving
// per-call rebuild is mandatory (as the tick-24 harness note said).
public class JaFuelCal {
    public static void main(String[] args) throws Exception {
        byte[] bytes = java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(args[0]));
        long n = Long.parseLong(args[1]);
        WasmModule mod = Parser.parse(bytes);

        // calls until trap on one instance
        Instance inst = Instance.builder(mod).build();
        ExportFunction k = inst.export("kernel");
        int calls = 0;
        try {
            while (true) { k.apply(n); calls++; }
        } catch (Exception e) {
            System.out.println("calls_until_trap=" + calls + " err=" + e.getClass().getSimpleName());
        }

        // rebuild cost vs call cost (order of magnitude only; load-unstable)
        long t0 = System.nanoTime(); int reps = 200;
        for (int i = 0; i < reps; i++) {
            Instance b = Instance.builder(mod).build();
            b.export("kernel").apply(n);
        }
        long t1 = System.nanoTime();
        for (int i = 0; i < reps; i++) {
            Instance b = Instance.builder(mod).build();
        }
        long t2 = System.nanoTime();
        // reuse-allowed control: kernel(1..callsUntilTrap-1) calls on ONE instance
        Instance one = Instance.builder(mod).build();
        ExportFunction k1 = one.export("kernel");
        long t3 = System.nanoTime();
        for (int i = 0; i < reps; i++) k1.apply(n);
        long t4 = System.nanoTime();
        System.out.printf("ns_per_rebuild_and_call=%d ns_per_rebuild_only=%d ns_per_call_on_same_instance_first_%d=%.0f%n",
            (t1 - t0) / reps, (t2 - t0 - (t1 - t0)) / reps, reps, (t4 - t3) / (double) reps);
    }
}
