#!/bin/bash
# keep only what later rounds need from the header-only variants: .config, generated headers, mm/.memory.o.cmd, logs
for d in /root/work/swapsym/cfg_*; do
  find "$d" -type f \( -name '*.o' -o -name '*.d' -o -name '*.a' -o -name '*.tmp' -o -name 'modules.order' -o -name '*.symvers' \) -delete
  find "$d" -type f -name '.*.cmd' ! -path "$d/mm/.memory.o.cmd" -delete
  find "$d/scripts" "$d/tools" -type f -exec sh -c 'head -c4 "$1" | grep -q "ELF" && rm -f "$1"' _ {} \; 2>/dev/null
  find "$d" -type d -empty -delete
done
du -sh /root/work/swapsym
