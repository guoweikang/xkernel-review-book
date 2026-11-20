#!/usr/bin/env bash
set -euo pipefail
fixture_dir=$(cd -- "$(dirname -- "$0")" && pwd)
output_dir=${1:?Provide a fresh output directory}
mkdir -- "$output_dir"
output_dir=$(cd -- "$output_dir" && pwd)
rustc +1.95.0 -vV > "$output_dir/toolchain.txt"
printf 'mode\trepetition\texit_code\n' > "$output_dir/results.tsv"
for mode in debug release; do
    optimization=0
    if [[ "$mode" == release ]]; then optimization=3; fi
    timeout 60 rustc +1.95.0 --edition=2024 --test "$fixture_dir/witness.rs" \
        -C panic=unwind -C opt-level="$optimization" -o "$output_dir/$mode" \
        > "$output_dir/$mode-build.log" 2>&1
    for repetition in 1 2; do
        status=0
        timeout 60 "$output_dir/$mode" --test-threads=1 --nocapture \
            > "$output_dir/$mode-$repetition.log" 2>&1 || status=$?
        printf '%s\t%s\t%s\n' "$mode" "$repetition" "$status" >> "$output_dir/results.tsv"
    done
done
