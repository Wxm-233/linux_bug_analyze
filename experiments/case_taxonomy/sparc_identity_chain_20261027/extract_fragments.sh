#!/bin/bash
# Extract original function bodies verbatim from pinned blobs; record blob ids and line ranges.
set -eu
REPO=/root/repos/linux
HERE=$(cd "$(dirname "$0")" && pwd)
OUT="$HERE/fragments"
mkdir -p "$OUT"
P=95706e717c4f55ca62025c151451ccc28863d085
F=98937707fea8375e8acea0aaa0b68a956dd52719
MANIFEST="$HERE/source_manifest.tsv"
printf 'name\tcommit\tpath\tblob\tfirst_line\tlast_line\tsha256\n' > "$MANIFEST"

extract() {  # name commit path header-regex
  local name=$1 rev=$2 path=$3 re=$4
  local blob first last
  blob=$(git -C "$REPO" rev-parse "$rev:$path")
  git -C "$REPO" show "$rev:$path" > "$OUT/.whole"
  first=$(grep -n -m1 -E "$re" "$OUT/.whole" | cut -d: -f1)
  [ -n "$first" ] || { echo "header not found: $name" >&2; exit 2; }
  # a function header may span the previous line (return type on its own line)
  if ! grep -q '(' <(sed -n "${first}p" "$OUT/.whole"); then echo "bad header $name" >&2; exit 2; fi
  case "$(sed -n "$((first-1))p" "$OUT/.whole")" in
    static*|void*|int*|"static inline"*) first=$((first-1));;
  esac
  last=$(awk -v s="$first" 'NR>=s && /^}/ {print NR; exit}' "$OUT/.whole")
  sed -n "${first},${last}p" "$OUT/.whole" > "$OUT/$name.c"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$rev" "$path" "$blob" "$first" "$last" \
    "$(sha256sum "$OUT/$name.c" | cut -d' ' -f1)" >> "$MANIFEST"
}

extract record_one_cpu_parent "$P" arch/sparc/kernel/prom_64.c '^static void \*record_one_cpu\('
extract record_one_cpu_fixed  "$F" arch/sparc/kernel/prom_64.c '^static void \*record_one_cpu\('
extract smp_fill_in_cpu_possible_map_parent "$P" arch/sparc/kernel/smp_64.c '^void __init smp_fill_in_cpu_possible_map\('
extract alloc_irqstack_bootmem_parent "$P" arch/sparc/kernel/setup_64.c '^static void __init alloc_irqstack_bootmem\('
extract alloc_irqstack_bootmem_fixed  "$F" arch/sparc/kernel/setup_64.c '^static void __init alloc_irqstack_bootmem\('
extract nrcpus "$F" kernel/smp.c '^static int __init nrcpus\('
extract setup_nr_cpu_ids "$F" kernel/smp.c '^void __init setup_nr_cpu_ids\('
extract cpuhp_bringup_mask "$F" kernel/cpu.c '^static void __init cpuhp_bringup_mask\('
extract cpu_up_reference "$F" kernel/cpu.c '^static int cpu_up\(unsigned int cpu'
extract setup_arch_parent "$P" arch/sparc/kernel/setup_64.c '^void __init setup_arch\('
extract setup_arch_fixed  "$F" arch/sparc/kernel/setup_64.c '^void __init setup_arch\('
extract setup_per_cpu_areas_reference "$F" arch/sparc/kernel/smp_64.c '^void __init setup_per_cpu_areas\('
extract set_hardirq_stack_reference "$F" arch/sparc/kernel/kstack.h 'void \*set_hardirq_stack\(void\)'
rm -f "$OUT/.whole"

# whole-file blob identities used by the chain reading
{
  for rev in "$P" "$F" HEAD; do
    for f in arch/sparc/kernel/prom_64.c arch/sparc/kernel/setup_64.c arch/sparc/kernel/smp_64.c \
             arch/sparc/kernel/kstack.h arch/sparc/kernel/irq_64.c arch/sparc/mm/init_64.c \
             arch/sparc/Kconfig arch/sparc/configs/sparc64_defconfig include/linux/cpumask.h \
             kernel/cpu.c kernel/smp.c init/main.c Documentation/admin-guide/kernel-parameters.txt; do
      printf '%s\t%s\t%s\n' "$(git -C "$REPO" rev-parse "$rev")" "$f" "$(git -C "$REPO" rev-parse "$rev:$f")"
    done
  done
} > "$HERE/file_blobs.tsv"
echo "extracted $(($(wc -l < "$MANIFEST")-1)) fragments"
