# Build mutants, then run the rule checks on every mutant kernel (mutation criteria 三). WSL.
R=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/mutation_20261114
bash $R/build.sh
K=/root/work/mutation/kernels; args=""
for f in $K/*.img; do n=$(basename $f .img); a=${n%_M*}
  case $a in arm64) args="$args $n:arm64:plain $n:arm64:mte";; *) args="$args $n:$a:plain";; esac
done
echo "run args:$args"
bash $R/run.sh mut $K $args
