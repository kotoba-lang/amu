import com.dylibso.chicory.wasm.Parser;
import com.dylibso.chicory.wasm.WasmModule;
import com.dylibso.chicory.runtime.ExecutionListener;
import com.dylibso.chicory.runtime.Instance;
import com.dylibso.chicory.runtime.MStack;
import com.dylibso.chicory.wasm.types.OpCode;
import java.nio.file.Files;
import java.nio.file.Paths;

// J-A counting estimator (load-robust). Per-iteration executed-opcode
// histogram for the bench loop export: count(r) = fixed + r*iter, so
// iter = (count(2) - count(0)) / 2 per opcode. Measured this tick: 128
// instructions/iteration (28 LOCAL_GET, 34 I64_CONST, 19 LOCAL_SET, 16
// I64_MUL, 9 I64_SUB, 8 I64_ADD, 8 I64_DIV_S, 1 BR, 1 IF, 1 I64_EQZ,
// 1 I64_EQ, 1 I64_EXTEND_I32_U).
//
// usage: java ... JaLoopHistogram <wasm> <kernel-n>
public class JaLoopHistogram {
    static final int[] CNT = new int[OpCode.values().length];
    static final ExecutionListener HIST = new ExecutionListener() {
        public void onExecution(com.dylibso.chicory.wasm.types.Instruction i, MStack s) {
            CNT[i.opcode().ordinal()]++;
        }
    };

    static int[] run(WasmModule m, long n, long r) {
        java.util.Arrays.fill(CNT, 0);
        Instance.builder(m).withUnsafeExecutionListener(HIST).build()
            .export("bench").apply(n, r);
        return CNT.clone();
    }

    public static void main(String[] args) throws Exception {
        WasmModule m = Parser.parse(Files.readAllBytes(Paths.get(args[0])));
        long n = Long.parseLong(args[1]);
        int[] a = run(m, n, 0);
        int[] b = run(m, n, 2);
        int totA = 0, totB = 0;
        for (int c : a) totA += c;
        for (int c : b) totB += c;
        System.out.println("bench(r=0) executed=" + totA + "  bench(r=2) executed=" + totB
            + "  per-iteration=" + (totB - totA) / 2);
        for (int i = 0; i < b.length; i++) {
            int it = (b[i] - a[i]) / 2;
            if (it > 0 || b[i] > 0) {
                System.out.println("  " + OpCode.values()[i] + " fixed=" + a[i] + " per_iter=" + it);
            }
        }
    }
}
