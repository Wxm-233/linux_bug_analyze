from pathlib import Path
import hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent
vmlinux=Path('/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/parent/build/vmlinux')
sections=subprocess.check_output(['readelf','-S',str(vmlinux)]).decode()
(HERE/'vmlinux_sections.txt').write_text(sections)
state=dict(gdb=shutil.which('gdb'),gdb_multiarch=shutil.which('gdb-multiarch'),
    vmlinux=str(vmlinux),vmlinux_sha256=hashlib.sha256(vmlinux.read_bytes()).hexdigest(),
    has_symtab='.symtab' in sections,has_debug_sections='.debug' in sections,
    probe_only=True,linux_boots=0)
(HERE/'environment.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(state))
