import com.dylibso.chicory.wasm.Parser;
import com.dylibso.chicory.wasm.WasmModule;
import com.dylibso.chicory.runtime.ExecutionListener;
import com.dylibso.chicory.runtime.ExportFunction;
import com.dylibso.chicory.runtime.Instance;
import com.dylibso.chicory.runtime.MStack;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Arrays;

// J-A slope estimator: fixed-vs-per-instruction split on the LOOP export.
// bench(n, r) runs the kotoba loop r iterations; exact executed-instruction
// counts come from the counting listener (load-robust), per-call medians from
// timed fresh-instance runs. OLS(median_ns | instrs) -> slope =
// ns/executed-instruction (upper bound on dispatch+exec per instr),
// intercept = fixed per-call cost.
// TICK-25 STATUS: slope estimate NOT load-stable (454 ns/instr with negative
// intercept at load1 ~8; 200 ns/instr with +133 us intercept at load1 ~10;
// r=64 regime jump both runs). Re-run only in a quiet-gate window
// (idle >= 90%); do not quote these two runs.
//
// usage: java ... JaFixedVsSlope <wasm> <kernel-n> <reps>
public class JaFixedVsSlope {
    static volatile long instrCount = 0;
    static final ExecutionListener COUNT = new ExecutionListener() {
        public void onExecution(com.dylibso.chicory.wasm.types.Instruction i, MStack s) {
            instrCount++;
        }
    };

    static double median(double[] xs) {
        double[] c = xs.clone(); Arrays.sort(c);
        int n = c.length;
        return n % 2 == 1 ? c[n / 2] : (c[n / 2 - 1] + c[n / 2]) / 2.0;
    }

    public static void main(String[] args) throws Exception {
        byte[] bytes = Files.readAllBytes(Paths.get(args[0]));
        long n = Long.parseLong(args[1]);
        int reps = Integer.parseInt(args[2]);
        int[] rs = {0, 1, 2, 4, 8, 16, 32, 64};

        long[] icnt = new long[rs.length];
        {
            WasmModule m = Parser.parse(bytes);
            for (int k = 0; k < rs.length; k++) {
                instrCount = 0;
                Instance.builder(m).withUnsafeExecutionListener(COUNT).build()
                    .export("bench").apply(n, (long) rs[k]);
                icnt[k] = instrCount;
            }
        }

        double[] med = new double[rs.length];
        {
            WasmModule m = Parser.parse(bytes);
            for (int w = 0; w < 15; w++) {
                Instance.builder(m).build().export("bench").apply(n, 8L);
                Instance.builder(m).build().export("bench").apply(n, 32L);
            }
        }
        System.out.println("load1_at_start=" + java.lang.management.ManagementFactory
            .getOperatingSystemMXBean().getSystemLoadAverage());
        for (int k = 0; k < rs.length; k++) {
            double[] ts = new double[reps];
            for (int i = 0; i < reps; i++) {
                WasmModule m = Parser.parse(bytes);
                Instance inst = Instance.builder(m).build();
                ExportFunction f = inst.export("bench");
                long t0 = System.nanoTime();
                f.apply(n, (long) rs[k]);
                long t1 = System.nanoTime();
                ts[i] = t1 - t0;
            }
            med[k] = median(ts);
            System.out.println("r=" + rs[k] + " instrs=" + icnt[k] + " median_ns=" + (long) med[k]);
        }
        double sx = 0, sy = 0, sxx = 0, sxy = 0; int c = rs.length;
        for (int k = 0; k < c; k++) {
            sx += icnt[k]; sy += med[k]; sxx += icnt[k] * (double) icnt[k]; sxy += icnt[k] * med[k];
        }
        double slope = (c * sxy - sx * sy) / (c * sxx - sx * sx);
        double icept = (sy - slope * sx) / c;
        System.out.println("OLS ns_per_executed_instr=" + slope + " fixed_ns_per_call=" + icept);
        System.out.println("load1_at_end=" + java.lang.management.ManagementFactory
            .getOperatingSystemMXBean().getSystemLoadAverage());
    }
}
