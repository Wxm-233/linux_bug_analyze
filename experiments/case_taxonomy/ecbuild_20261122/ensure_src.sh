#!/bin/bash
# Re-export the source copy of a revision for its kept header variants (space rule 11-22: source copies are not kept, ~11 s to re-export).
#   bash ensure_src.sh <rev>   -> /root/work/ecver/<rev12>/src (no-op if present); run before re-running ec6.py engine/fixed on kept variants
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
for r in "$@"; do
  REV=$(git -C $KSRC rev-parse --short=12 "$r"); W=/root/work/ecver/$REV
  if [ ! -f $W/src/Makefile ]; then rm -rf $W/src; mkdir -p $W/src; git -C $KSRC archive $REV | tar -x -C $W/src; echo "$REV src exported"; else echo "$REV src present"; fi
done
