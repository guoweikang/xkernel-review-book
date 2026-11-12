import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import recommender.AutoMap;
import recommender.Evaluator;
import recommender.Program;
import recommender.ir.IRAnalysis;

public class InMapLoopProbe {
    private static Object field(Object target, String name) throws Exception {
        Field result = target.getClass().getDeclaredField(name);
        result.setAccessible(true);
        return result.get(target);
    }

    @SuppressWarnings("unchecked")
    private static void scores(AutoMap mapper, String name) throws Exception {
        Map<Map<String, String>, Double> values = (Map<Map<String, String>, Double>) field(mapper, name);
        ArrayList<String> rows = new ArrayList<>();
        for (Map.Entry<Map<String, String>, Double> value : values.entrySet()) {
            if (value.getKey().size() != 1 || !Double.isFinite(value.getValue())) {
                throw new IllegalStateException("Invalid terminal score");
            }
            Map.Entry<String, String> pair = value.getKey().entrySet().iterator().next();
            rows.add(pair.getKey() + "\t" + pair.getValue() + "\t" + value.getValue());
        }
        Collections.sort(rows);
        Files.write(Paths.get("terminal-" + name + ".tsv"), rows, StandardCharsets.UTF_8);
    }

    @SuppressWarnings("unchecked")
    private static void selectionControls(AutoMap mapper, IRAnalysis analysis) throws Exception {
        String entity = analysis.getFilteredClasses().get(0);
        String[] modules = (String[]) field(mapper, "moduleNames");
        if (modules.length != 6) throw new IllegalStateException("Six-module fixture required");
        Map<Map<String, String>, Double> input = (Map<Map<String, String>, Double>) field(mapper, "classModuleSimilarity_AffinityScores");
        ((Map<?, ?>) field(mapper, "acceptedMappings")).clear();
        Method select = AutoMap.class.getDeclaredMethod("pickHighestClassScore");
        select.setAccessible(true);
        String[] labels = {"unique_maximum", "early_lower_tie_then_unique_maximum", "maximum_tie", "lower_tie_after_maximum"};
        double[][] fixtures = {{1, 2, 9, 0, 0, 0}, {1, 1, 9, 0, 0, 0}, {1, 9, 9, 0, 0, 0}, {1, 9, 2, 2, 0, 0}};
        ArrayList<String> rows = new ArrayList<>();
        rows.add("fixture\tselected_pairs\tmathematical_unique_maximum");
        for (int fixture = 0; fixture < fixtures.length; fixture++) {
            input.clear();
            for (int module = 0; module < modules.length; module++) {
                Map<String, String> pair = new HashMap<>();
                pair.put(entity, modules[module]);
                input.put(pair, fixtures[fixture][module]);
            }
            select.invoke(mapper);
            Map<?, ?> selected = (Map<?, ?>) field(mapper, "highestClassScoreMappings");
            rows.add(labels[fixture] + "\t" + selected.size() + "\t" + (fixture != 2));
        }
        Files.write(Paths.get("terminal-selection-controls.tsv"), rows, StandardCharsets.UTF_8);
    }

    @SuppressWarnings("unchecked")
    private static void mappings(AutoMap mapper, String name) throws Exception {
        Map<String, Set<String>> mapping = (Map<String, Set<String>>) field(mapper, name);
        ArrayList<String> rows = new ArrayList<>();
        for (Map.Entry<String, Set<String>> module : mapping.entrySet()) {
            for (String entity : module.getValue()) {
                rows.add(entity + "\t" + module.getKey());
            }
        }
        Collections.sort(rows);
        Files.write(Paths.get(name + ".tsv"), rows, StandardCharsets.UTF_8);
    }

    public static void main(String[] arguments) throws Exception {
        Method loader = Evaluator.class.getDeclaredMethod("loadConfigSettings", String.class);
        loader.setAccessible(true);
        loader.invoke(null, "config-single.txt");
        Field programField = Evaluator.class.getDeclaredField("program");
        programField.setAccessible(true);
        Program program = (Program) programField.get(null);
        if (Files.exists(Paths.get(program.getProgramUrl() + "bin/static-cdg.txt"))) {
            throw new IllegalStateException("This control requires an explicitly absent graph");
        }
        AutoMap mapper = new AutoMap(program, 1, "Search Only", "None", "Recommendation Average",
                1.0, 0.0, 0.0, 0.0, 33.0, 1.0, 0.0, 50, "missing-method-feedback", true);
        if (!((Map<?, ?>) field(mapper, "classMethodsMap")).isEmpty()) {
            throw new IllegalStateException("Unexpected method feedback in missing-input control");
        }
        IRAnalysis analysis = (IRAnalysis) field(mapper, "irAnalysis");
        Files.write(Paths.get("filtered-classes.txt"), new TreeSet<>(analysis.getFilteredClasses()), StandardCharsets.UTF_8);
        ArrayList<String> oracle = new ArrayList<>();
        for (Map.Entry<String, ArrayList<String>> module : program.getProgramMap().entrySet()) {
            for (String entity : module.getValue()) {
                oracle.add(entity + "\t" + module.getKey());
            }
        }
        Collections.sort(oracle);
        Files.write(Paths.get("oracle.tsv"), oracle, StandardCharsets.UTF_8);
        ArrayList<Map<String, String>> pages = mapper.call();
        TreeSet<String> columns = new TreeSet<>();
        for (Map<String, String> page : pages) columns.addAll(page.keySet());
        ArrayList<String> rows = new ArrayList<>();
        rows.add(String.join("\t", columns));
        for (Map<String, String> page : pages) {
            ArrayList<String> values = new ArrayList<>();
            for (String column : columns) values.add(page.getOrDefault(column, ""));
            rows.add(String.join("\t", values));
        }
        Files.write(Paths.get("pages.tsv"), rows, StandardCharsets.UTF_8);
        mappings(mapper, "acceptedMappings");
        mappings(mapper, "rejectedMappings");
        for (String name : new String[] {"classModuleSimilarity_AffinityScores", "classModule_AffinityScores",
                "highestClassScoreMappings", "recommendedMappings"}) {
            scores(mapper, name);
        }
        ArrayList<String> state = new ArrayList<>();
        for (String name : new String[] {"pageNumber", "runMapping", "threshold", "pageThreshold"}) {
            state.add(name + "\t" + field(mapper, name));
        }
        Files.write(Paths.get("terminal-state.tsv"), state, StandardCharsets.UTF_8);
        System.out.println("SCOPE\texplicit missing-method-feedback control; not full paper reproduction");
        System.out.println("PAGES\t" + pages.size());
        selectionControls(mapper, analysis);
    }
}
