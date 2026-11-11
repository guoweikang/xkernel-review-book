import java.util.Arrays;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.StringField;
import org.apache.lucene.document.TextField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.similarities.ClassicSimilarity;
import org.apache.lucene.store.ByteBuffersDirectory;

public class LuceneScoringProbe {
    public static void main(String[] arguments) throws Exception {
        String[][] fixtures = {
            {"driver.Node", "cpu node decode"},
            {"cpu.Node", "cpu node decode"},
            {"driver.Repeated", "cpu cpu cpu node decode"},
            {"driver.Prefix", "cpus node decode"},
            {"driver.Typo", "cpx node decode"},
            {"driver.Unrelated", "network packet transmit"}
        };
        String[] queries = {"cpu", "cpu*", "cpu~", "cpu*~", "( cpu*~ )^30.0 ( node*~ )^2.0"};
        for (String mode : Arrays.asList("default", "classic-control")) {
            try (ByteBuffersDirectory directory = new ByteBuffersDirectory();
                 StandardAnalyzer analyzer = new StandardAnalyzer()) {
                IndexWriterConfig configuration = new IndexWriterConfig(analyzer);
                if (mode.equals("classic-control")) {
                    configuration.setSimilarity(new ClassicSimilarity());
                }
                System.out.println("WRITER\t" + mode + "\t" + configuration.getSimilarity());
                try (IndexWriter writer = new IndexWriter(directory, configuration)) {
                    for (String[] fixture : fixtures) {
                        Document document = new Document();
                        document.add(new StringField("path", fixture[0], Field.Store.YES));
                        document.add(new TextField("contents", fixture[1], Field.Store.YES));
                        writer.addDocument(document);
                    }
                }
                try (DirectoryReader reader = DirectoryReader.open(directory)) {
                    IndexSearcher searcher = new IndexSearcher(reader);
                    if (mode.equals("classic-control")) {
                        searcher.setSimilarity(new ClassicSimilarity());
                    }
                    System.out.println("SEARCHER\t" + mode + "\t" + searcher.getSimilarity());
                    QueryParser parser = new QueryParser("contents", analyzer);
                    for (String source : queries) {
                        Query query = parser.parse(source);
                        System.out.println("QUERY\t" + mode + "\t" + source + "\t"
                                + query.getClass().getSimpleName() + "\t" + query);
                        System.out.println("REWRITE\t" + mode + "\t" + source + "\t"
                                + searcher.rewrite(query));
                        for (ScoreDoc hit : searcher.search(query, fixtures.length).scoreDocs) {
                            String path = searcher.doc(hit.doc).get("path");
                            double adjusted = path.contains("cpu") ? hit.score * 30.0 : hit.score / 30.0;
                            System.out.println("HIT\t" + mode + "\t" + source + "\t" + path
                                    + "\t" + hit.score + "\t" + adjusted);
                            System.out.println("EXPLAIN\t" + mode + "\t" + source + "\t" + path
                                    + "\t" + searcher.explain(query, hit.doc).toString().replace("\n", "\\n"));
                        }
                    }
                }
            }
        }
    }
}
