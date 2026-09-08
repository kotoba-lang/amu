import com.dylibso.chicory.wasm.Parser;
import com.dylibso.chicory.wasm.WasmModule;
import java.nio.file.Files;
import java.nio.file.Paths;

// J-A fixture shape check (static, load-independent): exports, imports.
// measured 2026-09-08 on kernel.kotoba.wasm: exports kernel(0) bench(1)
// __kotoba_loop_1(2) main(3), imports=0.
//
// usage: java ... JaModuleShape <wasm>
public class JaModuleShape {
    public static void main(String[] args) throws Exception {
        WasmModule m = Parser.parse(Files.readAllBytes(Paths.get(args[0])));
        var es = m.exportSection();
        System.out.println("exportCount=" + es.exportCount());
        for (int i = 0; i < es.exportCount(); i++) {
            var e = es.getExport(i);
            System.out.println("  export " + e.name() + " type=" + e.exportType() + " idx=" + e.index());
        }
        System.out.println("importCount=" + m.importSection().importCount());
    }
}
