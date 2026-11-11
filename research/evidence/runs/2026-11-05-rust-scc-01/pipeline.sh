#!/bin/bash
set -euo pipefail
java -version
ant -version
test ! -e /root
test ! -e /proc/1/root
cd /work/clone-detector
ant clean cdi
bash execute.sh 1
run_phase() {
    echo 1 > search_metadata.txt
    rm -f nodes_completed.txt
    java -Dproperties.rootDir=/work/clone-detector/ \
        -Dproperties.location=/work/clone-detector/NODE_1/sourcerer-cc.properties \
        -Dlog4j.configurationFile=/work/clone-detector/NODE_1/log4j2.xml \
        -jar dist/indexbased.SearchManager.jar "$1" 8
}
run_phase init
run_phase index
bash move-index.sh
bash execute.sh 1
run_phase search
