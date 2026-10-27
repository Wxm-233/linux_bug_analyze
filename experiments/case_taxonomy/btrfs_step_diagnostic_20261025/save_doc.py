from pathlib import Path
import hashlib,re,json,subprocess
HERE=Path(__file__).resolve().parent;p=Path('/usr/share/doc/qemu-system-common/system/gdb.html')
raw=p.read_bytes();s=raw.decode();i=s.find('qqemu.sstep')
(HERE/'qemu_step_document_excerpt.txt').write_text(re.sub('<[^>]+>','',s[i-1600:i+3500]))
(HERE/'qemu_document_identity.json').write_text(json.dumps(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),version=subprocess.check_output(['qemu-system-aarch64','--version']).decode()),indent=2)+'\n')
