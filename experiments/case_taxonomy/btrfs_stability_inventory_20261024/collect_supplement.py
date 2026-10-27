"""Save additional requested sources, from fixed parent git object only."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
revision='0d977e0eba234e01a60bdde27314dc21374201b3'
folder=HERE/'supplement_source';folder.mkdir(exist_ok=False)
rows=[]
for path in ['fs/super.c','include/linux/minmax.h']:
    raw=subprocess.check_output(['git','-C','/root/repos/linux','show',revision+':'+path])
    target=folder/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    rows.append(dict(path=path,revision=revision,artifact=str(target.relative_to(HERE)),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'supplement_source.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows))
