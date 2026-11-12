import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.MethodTree;
import com.sun.source.tree.Tree;
import com.sun.source.util.JavacTask;
import java.nio.charset.StandardCharsets;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import javax.tools.SimpleJavaFileObject;

public class JavaDeclaredMethods {
    private static void selfTest(JavaCompiler compiler) throws Exception {
        String source = "package fixture; class Example { Example() {} "
                + "void alpha() { class Local { void ignored() {} } "
                + "Runnable task = new Runnable() { public void run() {} }; } "
                + "void alpha(int value) {} class Member { void beta() {} } "
                + "interface Nested { void gamma(); } String text = \"void fake() {}\"; } "
                + "interface Peer { void delta(); }";
        JavaFileObject input = new SimpleJavaFileObject(URI.create("string:///fixture/Example.java"), JavaFileObject.Kind.SOURCE) {
            public CharSequence getCharContent(boolean ignoreErrors) { return source; }
        };
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        ArrayList<String> observed = new ArrayList<>();
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(diagnostics, null, StandardCharsets.UTF_8)) {
            JavacTask parser = (JavacTask) compiler.getTask(null, manager, diagnostics,
                    Arrays.asList("-proc:none", "-source", "8"), null, Arrays.asList(input));
            for (CompilationUnitTree unit : parser.parse()) {
                for (Tree declaration : unit.getTypeDecls()) {
                    if (declaration instanceof ClassTree) collect((ClassTree) declaration, "fixture.", "fixture.java", observed);
                }
            }
        }
        List<String> expected = Arrays.asList("fixture.Example\talpha\tfixture.java", "fixture.Example\talpha\tfixture.java",
                "fixture.Example$Member\tbeta\tfixture.java", "fixture.Example$Nested\tgamma\tfixture.java",
                "fixture.Peer\tdelta\tfixture.java");
        Collections.sort(observed);
        Collections.sort(expected);
        if (!observed.equals(expected) || diagnostics.getDiagnostics().stream().anyMatch(item -> item.getKind() == Diagnostic.Kind.ERROR)) {
            throw new IllegalStateException("Declaration extraction fixture failed");
        }
        Files.write(Paths.get("declared-method-contract.tsv"), observed, StandardCharsets.UTF_8);
    }

    private static void collect(ClassTree declaration, String prefix, String source, List<String> rows) {
        String simple = declaration.getSimpleName().toString();
        if (simple.isEmpty()) return;
        String owner = prefix + simple;
        for (Tree member : declaration.getMembers()) {
            if (member instanceof MethodTree) {
                String method = ((MethodTree) member).getName().toString();
                if (!method.contains("<") && !method.contains("$")) {
                    rows.add(owner + "\t" + method + "\t" + source);
                }
            } else if (member instanceof ClassTree) {
                collect((ClassTree) member, owner + "$", source, rows);
            }
        }
    }

    public static void main(String[] arguments) throws Exception {
        Path root = Paths.get(arguments[0]).toAbsolutePath().normalize();
        List<Path> paths;
        try (Stream<Path> stream = Files.walk(root)) {
            paths = stream.filter(path -> path.toString().endsWith(".java")).sorted().collect(Collectors.toList());
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK compiler required");
        selfTest(compiler);
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        ArrayList<String> rows = new ArrayList<>();
        int units = 0;
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(diagnostics, null, StandardCharsets.UTF_8)) {
            Iterable<? extends JavaFileObject> files = manager.getJavaFileObjectsFromFiles(
                    paths.stream().map(Path::toFile).collect(Collectors.toList()));
            JavacTask parser = (JavacTask) compiler.getTask(null, manager, diagnostics,
                    Arrays.asList("-proc:none", "-source", "8"), null, files);
            for (CompilationUnitTree unit : parser.parse()) {
                units++;
                String prefix = unit.getPackageName() == null ? "" : unit.getPackageName().toString() + ".";
                String relative = root.relativize(Paths.get(unit.getSourceFile().toUri())).toString();
                for (Tree declaration : unit.getTypeDecls()) {
                    if (declaration instanceof ClassTree) collect((ClassTree) declaration, prefix, relative, rows);
                }
            }
        }
        ArrayList<String> messages = new ArrayList<>();
        int errors = 0;
        for (Diagnostic<? extends JavaFileObject> diagnostic : diagnostics.getDiagnostics()) {
            messages.add(diagnostic.toString());
            if (diagnostic.getKind() == Diagnostic.Kind.ERROR) errors++;
        }
        Files.write(Paths.get("declared-method-diagnostics.txt"), messages, StandardCharsets.UTF_8);
        if (errors != 0) throw new IllegalStateException("Parse errors: " + errors);
        Collections.sort(rows);
        Files.write(Paths.get("declared-methods.tsv"), rows, StandardCharsets.UTF_8);
        Files.write(Paths.get("declared-method-summary.tsv"), Arrays.asList(
                "source_files\t" + paths.size(), "parsed_units\t" + units,
                "method_declarations\t" + rows.size(), "parse_errors\t" + errors), StandardCharsets.UTF_8);
        System.out.println("SCOPE\tsource-defined named type methods; no type resolution, anonymous/local methods or generated methods");
    }
}
