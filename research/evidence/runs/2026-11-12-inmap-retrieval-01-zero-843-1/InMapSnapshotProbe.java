import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import recommender.Evaluator;
import recommender.Program;
import recommender.InMapTrace;
import recommender.ir.IRAnalysis;

public class InMapSnapshotProbe {
    public static void main(String[] arguments) throws Exception {
        Method loader = Evaluator.class.getDeclaredMethod("loadConfigSettings", String.class);
        loader.setAccessible(true);
        loader.invoke(null, "config-single.txt");
        Field field = Evaluator.class.getDeclaredField("program");
        field.setAccessible(true);
        Program program = (Program) field.get(null);
        IRAnalysis analysis = new IRAnalysis(program, 1, true);
        ArrayList<String> names = new ArrayList<>(analysis.getFilteredClasses());
        Collections.sort(names);
        Files.write(Paths.get("filtered-classes.txt"), names, StandardCharsets.UTF_8);
        int argumentOffset = arguments.length > 0 && arguments[0].matches("[0-9]+") ? 1 : 0;
        analysis.setNumOfRequestedDocs(argumentOffset == 1 ? Integer.parseInt(arguments[0]) : names.size());
        HashMap<String, HashSet<String>> methods = new HashMap<>();
        if (arguments.length > argumentOffset) {
            for (String row : Files.readAllLines(Paths.get(arguments[argumentOffset]), StandardCharsets.UTF_8)) {
                String[] cells = row.split("\t", -1);
                if (cells.length != 2 || methods.containsKey(cells[0])) throw new IllegalStateException("Invalid method row");
                methods.put(cells[0], cells[1].isEmpty() ? new HashSet<>() : new HashSet<>(Arrays.asList(cells[1].split(","))));
            }
            if (!methods.keySet().equals(new HashSet<>(names))) throw new IllegalStateException("Method population mismatch");
        }
        analysis.setClassMethods(methods);
        HashMap<String, HashSet<String>> accepted = new HashMap<>();
        HashSet<String> owners = new HashSet<>();
        for (String row : Files.readAllLines(Paths.get("snapshot-input.tsv"), StandardCharsets.UTF_8)) {
            String[] cells = row.split("\t", -1);
            if (cells.length != 2 || !names.contains(cells[1]) || !program.getProgramMap().containsKey(cells[0]) || !owners.add(cells[1])) throw new IllegalStateException("Invalid accepted row");
            accepted.computeIfAbsent(cells[0], key -> new HashSet<>()).add(cells[1]);
        }
        InMapTrace.begin(1, accepted);
        Map<Map<String, String>, Double> scores = analysis.getSimilarityAffinityScores(accepted, 33.0, 1.0);
        ArrayList<String> rows = new ArrayList<>();
        for (Map.Entry<Map<String, String>, Double> item : scores.entrySet()) {
            if (!Double.isFinite(item.getValue())) throw new IllegalStateException("Non-finite score");
            Map.Entry<String, String> pair = item.getKey().entrySet().iterator().next();
            rows.add(pair.getKey() + "\t" + pair.getValue() + "\t" + item.getValue());
        }
        Collections.sort(rows);
        Files.write(Paths.get("initial-ir-scores.tsv"), rows, StandardCharsets.UTF_8);
        System.out.println("SNAPSHOT_ACCEPTED\t" + owners.size());
        System.out.println("SCORE_PAIRS\t" + rows.size());
    }
}
