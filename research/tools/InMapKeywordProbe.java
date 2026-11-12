import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import recommender.Evaluator;
import recommender.Program;
import recommender.da.DependencyAnalysis;
import recommender.ir.IRAnalysis;

public class InMapKeywordProbe {
    private static Field field(Object target, String name) throws Exception {
        Field result = target.getClass().getDeclaredField(name);
        result.setAccessible(true);
        return result;
    }

    private static void invoke(Object target, String name) throws Exception {
        Method method = target.getClass().getDeclaredMethod(name);
        method.setAccessible(true);
        method.invoke(target);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, HashSet<String>> values(Object target, String name) throws Exception {
        return (Map<String, HashSet<String>>) field(target, name).get(target);
    }

    private static void snapshot(Object target, String fixture, String name) throws Exception {
        ArrayList<String> rows = new ArrayList<>();
        for (Map.Entry<String, HashSet<String>> entry : values(target, name).entrySet()) {
            ArrayList<String> methods = new ArrayList<>(entry.getValue());
            Collections.sort(methods);
            rows.add(entry.getKey() + "\t" + String.join(",", methods));
        }
        Collections.sort(rows);
        Files.write(Paths.get("keyword-" + fixture + "-" + name + ".tsv"), rows, StandardCharsets.UTF_8);
    }

    private static void reset(Object target) throws Exception {
        for (String name : new String[] {"classMethods", "sanitizedClassMethods", "filteredClassMethods"}) {
            values(target, name).clear();
        }
    }

    public static void main(String[] arguments) throws Exception {
        Method loader = Evaluator.class.getDeclaredMethod("loadConfigSettings", String.class);
        loader.setAccessible(true);
        loader.invoke(null, "config-single.txt");
        Field programField = Evaluator.class.getDeclaredField("program");
        programField.setAccessible(true);
        Program program = (Program) programField.get(null);
        DependencyAnalysis analysis = new DependencyAnalysis(program, new IRAnalysis(program, 1, true));
        String methodLine = "M:fixture.First:alpha() (M)fixture.Second:beta()";
        String classLine = "C:fixture.First fixture.Second";
        String[] names = {"method-only", "class-before-method", "class-after-method"};
        String[][] inputs = {{methodLine}, {classLine, methodLine}, {methodLine, classLine}};
        for (int fixture = 0; fixture < inputs.length; fixture++) {
            reset(analysis);
            String filename = "keyword-" + names[fixture] + "-input.txt";
            Files.write(Paths.get(filename), Arrays.asList(inputs[fixture]), StandardCharsets.UTF_8);
            field(analysis, "cdgPath").set(analysis, filename);
            invoke(analysis, "extractClassMethodsKeywords");
            snapshot(analysis, names[fixture], "classMethods");
            invoke(analysis, "sanitizeClassMethodsKeywords");
            snapshot(analysis, names[fixture], "sanitizedClassMethods");
        }
        for (boolean reverse : new boolean[] {false, true}) {
            reset(analysis);
            Map<String, HashSet<String>> input = new LinkedHashMap<>();
            String[] order = reverse ? new String[] {"fixture.Outer$Inner", "fixture.Other"}
                                     : new String[] {"fixture.Other", "fixture.Outer$Inner"};
            for (String owner : order) {
                input.put(owner, new HashSet<>(Arrays.asList(owner.contains("$") ? "innerMethod" : "unrelatedMethod")));
            }
            field(analysis, "classMethods").set(analysis, input);
            String name = reverse ? "inner-first" : "unrelated-first";
            snapshot(analysis, name, "classMethods");
            invoke(analysis, "sanitizeClassMethodsKeywords");
            snapshot(analysis, name, "sanitizedClassMethods");
        }
        System.out.println("SCOPE\tcontrolled method-keyword extraction and sanitization; synthetic inputs, not a recovered graph");
    }
}
