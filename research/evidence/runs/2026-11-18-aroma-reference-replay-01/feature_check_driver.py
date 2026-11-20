import collections
import json
import pathlib
import runpy
import sys

source = pathlib.Path(sys.argv[1]).resolve()
fixture = pathlib.Path(sys.argv[2]).resolve()
expected_path = pathlib.Path(sys.argv[3]).resolve()
cache = pathlib.Path(sys.argv[4]).resolve()
query_too = len(sys.argv) > 5 and sys.argv[5] == "--query-too"
sys.argv = [str(source), "-c", str(fixture), "-d", str(cache)]
if query_too:
    sys.argv.extend(["-f", str(fixture)])
namespace = runpy.run_path(str(source), run_name="__main__")
records = namespace["records"]
vocabulary = namespace["vocab"]
feature_ids = [feature for record in records for feature in record["features"]]
actual = [vocabulary.get_word(feature) for feature in feature_ids]
expected = expected_path.read_text().splitlines()
actual_counts = collections.Counter(actual)
expected_counts = collections.Counter(expected)
result = {
    "records": len(records),
    "feature_occurrences": len(actual),
    "unique_features": len(actual_counts),
    "feature_id_types": dict(collections.Counter(type(feature).__name__ for feature in feature_ids)),
    "decoded_types": dict(collections.Counter(type(feature).__name__ for feature in actual)),
    "expected_lines": len(expected),
    "expected_unique": len(expected_counts),
    "expected_blank_lines": sum(feature == "" for feature in expected),
    "ordered_equal": actual == expected,
    "multiset_equal": actual_counts == expected_counts,
    "missing": dict(expected_counts - actual_counts),
    "extra": dict(actual_counts - expected_counts),
    "actual": actual,
    "expected": expected,
}
print("FEATURE_CHECK_JSON=" + json.dumps(result, sort_keys=True))
