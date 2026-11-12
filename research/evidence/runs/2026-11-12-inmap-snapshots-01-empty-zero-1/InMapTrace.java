package recommender;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.Map;

public class InMapTrace {
    private static int page;

    private static String clean(Object value) {
        return String.valueOf(value).replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n");
    }

    private static void append(String file, String row) {
        try {
            Files.write(Paths.get(file), (row + "\n").getBytes(StandardCharsets.UTF_8),
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
    }

    public static void begin(int number, Map<String, HashSet<String>> accepted) {
        page = number;
        ArrayList<String> rows = new ArrayList<>();
        for (Map.Entry<String, HashSet<String>> module : accepted.entrySet()) {
            for (String entity : module.getValue()) rows.add(page + "\t" + clean(module.getKey()) + "\t" + clean(entity));
        }
        Collections.sort(rows);
        for (String row : rows) append("trace-accepted.tsv", row);
        append("trace-pages.tsv", Integer.toString(page));
    }

    public static void query(String module, int acceptedCount, int budget, Object counts, String raw, Object parsed) {
        append("trace-queries.tsv", page + "\t" + clean(module) + "\t" + acceptedCount + "\t" + budget
                + "\t" + clean(counts) + "\t" + clean(raw) + "\t" + clean(parsed));
    }
}
