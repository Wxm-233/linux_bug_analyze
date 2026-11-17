# Claude 2026-11-08: build the senior's archbound (tool.zip) against the installed LLVM 18; the zip's Makefile is not used/modified.
set -euo pipefail
SRC=/mnt/c/Users/dell/AppData/Local/Temp/claude/9fd635bfbbb91193/85a3fb53-11cd-41f5-9f3f-98c9249974d0/scratchpad/tool_unzipped/tool
DST=/root/work/archbound
rm -rf $DST; mkdir -p $DST; cp -r $SRC/src $SRC/synth_test $SRC/_fix $DST/
cd $DST
sed -i "s/clang::InternalLinkage/clang::Linkage::Internal/" src/Collect.cpp   # LLVM 18 API rename (only port change)
L=/usr/lib/llvm-18
for f in main Facts Collect Analyze; do
  $L/bin/clang++ -std=c++17 -fno-rtti -O2 -w -D_GNU_SOURCE -D__STDC_CONSTANT_MACROS -D__STDC_LIMIT_MACROS \
    -isystem $L/include -c src/$f.cpp -o src/$f.o 2> build_$f.err || { echo "compile $f failed"; head -40 build_$f.err; exit 1; }
done
$L/bin/clang++ src/*.o $L/lib/libclang-cpp.so.18.1 -L$L/lib -lLLVM-18 -Wl,-rpath,$L/lib -o archbound 2> link.err || { echo link failed; head -30 link.err; exit 1; }
ls -la archbound
