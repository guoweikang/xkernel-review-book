import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.store.FSDirectory;
import recommender.Evaluator;
import recommender.Program;
import recommender.ir.IRAnalysis;

public class InMapInputProbe {
    public static void main(String[] arguments) throws Exception {
        Method loader = Evaluator.class.getDeclaredMethod("loadConfigSettings", String.class);
        loader.setAccessible(true);
        loader.invoke(null, "config-single.txt");
        Field field = Evaluator.class.getDeclaredField("program");
        field.setAccessible(true);
        Program program = (Program) field.get(null);
        if (program.getProgramMap().isEmpty() || program.getPackageExclusion() == null) {
            throw new IllegalStateException("Original configuration parser did not initialize required fields");
        }
        IRAnalysis analysis = new IRAnalysis(program, 1, true);
        ArrayList<String> names = new ArrayList<>(analysis.getFilteredClasses());
        Collections.sort(names);
        Files.write(Paths.get("filtered-classes.txt"), names, StandardCharsets.UTF_8);
        System.out.println("FILTERED_CLASSES\t" + names.size());
        int oracleCount = program.getProgramMap().values().stream().mapToInt(ArrayList::size).sum();
        System.out.println("ORACLE_ENTRIES\t" + oracleCount);
        try (DirectoryReader reader = DirectoryReader.open(FSDirectory.open(Paths.get(program.getProgramUrl() + "index")))) {
            System.out.println("INDEX_DOCUMENTS\t" + reader.numDocs());
            ArrayList<String> paths = new ArrayList<>();
            for (int document = 0; document < reader.maxDoc(); document++) {
                paths.add(reader.document(document).get("path"));
            }
            Collections.sort(paths);
            Files.write(Paths.get("indexed-paths.txt"), paths, StandardCharsets.UTF_8);
        }
        System.out.println("DEPENDENCY_GRAPH_EXISTS\t" + Files.isRegularFile(Paths.get(program.getProgramUrl() + "bin/static-cdg.txt")));
        int retrievalLimit = arguments.length == 0 ? names.size() : Integer.parseInt(arguments[0]);
        analysis.setNumOfRequestedDocs(retrievalLimit);
        System.out.println("RETRIEVAL_LIMIT\t" + retrievalLimit);
        Map<Map<String, String>, Double> scores = analysis.getSimilarityAffinityScores(
                new HashMap<String, HashSet<String>>(), 33.0, 1.0);
        ArrayList<String> scoreRows = new ArrayList<>();
        for (Map.Entry<Map<String, String>, Double> item : scores.entrySet()) {
            if (!Double.isFinite(item.getValue())) {
                throw new IllegalStateException("Non-finite original IR score");
            }
            Map.Entry<String, String> pair = item.getKey().entrySet().iterator().next();
            scoreRows.add(pair.getKey() + "\t" + pair.getValue() + "\t" + item.getValue());
        }
        Collections.sort(scoreRows);
        Files.write(Paths.get("initial-ir-scores.tsv"), scoreRows, StandardCharsets.UTF_8);
        System.out.println("INITIAL_IR_PAIRS\t" + scoreRows.size());
        System.out.println("SCOPE\toriginal input pipeline and initial IR scoring; no iterative recommendations");
    }
}
