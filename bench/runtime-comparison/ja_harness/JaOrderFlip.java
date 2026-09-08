import com.dylibso.chicory.wasm.Parser;
import com.dylibso.chicory.wasm.WasmModule;
import com.dylibso.chicory.runtime.ExecutionListener;
import com.dylibso.chicory.runtime.ExportFunction;
import com.dylibso.chicory.runtime.Instance;
import com.dylibso.chicory.runtime.MStack;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Arrays;

// Tick-25 control for the bare>listener inversion seen in the first
// dispatch-share attempts. Same batched-call method, but the arm order is
// FLIPPED (listener first, bare second) within each alternation. If the
// inversion is an order artifact the sign flips with order -> the wall-diff
// cannot bound dispatch share. Result (this tick): sign DOES follow order
// (+5.2% listener-first vs -33.0% bare-first), both arms on the same
// InterpreterMachine class. Estimator falsified; see README.md.
//
// usage: java ... JaOrderFlip <wasm> <kernel-n> <batch> <reps> <listenerFirst>
public class JaOrderFlip {
    static final ExecutionListener EMPTY = new ExecutionListener() {
        public void onExecution(com.dylibso.chicory.wasm.types.Instruction i, MStack s) {}
    };

    static double median(double[] xs) {
        double[] c = xs.clone(); Arrays.sort(c);
        int n = c.length;
        return n % 2 == 1 ? c[n / 2] : (c[n / 2 - 1] + c[n / 2]) / 2.0;
    }

    public static void main(String[] args) throws Exception {
        byte[] bytes = Files.readAllBytes(Paths.get(args[0]));
        long n = Long.parseLong(args[1]);
        int batch = Integer.parseInt(args[2]);
        int reps = Integer.parseInt(args[3]);
        boolean listenerFirst = Boolean.parseBoolean(args[4]);
        WasmModule m = Parser.parse(bytes);

        Instance b = Instance.builder(m).build();
        Instance l = Instance.builder(m).withUnsafeExecutionListener(EMPTY).build();
        ExportFunction fb = b.export("kernel");
        ExportFunction fl = l.export("kernel");
        System.out.println("machine_bare=" + b.getMachine().getClass().getSimpleName()
            + " machine_listener=" + l.getMachine().getClass().getSimpleName()
            + " listenerFirst=" + listenerFirst
            + " load1_at_start=" + java.lang.management.ManagementFactory
                .getOperatingSystemMXBean().getSystemLoadAverage());

        double[] tb = new double[reps];
        double[] tl = new double[reps];
        for (int w = 0; w < 10; w++) { fb.apply(n); fl.apply(n); }
        for (int r = 0; r < reps; r++) {
            if (listenerFirst) {
                long t0 = System.nanoTime();
                for (int i = 0; i < batch; i++) fl.apply(n);
                long t1 = System.nanoTime();
                tl[r] = (t1 - t0) / (double) batch;
                t0 = System.nanoTime();
                for (int i = 0; i < batch; i++) fb.apply(n);
                t1 = System.nanoTime();
                tb[r] = (t1 - t0) / (double) batch;
            } else {
                long t0 = System.nanoTime();
                for (int i = 0; i < batch; i++) fb.apply(n);
                long t1 = System.nanoTime();
                tb[r] = (t1 - t0) / (double) batch;
                t0 = System.nanoTime();
                for (int i = 0; i < batch; i++) fl.apply(n);
                long t1 = System.nanoTime();
                tl[r] = (t1 - t0) / (double) batch;
            }
        }
        double mb = median(tb), ml = median(tl);
        System.out.println("per_call_ns median bare=" + mb + " listener=" + ml
            + " delta=" + (ml - mb) + " (" + (100.0 * (ml - mb) / mb) + "% of bare)");
        System.out.println("load1_at_end=" + java.lang.management.ManagementFactory
            .getOperatingSystemMXBean().getSystemLoadAverage());
    }
}
