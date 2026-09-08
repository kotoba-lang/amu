import com.dylibso.chicory.wasm.Parser;
import com.dylibso.chicory.wasm.WasmModule;
import com.dylibso.chicory.runtime.ExecutionListener;
import com.dylibso.chicory.runtime.Instance;
import com.dylibso.chicory.runtime.MStack;
import com.dylibso.chicory.wasm.types.OpCode;
import java.nio.file.Files;
import java.nio.file.Paths;

// J-A counting estimator (load-robust: no timing). Per-call executed-opcode
// histogram for the kernel export via withUnsafeExecutionListener. This is
// the ground-truth denominator for any dispatch-share estimate; kernel(200)
// = 120 instructions, flat in n (n is a scalar arg, no loop in kernel).
//
// usage: java ... JaOpHistogram <wasm> <kernel-n>
public class JaOpHistogram {
    static final int[] CNT = new int[OpCode.values().length];
    static final ExecutionListener HIST = new ExecutionListener() {
        public void onExecution(com.dylibso.chicory.wasm.types.Instruction i, MStack s) {
            CNT[i.opcode().ordinal()]++;
        }
    };

    public static void main(String[] args) throws Exception {
        WasmModule m = Parser.parse(Files.readAllBytes(Paths.get(args[0])));
        long n = Long.parseLong(args[1]);
        Instance.builder(m).withUnsafeExecutionListener(HIST).build()
            .export("kernel").apply(n);
        int total = 0;
        for (int c : CNT) total += c;
        System.out.println("kernel(" + n + ") executed_instructions=" + total);
        for (int i = 0; i < CNT.length; i++) {
            if (CNT[i] > 0) System.out.println("  " + OpCode.values()[i] + " = " + CNT[i]
                + " (" + (100.0 * CNT[i] / total) + "%)");
        }
        Instance p = Instance.builder(m).build();
        StringBuilder sb = new StringBuilder("static per func: ");
        for (int f = 0; f < p.functionCount(); f++) {
            sb.append(f).append('=').append(p.function(f) == null ? "imp"
                : String.valueOf(p.function(f).instructions().size())).append(' ');
        }
        System.out.println(sb);
    }
}
