# Build the N mutants, then run the rule checks (mutation3 criteria). WSL.
R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/mutation3_20261115
bash $R/build.sh
K=/root/work/mutation3/kernels; args=""
for f in $K/*.img; do n=$(basename $f .img); a=${n%_N*}; args="$args $n:$a:plain"; done
echo "run args:$args"
bash $R/run.sh mut3 $K $args
