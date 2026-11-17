# Claude 2026-11-09: build the extended archbound (criteria section 2) from this round's archbound_ext/src with LLVM 18.
# src = tool.zip's src + "clang::InternalLinkage -> clang::Linkage::Internal" (LLVM 18 rename) + patch_ext.py.
set -euo pipefail
HERE=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/checks2_xarch_20261109/archbound_ext
DST=/root/work/checks2/archbound_ext
rm -rf $DST; mkdir -p $DST; cp -r $HERE/src $DST/; cd $DST
L=/usr/lib/llvm-18
for f in main Facts Collect Analyze; do
  $L/bin/clang++ -std=c++17 -fno-rtti -O2 -w -D_GNU_SOURCE -D__STDC_CONSTANT_MACROS -D__STDC_LIMIT_MACROS \
    -isystem $L/include -c src/$f.cpp -o src/$f.o 2> build_$f.err || { echo "compile $f failed"; head -30 build_$f.err; exit 1; }
done
$L/bin/clang++ src/*.o $L/lib/libclang-cpp.so.18.1 -L$L/lib -lLLVM-18 -Wl,-rpath,$L/lib -o archbound
sha256sum archbound src/*.cpp src/*.h | tee $HERE/build_sha256.txt
