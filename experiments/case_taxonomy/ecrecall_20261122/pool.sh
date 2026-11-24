#!/bin/bash
# ecrecall criteria 一.1: mechanical candidate pool. WSL.  -> stdout: hash<TAB>date<TAB>subject
# (script fix before any labelling: the first version matched the interface-name condition with a $'...' pattern whose escaping
#  silently dropped matches; the conditions are unchanged, the subject field is now matched directly)
cd /root/repos/linux
R=df2908090cda
A="riscv x86 arm64 powerpc s390 loongarch mips arm hexagon"
P=""
for a in $A; do P="$P arch/$a/include/asm/pgtable*.h arch/$a/include/asm/*/pgtable*.h arch/$a/include/asm/*/*/pgtable*.h arch/$a/include/asm/pte*.h arch/$a/include/asm/*/pte*.h arch/$a/include/asm/hugetlb.h arch/$a/include/asm/*hash*.h arch/$a/include/asm/*/*hash*.h arch/$a/include/asm/*/*/*hash*.h"; done
P="$P include/linux/pgtable.h include/linux/swapops.h include/linux/leafops.h"
NAME='(\b(pte|pmd|pud)_[a-z_]+|p\?d_|\{pte,pmd\}|swp|swap entr|PAGE_PROT_NONE|_PAGE_[A-Z_]+|soft.?dirty)'
FIX="fix|correct|comply|semantic|must|wrong|broken|incorrect|let |ensure|missing|preserve|keep|don't|do not|only care|return true|return false"
NOT="typo|comment|build|compile|warning|cleanup|clean up|rename|refactor|return bool|implement|batch|add architecture|standardi|params|include"
git log --no-merges --format='%h%x09%ad%x09%s' --date=short v5.4..$R -- $P | while IFS=$'\t' read -r h d s; do
  echo "$s" | grep -qE "$NAME" || continue
  echo "$s" | grep -qiE "$FIX" || continue
  echo "$s" | grep -qiE "$NOT" && continue
  printf '%s\t%s\t%s\n' "$h" "$d" "$s"
done
