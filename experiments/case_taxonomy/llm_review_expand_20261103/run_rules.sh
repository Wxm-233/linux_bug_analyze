#!/bin/bash
# Run the frozen version-2 rules (criteria.md section 1) on each new snapshot, 8 at a time; snapshots with a flags file are skipped, so it can be rerun. WSL; no model calls.
cd "$(dirname "$0")/../rules_v2_unified_20261103" || exit 1
printf '%s\n' v6.2 v6.3 v6.4 v6.5 v6.7 v6.8 v6.9 v6.10 v6.11 v6.13 v6.14 v6.15 v6.16 v6.17 v6.18 v6.19 v7.0 v7.1 v7.2 |
  xargs -P 8 -I{} sh -c 'test -f ../llm_review_expand_20261103/flags/flags_{}.json && { echo skip {}; exit 0; }; python3 -B rules2.py {} ../llm_review_expand_20261103/flags/flags_{}.json > ../llm_review_expand_20261103/flags/run_{}.log 2>&1; echo done {} $?'
