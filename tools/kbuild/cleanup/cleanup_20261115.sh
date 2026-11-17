# 2026-11-15 user-approved cleanup ("先清理空间"): duplicated / superseded kernels and object files.
set -u
echo "before: $(df -h / | tail -1)"
for d in kcov kcov_inline kcov_pa x1loop proprules; do
  K=/root/work/$d/kernels
  [ -d $K ] || continue
  s=$(du -sh $K | cut -f1); rm -rf -- "$K"; echo "removed $K ($s)"
done
for d in arm64_defconfig closure_20261108_arm64_bpf; do
  B=/root/work/boundary_build/$d
  s0=$(du -sh $B | cut -f1)
  find $B -type f \( -name '*.o' -o -name '*.ko' \) -delete
  echo "stripped $B: $s0 -> $(du -sh $B | cut -f1); kept: $(ls $B/vmlinux $B/compile_commands.json $B/.config $B/System.map 2>/dev/null | wc -l)/4 key files, generated headers: $(ls -d $B/include/generated $B/arch/arm64/include/generated 2>/dev/null | wc -l)/2"
done
echo "after: $(df -h / | tail -1)"
